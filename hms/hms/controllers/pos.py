# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.nestedset import get_root_of
from frappe.utils import cint

from erpnext.accounts.doctype.pos_invoice.pos_invoice import get_stock_availability
from erpnext.accounts.doctype.pos_profile.pos_profile import get_item_groups

from erpnext.selling.page.point_of_sale.point_of_sale import (
    search_by_term,
    get_conditions,
    get_item_group_condition,
)


from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import (
    POSInvoiceMergeLog,
)
from erpnext.accounts.doctype.pos_invoice.pos_invoice import (
    POSInvoice,
)
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
    SalesInvoice,
)

# POS Related Overrides


class HMSPOSInvoice(POSInvoice):
    """
    Override POSInvoice to allow non stock items in POS Invoice
    """

    def validate(self):
        if not cint(self.is_pos):
            frappe.throw(
                _("POS Invoice should have {} field checked.").format(
                    frappe.bold("Include Payment")
                )
            )

        # run on validate method of selling controller
        super(SalesInvoice, self).validate()
        self.validate_auto_set_posting_time()
        self.validate_mode_of_payment()
        self.validate_uom_is_integer("stock_uom", "stock_qty")
        self.validate_uom_is_integer("uom", "qty")
        self.validate_debit_to_acc()
        self.validate_write_off_account()
        self.validate_change_amount()
        self.validate_change_account()
        self.validate_item_cost_centers()
        self.validate_warehouse()
        self.validate_serialised_or_batched_item()
        self.validate_stock_availablility()
        self.validate_return_items_qty()
        # skip validation for non stock items in POS Invoice
        # self.validate_non_stock_items()
        self.set_status()
        self.set_account_for_mode_of_payment()
        self.validate_pos()
        self.validate_payment_amount()
        self.validate_loyalty_transaction()
        if self.coupon_code:
            from erpnext.accounts.doctype.pricing_rule.utils import validate_coupon_code

            validate_coupon_code(self.coupon_code)


class HMSPOSInvoiceMergeLog(POSInvoiceMergeLog):
    """
    This class overrides consolidation of POS Invoices
    into single Sales Invoice when a POS Closing Entry is made.
    POS Invoices with no room_folio_cf are consolidated as per default behavior.
    """

    def on_submit(self):
        pos_invoice_docs = [
            frappe.get_doc("POS Invoice", d.pos_invoice) for d in self.pos_invoices
        ]

        individual_invoices = [d for d in pos_invoice_docs if d.room_folio_cf]
        if not individual_invoices:
            super(HMSPOSInvoiceMergeLog, self).on_submit()
            return

        # returns are not handles for pos invoices with room_folio_cf
        # returns = [d for d in pos_invoice_docs if d.get("is_return") == 1]

        sales = [d for d in pos_invoice_docs if d.get("is_return") == 0]

        sales_invoice, credit_note = "", ""
        if sales:
            to_consolidate = [d for d in sales if not d.room_folio_cf]
            if to_consolidate:
                sales_invoice = self.process_merging_into_sales_invoice(to_consolidate)
                self.save()
                self.update_pos_invoices(pos_invoice_docs, sales_invoice, credit_note)

            # Create individual Sales Invoices for pos invoices with room_folio_cf
            if individual_invoices:
                for invoice in individual_invoices:
                    sales_invoice = self.process_merging_into_sales_invoice([invoice])
                    self.update_pos_invoices([invoice], sales_invoice, credit_note)
                    frappe.db.set_value(
                        "Sales Invoice",
                        sales_invoice,
                        "room_folio_cf",
                        invoice.room_folio_cf,
                    )


@frappe.whitelist()
def get_items(start, page_length, price_list, item_group, pos_profile, search_term=""):
    warehouse, hide_unavailable_items = frappe.db.get_value(
        "POS Profile", pos_profile, ["warehouse", "hide_unavailable_items"]
    )

    result = []

    if search_term:
        result = search_by_term(search_term, warehouse, price_list) or []
        if result:
            return result

    if not frappe.db.exists("Item Group", item_group):
        item_group = get_root_of("Item Group")

    condition = get_conditions(search_term)
    condition += get_item_group_condition(pos_profile)

    lft, rgt = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"])

    bin_join_selection, bin_join_condition = "", ""
    if hide_unavailable_items:
        bin_join_selection = ", `tabBin` bin"
        bin_join_condition = "AND bin.warehouse = %(warehouse)s AND bin.item_code = item.name AND bin.actual_qty > 0"

    items_data = frappe.db.sql(
        """
		SELECT
			item.name AS item_code,
			item.item_name,
			item.description,
			item.stock_uom,
			item.image AS item_image,
			item.is_stock_item
		FROM
			`tabItem` item {bin_join_selection}
		WHERE
			item.disabled = 0
			AND item.has_variants = 0
			AND item.is_sales_item = 1
			AND item.is_fixed_asset = 0
			AND item.item_group in (SELECT name FROM `tabItem Group` WHERE lft >= {lft} AND rgt <= {rgt})
			AND {condition}
			{bin_join_condition}
		ORDER BY
			item.name asc
		LIMIT
			{start}, {page_length}""".format(
            start=start,
            page_length=page_length,
            lft=lft,
            rgt=rgt,
            condition=condition,
            bin_join_selection=bin_join_selection,
            bin_join_condition=bin_join_condition,
        ),
        {"warehouse": warehouse},
        as_dict=1,
    )

    if items_data:
        # skip filtering out non stock items for POS item selector
        # items_data = filter_service_items(items_data)
        items = [d.item_code for d in items_data]
        item_prices_data = frappe.get_all(
            "Item Price",
            fields=["item_code", "price_list_rate", "currency"],
            filters={"price_list": price_list, "item_code": ["in", items]},
        )

        item_prices = {}
        for d in item_prices_data:
            item_prices[d.item_code] = d

        for item in items_data:
            item_code = item.item_code
            item_price = item_prices.get(item_code) or {}
            item_stock_qty = get_stock_availability(item_code, warehouse)

            row = {}
            row.update(item)
            row.update(
                {
                    "price_list_rate": item_price.get("price_list_rate"),
                    "currency": item_price.get("currency"),
                    "actual_qty": item_stock_qty,
                }
            )
            result.append(row)

    return {"items": result}
