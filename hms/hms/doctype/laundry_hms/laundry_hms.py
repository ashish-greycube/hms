# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
import frappe
from frappe.utils import now_datetime, nowdate, cint, getdate, add_days
from frappe.model.document import Document
from erpnext import get_default_currency, get_default_company
from erpnext.accounts.party import get_party_details
from erpnext.stock.get_item_details import get_price_list_rate_for


class LaundryHMS(Document):
    def validate(self):
        self.total_qty = sum([d.qty for d in self.items])
        folio = frappe.get_doc("Room Folio HMS", self.room_folio)
        if self.is_new() or not self.customer:
            if cint(folio.is_split_bill):
                laundry_item_group = frappe.db.get_value("Company", self.company, "default_laundry_item_group_cf")
                for d in folio.room_folio_split_bill_detail:
                    if d.item_group == laundry_item_group:
                        self.customer = d.customer
            else:
                self.customer = folio.customer
        if self.is_new() or not self.guest:
            for d in folio.room_guest_detail:
                self.guest = d.guest
                break
        self.create_sales_invoice()

    def on_submit(self):
        self.status == "IN"
        self.received_datetime = now_datetime()

    def make_delivery_and_invoice(self):
        self.status == "OUT"
        self.delivered_datetime = now_datetime()
        # create invoice
        self.create_sales_invoice()
        self.invoiced = 1

    def create_sales_invoice(self):
        si = frappe.new_doc("Sales Invoice")
        si.room_folio_cf = self.room_folio
        si.room_date_cf = nowdate()
        si.set_posting_time = 1
        si.posting_date = nowdate()

        si.company = self.company
        si.customer = self.customer
        si.selling_price_list = get_default_price_list(self.customer, self.company)
        si.debit_to = frappe.defaults.get_user_default('default_folio_receivable_account')
        si.cuurency = get_default_currency()
        si.conversion_rate = 1
        si.due_date = add_days(getdate(), 30)

        customer_details = get_party_details(party=self.customer, party_type="Customer")
        customer_details.update({
            "company": get_default_company(),
            "price_list": si.selling_price_list,
            "transaction_date": getdate()
        })
        for d in self.items:
            si.append("items", {
                "item_code": d.item,
                "qty": d.qty or 1,
                "rate": get_price_list_rate_for(customer_details, d.item) or 0.0
            })
        si.set_taxes()
        si.calculate_taxes_and_totals()
        si.set_missing_values(for_validate=True)
        si.insert()
        # si.submit()
        return si


def get_default_price_list(customer, company):
    company = company or get_default_company()
    default_price_list = frappe.db.sql("""
    select 
        COALESCE(cu.default_price_list,cug.default_price_list,sing.value) price_list
    from 
        tabCustomer cu
        inner join `tabCustomer Group` cug on cug.name = cu.customer_group
        cross join tabSingles sing on sing.field = 'selling_price_list'
        and sing.doctype = 'Selling Settings'
    where
        cu.name=%s""", (customer,))
    return default_price_list and default_price_list[0][0] or None
