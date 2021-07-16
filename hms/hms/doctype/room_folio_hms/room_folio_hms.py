# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from hms.hms.controllers.reservation import get_available_rooms
from frappe.utils import (
    get_datetime,
    formatdate,
    nowdate,
    flt,
    cint,
    today,
    date_diff,
    add_days,
    getdate,
    cstr,
    now,
    get_link_to_form,
    format_datetime,
)
from erpnext.accounts.party import get_party_account, get_party_bank_account
from frappe.contacts.doctype.contact.contact import (
    get_contact_details,
    get_default_contact,
)
from erpnext.accounts.utils import get_outstanding_invoices
import json
from hms.hms.doctype.room_status_ledger_entry_hms.room_status_ledger_entry_hms import (
    update_room_status_ledger,
)
from hms.hms.controllers.reservation import get_room_service_item
from erpnext.accounts.doctype.journal_entry.journal_entry import (
    get_default_bank_cash_account,
)
import erpnext
from six import iteritems, string_types
from frappe.utils.formatters import format_value
from erpnext.setup.doctype.item_group.item_group import get_child_item_groups
from hms.hms.report.night_audit.night_audit import validate_system_date
from erpnext.accounts.utils import get_balance_on


folio_checklist = {
    "guest_id": _("Please attach Identification for guest"),
    "advance_amount": _("Please make an advance payment for the folio."),
    "sign_in_sheet": _("Please create Sign In Sheet for guest."),
    "sign_in_sheet_incomplete": _("Please get Signature in Sign In Sheet."),
}


class RoomFolioHMS(Document):
    def before_insert(self):
        if getdate(self.check_in) == getdate():
            validate_system_date(getdate(), raise_exception=0)

    def before_update_after_submit(self):
        self.validate_extend_checkout()
        self.validate_room_change()

    def on_update_after_submit(self):
        self.update_charges_and_amounts()
        self.update_so_items()
        self.handle_room_change()

    def handle_room_change(self):
        if not self.flags or not self.flags.get("old_room_no"):
            return
            #
        from hms.hms.doctype.room_status_ledger_entry_hms.room_status_ledger_entry_hms import (
            update_room_status_ledger,
        )

        args = self.as_dict()
        args["old_room_no"] = self.flags.get("old_room_no")
        update_room_status_ledger(args, action="move")

    def validate_room_change(self):
        if self.db_get("room_no") == self.room_no:
            return
        args = {
            "item_code": self.room_package,
            "check_in": today(),
            "check_out": self.check_out,
            "company": self.company,
        }
        if not get_available_rooms("", self.room_no, "", 0, 1, args):
            frappe.throw(
                "Changed room %s is not available for the new dates."
                % (frappe.bold(self.room_no),)
            )
        self.flags.old_room_no = self.db_get("room_no")

    def validate_extend_checkout(self):
        """If checkout is extended, check room is available for extra days"""
        if get_datetime(self.check_out) > self.db_get("check_out"):

            if not get_available_rooms(
                "",
                self.room_no,
                "",
                0,
                1,
                {
                    "item_code": self.room_package,
                    "check_in": self.db_get("check_out"),
                    "check_out": self.check_out,
                    "company": self.company,
                },
            ):
                frappe.throw(
                    "Room %s is not available for the new dates."
                    % (frappe.bold(self.room_no),)
                )

    def update_so_items(self):
        """Update Sales Order Items if room package or Rate has changed since submit"""
        so = frappe.get_doc("Sales Order", self.reservation)
        updated_items, new_items = [], []
        for item in so.items:
            # ignore billed rows and rows where no change
            if (
                item.billed_amt
                # or (item.get("reservation_date_cf") < getdate())
                or (item.item_code == self.room_package and item.rate == self.room_rate)
            ):
                updated_items.append(
                    {
                        "item_code": item.item_code,
                        "rate": item.rate,
                        "qty": item.qty,
                        "docname": item.name,
                    },
                )
            else:
                updated_items.append(
                    {
                        "item_code": self.room_package,
                        "rate": self.room_rate,
                        "qty": item.qty,
                    },
                )
        # add rows for checkout date extended
        for d in range(
            date_diff(self.check_out, so.items[-1].get("reservation_date_cf"))
        ):
            updated_items.append(
                {
                    "item_code": self.room_package,
                    "rate": self.room_rate,
                    "qty": item.qty,
                }
            )

        from erpnext.controllers.accounts_controller import update_child_qty_rate

        trans_item = json.dumps(updated_items)
        update_child_qty_rate("Sales Order", trans_item, so.name)
        so.reload()

        for idx, d in enumerate(so.items):
            if not d.get("reservation_date_cf"):
                frappe.db.set_value(
                    "Sales Order Item",
                    d.name,
                    "reservation_date_cf",
                    add_days(self.check_in, idx),
                )
        # frappe.db.commit()
        so.reload()

    def validate(self):
        # check night audit completed for previous date
        # if self.is_new() and date_diff(getdate(), getdate(self.check_in)) > 0:
        # frappe.throw(_("Check In date cannot be earlier than today."))

        if self.is_new() and self.status == "Checked In":
            self.validate_room_reservation()
            self.validate_room_status()

        self.set_missing_values()
        self.validate_checklist()
        self.validate_duplicate_checkin()
        self.update_charges_and_amounts()

    def set_missing_values(self):
        contact_person = get_default_contact("Customer", self.customer)
        if contact_person:
            details = get_contact_details(contact_person)
            self.customer_email = details.get("contact_email")
            self.customer_mobile = details.get("contact_mobile") or details.get("phone")

    def validate_duplicate_checkin(self):
        for d in frappe.db.sql(
            """select name from `tabRoom Folio HMS`
        where reservation = %s and name <> %s limit 1""",
            (self.reservation, self.name),
        ):
            rf_link = get_link_to_form("Room Folio HMS", d[0])
            so_link = get_link_to_form("Sales Order", self.reservation)
            frappe.throw(
                _("Room Folio {} already created for reservation {}.").format(
                    rf_link, so_link
                )
            )
        for d in frappe.db.sql(
            """
select name
        from `tabRoom Folio HMS`
        where name <> %s
        and room_no = %s
        and status <> 'Checked Out'
        and not (check_in >= %s or check_out <= %s)
        limit 1""",
            (self.name, self.room_no, self.check_out, self.check_in),
        ):
            frappe.throw(
                _("Room Folio dates overlap with existing room folio {}.").format(
                    get_link_to_form("Room Folio HMS", d[0])
                )
            )

    def make_sign_in_sheet(self):
        from hms.hms.doctype.sign_in_sheet_hms.sign_in_sheet_hms import (
            make_sign_in_sheet,
        )

        return make_sign_in_sheet(self.name)

    def validate_room_reservation(self):
        """WHERE NOT (From_date > @RangeTill OR To_date < @RangeFrom)"""
        for d in frappe.db.sql(
            """
select name reservation, room_no_cf, check_in_cf, check_out_cf
        from `tabSales Order`
        where docstatus = 1 and room_no_cf = %s and name <> %s
        and not (check_in_cf >= %s or check_out_cf <= %s)
        """,
            (self.room_no, self.reservation, self.check_out, self.check_in),
            as_dict=True,
        ):
            frappe.throw(
                f"Reservation {d.reservation} exists for room {d.room_no} between {d.check_in_cf} and {d.check_out_cf} "
            )

    def validate_room_status(self):
        for d in frappe.db.sql(
            """
select status, reference_type, reference_name
        from `tabRoom Status Ledger Entry HMS`
        where room_no = %s and docstatus <> 2""",
            (self.room_no),
            as_dict=True,
        ):
            frappe.throw(f"Room {self.room_no} is {d.status} for {self.check_in} ")

    def validate_checklist(self):
        """
        1. Guest ID
        2. advance paid
        3. Sign In Sheet signed"""
        if cint(self.is_checklist_done):
            return ""

        checklist = []
        valid = frappe.db.sql(
            """
            select
            if(con.name is not null,1,0) guest_id,
            if(sg.name is not null,1,0) sign_in_sheet,
            if(sg.signature is not null, 1, 0) sign_in_sheet_incomplete
            from `tabRoom Folio HMS` f
            inner join tabCustomer cu on cu.name = f.customer
            inner join `tabSales Order` so on so.name = f.reservation
            left outer join tabContact con on con.name = so.guest_cf and con.image is not null
            left outer join `tabSign In Sheet HMS` sg on sg.name = f.sign_in_sheet
            where f.name = %s limit 1""",
            (self.name,),
            as_dict=True,
        )
        valid = (
            valid
            and valid[0]
            or {
                "advance_amount": 0,
                "guest_id": 0,
                "sign_in_sheet": 0,
                "sign_in_sheet_incomplete": 0,
            }
        )

        allow_checkin_without_advance = frappe.db.get_value(
            "Customer", self.customer, "allow_checkin_without_advance_cf"
        )
        if not cint(allow_checkin_without_advance):
            party_balance = get_party_balance(self.customer, self.company)
            valid["advance_amount"] = cint(party_balance <= 0)
        else:
            valid["advance_amount"] = 1

        if not valid:
            checklist = "<br>".join(folio_checklist.values())
        else:
            checklist = [
                folio_checklist.get(k) for k, v in valid.items() if not cint(v)
            ]

        if folio_checklist.get("sign_in_sheet") in checklist:
            checklist = [
                d
                for d in checklist
                if not d == folio_checklist.get("sign_in_sheet_incomplete")
            ]

        if not checklist:
            self.db_set("is_checklist_done", 1)
        else:
            return "<br>".join(checklist)

    def make_check_in(self):
        "check in"
        if not self.docstatus == 1:
            frappe.throw("Please submit Folio before Check In.")

        if getdate(self.check_in) == getdate():
            validate_system_date(getdate(), raise_exception=0)

        self.db_set("status", "Checked In", update_modified=True)
        update_room_status_ledger(self.as_dict(), action="check_in")

    def after_insert(self):
        self.create_charge_purchase(self.check_in)

    def on_cancel(self):
        "cancel"
        update_room_status_ledger(self.as_dict(), action="cancel")

    def create_charge_purchase(self, room_date):
        """create sales invoice for room_date date"""
        # if frappe.db.exists("Sales Invoice", {'room_folio_cf': self.name, 'room_date_cf': room_date, 'docstatus': 1}):
        #     frappe.throw(
        #         _("Sales Invoice already created for %s") % (room_date,))
        #     return

        from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

        out = make_sales_invoice(source_name=self.reservation)
        out.room_folio_cf = self.name
        out.due_date = max(getdate(self.check_out), getdate(now()))
        out.room_date_cf = room_date
        out.debit_to = frappe.defaults.get_user_default(
            "default_folio_receivable_account"
        )
        out.ignore_pricing_rule = 1
        items = self.get_invoice_items(room_date, out)
        out.items = []
        for d in items:
            out.append(
                "items",
                {
                    "qty": d.qty,
                    "sales_order": d.sales_order,
                    "so_detail": d.so_detail,
                    # set item as Room Folio room_package
                    "item_code": self.room_package,
                    # set rate as per rate in Room Folio
                    "rate": self.room_rate,
                },
            )
        out.remarks = "%s Room Charges: %s for %s" % (
            self.name,
            self.room_package,
            format_datetime(room_date, "d/m/Y"),
        )
        out.save()
        out.submit()
        return out.name

    def get_invoice_items(self, room_date, out):
        # remove lines for other dates in Sales Invoice, only bill for room_date
        so_items = frappe.db.get_all(
            "Sales Order Item",
            filters={
                "parent": self.reservation,
                "reservation_date_cf": room_date,
            },
            fields=["name", "qty"],
        )
        # qty will be less than 1 in cases where room rate was changed in Sales Invoice from Sales Order
        # filters dates that have already been invoiced
        items = [
            d
            for d in out.items
            if so_items and d.so_detail == so_items[0]["name"] and not d.qty < 1
        ]
        if not items:
            frappe.throw("No billable room charges for %s." % room_date)
        return items

    def make_check_out(self):
        self.update_charges_and_amounts()
        self.validate_room_folio_balance()
        self.db_set("status", "Checked Out", update_modified=True)
        if getdate(self.check_out) > getdate(now()):
            self.db_set("check_out", frappe.utils.now_datetime(), update_modified=True)
        update_room_status_ledger(self.as_dict(), action="check_out")
        return self.as_dict()

    def validate_room_folio_balance(self):
        if not self.master_folio:
            if not self.guest_purchase_balance == 0:
                frappe.throw(
                    _(
                        "Unsettled Guest Purchases in folio. Please settle outstanding amount {} before checkout."
                    ).format(format_value(self.guest_purchase_balance, df="Currency"))
                )

    def make_folio_advance_entry(self):
        args = json.loads(frappe.local.form_dict["args"] or "{}")
        mode_of_payment = args.get("mode_of_payment")
        amount = flt(args.get("paid_amount", 0))
        je = frappe.new_doc("Journal Entry")
        je.posting_date = nowdate()
        je.mode_of_payment = mode_of_payment
        je.voucher_type = "Journal Entry"
        je.company = self.company
        if not mode_of_payment == "Cash":
            je.cheque_no = args.get("reference_no")
            je.cheque_date = args.get("reference_date")

        cash_bank_account = get_default_bank_cash_account(
            self.company, mode_of_payment=mode_of_payment
        )

        folio_account = frappe.defaults.get_user_default(
            "default_folio_receivable_account"
        )

        if args.get("payment_type") == "Receive":
            je.remark = f"Room Folio advance ({mode_of_payment}) against: {self.name}"
            je.append(
                "accounts",
                {
                    "account": folio_account,
                    "party_type": "Customer",
                    "party": self.customer,
                    "reference_type": self.doctype,
                    "reference_name": self.name,
                    "is_advance": "Yes",
                    "credit_in_account_currency": amount,
                },
            )

            je.append(
                "accounts",
                {
                    "account": cash_bank_account.account,
                    "account_currency": cash_bank_account.account_currency,
                    "account_type": cash_bank_account.account_type,
                    "debit_in_account_currency": amount,
                },
            )
        else:
            je.remark = "Room Folio refund against: " + self.name
            je.append(
                "accounts",
                {
                    "account": cash_bank_account.account,
                    "account_currency": cash_bank_account.account_currency,
                    "account_type": cash_bank_account.account_type,
                    "credit_in_account_currency": amount,
                },
            )

            je.append(
                "accounts",
                {
                    "account": folio_account,
                    "party_type": "Customer",
                    "party": self.customer,
                    "debit_in_account_currency": amount,
                    "reference_type": self.doctype,
                    "reference_name": self.name,
                },
            )

        je.insert(ignore_permissions=True)
        je.submit()
        self.update_charges_and_amounts()
        frappe.msgprint(_("Payment created."), alert=True)

    def update_charges_and_amounts(self):
        # set totals from charge purchase and advances
        total_charges = frappe.db.sql(
            """
        select 
            sum(si.rounded_total)
        from 
            `tabSales Invoice` si
        where 
            si.docstatus = 1 
            and NULLIF(si.room_folio_cf, '') = %s""",
            (self.name),
        )
        total_charges = total_charges and flt(total_charges[0][0]) or 0
        self.db_set("total_charges", total_charges, update_modified=False)

        guest_purchase_balance = frappe.db.sql(
            """
        select sum(si.outstanding_amount)
        from `tabSales Invoice` si
        inner join `tabRoom Folio HMS` rf on rf.name = si.room_folio_cf and rf.customer <> si.customer
        where si.docstatus = 1 and si.is_pos = 1 and si.room_folio_cf = %s""",
            (self.name,),
        )
        if guest_purchase_balance:
            self.db_set(
                "guest_purchase_balance",
                guest_purchase_balance[0][0] or 0,
                update_modified=False,
            )

    def get_print_doc(self, only_charges=None):
        print_doc = get_folio_invoice_summary(self.name)
        if only_charges:
            print_doc["only_charges"] = get_charge_and_purchase(self.name)

        return print_doc


@frappe.whitelist()
def get_charge_and_purchase(docname):
    return frappe.db.sql(
        """
    select si.name, rf.name room_folio, rf.room_no, 
    date_format(coalesce(room_date_cf, posting_date),'%%d %%b, %%y') room_date_cf,
    date_format(posting_time,'%%H:%%i') posting_time, rounded_total, outstanding_amount,
    sit.items charges_for
    from `tabRoom Folio HMS` rf
    inner join `tabSales Invoice` si on si.docstatus = 1 and rf.name = ifnull(si.room_folio_cf, '')
    inner join (
        select parent, group_concat(distinct item_name) items
        from `tabSales Invoice Item`
        group by parent
    ) sit on sit.parent = si.name
    where rf.name = %(folio)s or rf.master_folio = %(folio)s""",
        dict(
            folio=docname,
        ),
        as_dict=True,
    )


@frappe.whitelist()
def make_transfer_jv(**args):
    args = frappe._dict(args)
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = erpnext.get_default_company()
    je.posting_date = today()
    je.remark = f"Ref. folio# {args.folio}. Transfer of funds for {args.customer}."

    against_voucher, against_voucher_type = None, None

    if args.get("transfer_type") == "Transfer to Room":
        debit_account = args.desk_account
        credit_account = args.folio_account
    else:
        credit_account = args.desk_account
        debit_account = args.folio_account

    against_voucher = args.folio
    against_voucher_type = "Room Folio HMS"

    je.append(
        "accounts",
        {
            "account": credit_account,
            "party_type": "Customer",
            "party": args.customer,
            "debit_in_account_currency": 0,
            "credit_in_account_currency": flt(args.amount_to_transfer),
            "is_advance": "Yes",
            "reference_name": against_voucher,
            "reference_type": against_voucher_type,
        },
    )

    je.append(
        "accounts",
        {
            "account": debit_account,
            "party_type": "Customer",
            "party": args.customer,
            "debit_in_account_currency": flt(args.amount_to_transfer),
            "credit_in_account_currency": 0,
            "reference_name": against_voucher,
            "reference_type": against_voucher_type,
        },
    )

    je.insert(ignore_permissions=True)
    je.submit()
    frappe.get_doc("Room Folio HMS", args.folio).update_charges_and_amounts()


@frappe.whitelist()
def get_nonreconciled_payment_entries(**args):
    """Only JVs against this room folio.
    Does not consider Payment Entries, other party advances without reference of this room_folio"""

    dr_or_cr = "credit_in_account_currency"
    journal_entries = frappe.db.sql(
        """
        select
            "Journal Entry" as reference_type, t1.name as reference_name,
            t1.posting_date, t1.remark as remarks, t2.name as reference_row,
            {dr_or_cr} as amount, t2.is_advance
        from
            `tabJournal Entry` t1, `tabJournal Entry Account` t2
        where
            t1.name = t2.parent and t1.docstatus = 1 and t2.docstatus = 1
            and t2.party_type = %(party_type)s and t2.party = %(party)s
            and t2.account = %(account)s and {dr_or_cr} > 0
            and t2.reference_type = 'Room Folio HMS' and t2.reference_name = %(room_folio)s
        order by t1.posting_date
    """.format(
            **{
                "dr_or_cr": dr_or_cr,
            }
        ),
        args,
        as_dict=1,
    )
    return list(journal_entries)


def update_checklist_status(sign_in_sheet=None):
    if sign_in_sheet:
        for d in frappe.db.sql(
            """select name
        from `tabRoom Folio HMS` where sign_in_sheet = %s""",
            (sign_in_sheet),
        ):
            frappe.get_doc("Room Folio HMS", d[0]).validate_checklist()


def on_submit_sales_invoice(doc, method=None):
    if doc.room_folio_cf:
        frappe.get_doc("Room Folio HMS", doc.room_folio_cf).update_charges_and_amounts()
    # set remarks
    if not doc.remarks or doc.remarks == "No Remarks":
        item_groups, items = [], []
        for d in doc.items:
            item_groups += [d.item_group]
            items += [d.item_name]
        doc.remarks = "{} - {}".format(", ".join(item_groups), ", ".join(items))


def on_validate_sales_invoice(doc, method=None):
    if doc.room_folio_cf and doc.is_pos:
        if doc.paid_amount > 0:
            frappe.throw("Cannot recieve payment when charging to folio.")
        doc.debit_to = frappe.defaults.get_user_default(
            "default_folio_receivable_account"
        )

        def _make_split_invoice(doc, customer, items):
            """split POS Invoice based on item-group set in reservation split bill."""
            si = frappe.new_doc("Sales Invoice")
            si.flags.is_split_bill = True
            si.room_folio_cf = doc.room_folio_cf
            si.posting_date = doc.posting_date or nowdate()
            si.company = doc.company
            si.customer = customer
            si.debit_to = doc.debit_to
            si.update_stock = doc.update_stock
            si.is_pos = doc.is_pos
            si.currency = doc.currency
            si.conversion_rate = doc.conversion_rate
            for d in doc.payments:
                si.append(
                    "payments",
                    {
                        "mode_of_payment": d.mode_of_payment,
                        "account": d.account,
                        "type": d.type,
                    },
                )
            for item in items:
                si.append(
                    "items",
                    {
                        "item_code": item.item_code,
                        "warehouse": item.warehouse,
                        "qty": item.qty,
                        "rate": item.rate,
                        "income_account": item.income_account,
                        "expense_account": item.expense_account,
                        "cost_center": item.cost_center,
                    },
                )
            si.calculate_taxes_and_totals()
            si.insert()
            si.submit()
            frappe.msgprint("Split Invoice %s created." % si.name, alert=True)

    if cint(doc.is_pos) and doc.room_folio_cf and not doc.flags.is_split_bill:
        customer_item_groups = frappe.db.sql(
            """
        select  a.customer, group_concat(a.item_group)
        from `tabRoom Folio Split Bill Detail HMS` a
        inner join `tabRoom Folio HMS` b on b.name = a.parent
        and b.name = %s and a.customer <> %s
        group by a.customer""",
            (doc.room_folio_cf, doc.customer),
            as_dict=False,
        )
        if customer_item_groups:
            split_invoices = []
            for customer, item_groups in customer_item_groups:
                _groups = item_groups.split(",")
                for g in item_groups.split(","):
                    _groups += get_child_item_groups(g)
                items = [i for i in doc.items if i.item_group in _groups]
                if items:
                    split_invoices.append((customer, items))
                    doc.items = [i for i in doc.items if not i.item_group in _groups]

            if not doc.items:
                doc.customer = split_invoices[0][0]
                doc.update(
                    {
                        "title": None,
                        "customer_name": None,
                        "contact_person": None,
                        "contact_display": None,
                        "contact_mobile": None,
                        "contact_email": None,
                    }
                )
                doc.set_missing_values()
                doc.items = split_invoices[0][1]
                split_invoices = split_invoices[1:]

            doc.calculate_taxes_and_totals()
            for d in split_invoices:
                _make_split_invoice(doc, d[0], d[1])


@frappe.whitelist()
def update_room_folio_status(name, status):
    frappe.db.set_value("Room Folio HMS", name, "status", status, update_modified=True)


@frappe.whitelist()
def get_guest_purchase(room_folio):
    return frappe.db.sql(
        """
        select si.name invoice, concat(si.posting_date, ' ', left(si.posting_time,5)) posting_date,
        si.base_rounded_total, si.remarks, si.customer_name, si.status, group_concat(distinct sit.item_group) items
        from `tabSales Invoice` si
        inner join `tabRoom Folio HMS` rf on rf.name = si.room_folio_cf and rf.customer <> si.customer
        inner join `tabSales Invoice Item` sit on sit.parent = si.name
        where si.docstatus = 1 and si.is_pos = 1 and si.room_folio_cf = %s
        group by si.name, si.posting_date, si.posting_time, si.base_rounded_total,
        si.remarks, si.customer_name, si.status
        """,
        (room_folio),
        as_dict=True,
    )


@frappe.whitelist()
def get_folio_invoice_summary(docname):
    doc = frappe.get_doc("Room Folio HMS", docname).as_dict()

    print_args = dict()

    print_args["company_description"] = frappe.db.get_value(
        "Company", doc["company"], "company_description"
    )

    print_args["currency"] = frappe.get_cached_value(
        "Company", doc["company"], "default_currency"
    )

    folios = frappe.db.sql(
        """
        select f.name folio, r.room_no, f.check_in, f.check_out, 
        f.customer, case when f.master_folio is null then 1 else 0 end is_master,
        f.total_charges, f.outstanding_charges
        from `tabRoom Folio HMS` f
        inner join `tabRoom HMS` r on r.name = f.room_no
        where f.name = %(name)s or f.master_folio = %(name)s
    """,
        {"name": docname},
        as_dict=True,
    )

    print_args["folios"] = folios

    filters = dict(
        room_folio=doc["name"],
        company=doc["company"],
        party_type="Customer",
        party=doc["customer"],
        account=frappe.defaults.get_user_default("default_folio_receivable_account"),
    )

    items = frappe.db.sql(
        """
    with data as
    (
        select si.name invoice,
    coalesce(si.room_date_cf, si.posting_date) date, rm.room_no, sit.voucher, si.base_rounded_total charges,
    0 credits, 0 balance, rm.name room_name, si.creation
            from
                `tabSales Invoice` si
                inner join (
                        select parent, group_concat(item.item_code) voucher from `tabSales Invoice Item` item
                        group by parent) sit on sit.parent = si.name
                inner join `tabRoom Folio HMS` fo on fo.name = si.room_folio_cf
                inner join `tabRoom HMS` rm on rm.name = fo.room_no
            where
                si.docstatus = 1 and si.room_folio_cf = %(room_folio)s
    union all
    select '' invoice, t1.posting_date `date`,
    rm.room_no, t1.remark as voucher,
    0 charges, credit_in_account_currency - debit_in_account_currency as credits,
    0 balance,  rm.name room_name,
    t1.creation
            from
                `tabJournal Entry` t1, `tabJournal Entry Account` t2,
                `tabRoom Folio HMS` fo, `tabRoom HMS` rm
            where
                t1.name = t2.parent and t1.docstatus = 1 and t2.docstatus = 1
                and t2.party_type = 'Customer' and t2.party = %(party)s
                and t2.account = %(account)s
                and t2.reference_type = 'Room Folio HMS' and t2.reference_name = %(room_folio)s
                and fo.name = t2.reference_name
                and rm.name = fo.room_no
    order by creation
    )
select invoice, date, room_no, voucher, charges, credits, 
sum(credits-charges) over (order by creation) balance from data
""",
        filters,
        as_dict=True,
    )

    print_args["items"] = items
    print_args["gl_items"] = get_folio_gl(docname)

    invoice_html = ""
    for d in items:
        if not d["invoice"]:
            continue
        invoice_html += frappe.get_print(
            "Sales Invoice", d["invoice"], "Standard", no_letterhead=0
        )

    print_args["invoice_html"] = invoice_html or "**" * 10

    return print_args

    # html = frappe.render_template("templates/folio_invoice_summary.html", doc)
    # return html


@frappe.whitelist()
def get_party_balance(customer, company=None, posting_date=None):
    return get_balance_on(
        party_type="Customer",
        party=customer,
        date=posting_date or today(),
        company=company or erpnext.get_default_company(),
    )


@frappe.whitelist()
def get_folio_outstanding_charges(folio):
    outstanding_amount = frappe.db.sql(
        """
    select 
        sum(outstanding_amount)
    from 
        `tabSales Invoice`
    where 
        room_folio_cf = %s
    """,
        (folio),
    )
    return outstanding_amount and flt(outstanding_amount[0][0]) or 0


@frappe.whitelist()
def get_advance_against_reservation(folio):
    advance_amount = frappe.db.sql(
        """
            select 
                coalesce(so.advance_paid,0)
            from 
                `tabRoom Folio HMS` rf
                left outer join `tabSales Order` so on so.name = rf.reservation
            where
                rf.name = %s
    """,
        (folio),
    )
    return advance_amount and flt(advance_amount[0][0]) or 0


@frappe.whitelist()
def allow_check_in(customer, company):
    if frappe.db.get_value("Customer", customer, "allow_checkin_without_advance_cf"):
        return 1
    return get_party_balance(customer, company) <= 0


@frappe.whitelist()
def allow_check_out(folio, customer, company):
    if (
        frappe.db.get_value(
            "Customer", customer, "allow_checkout_without_settlement_cf"
        )
        or flt(frappe.db.get_value("Room Folio HMS", folio, "outstanding_charges")) == 0
        or cint(get_party_balance(customer, company) <= 0)
    ):
        return 1
    return 0


def get_folio_gl(folio):
    filters = frappe.db.sql(
        """
    select 
        rf.company, rf.customer party, 'Customer' party_type, 
        DATE_FORMAT(coalesce(so.transaction_date, date(rf.check_in)),'%%Y-%%m-%%d') from_date,
        DATE_FORMAT(curdate(),'%%Y-%%m-%%d') to_date
    from 
        `tabRoom Folio HMS` rf
    left outer join 
        `tabSales Order` so on so.name = rf.reservation
    where rf.name = %(folio)s""",
        dict(folio=folio),
        as_dict=True,
    )

    folio_vouchers = frappe.db.sql(
        """
select 
    distinct j.name
from
    `tabJournal Entry Account` ea
    inner join `tabJournal Entry` j on j.name = ea.parent
    inner join `tabSales Invoice` si on si.name = ea.reference_name 
    and si.room_folio_cf = %(folio)s
    where 
        j.voucher_type = 'Journal Entry' and ea.reference_type = 'Sales Invoice'
union
select 
    distinct j.name
from
    `tabJournal Entry Account` ea
    inner join `tabJournal Entry` j on j.name = ea.parent
    where 
        j.voucher_type = 'Journal Entry' and ea.reference_type = 'Room Folio HMS' 
        and ea.reference_name = %(folio)s
union
select 
    distinct per.parent
from
    `tabPayment Entry Reference` per
inner join `tabPayment Entry` pe on pe.name = per.parent
where 
    per.reference_doctype = 'Sales Order' 
    and exists (select 1 from `tabRoom Folio HMS` x where x.reservation = per.reference_name 
    and x.name = %(folio)s)
union
select 
    distinct per.parent
from
    `tabPayment Entry Reference` per
inner join `tabPayment Entry` pe on pe.name = per.parent
where 
    per.reference_doctype = 'Sales Invoice' 
    and exists (select 1 from `tabSales Invoice` x where x.name = per.reference_name 
    and x.room_folio_cf = %(folio)s)
union 
select 
    name
from 
    `tabSales Invoice` si
where 
    si.room_folio_cf = %(folio)s""",
        dict(folio=folio),
    )

    sales_invoice_remarks = frappe.db.sql(
        """
    select 
        si.name, t.description
    from 
        `tabSales Invoice` si
    inner join 
    (
        select parent, 
        concat(
        group_concat(distinct item_group SEPARATOR ', ') , ' - ',
        group_concat(distinct item_code SEPARATOR ', ')) description
        from `tabSales Invoice Item`
        group by parent
    ) t on t.parent = si.name
    where si.room_folio_cf = %(folio)s""",
        dict(folio=folio),
    )
    sales_invoice_remarks = {k: v for (k, v) in sales_invoice_remarks}

    voucher_rooom_map = frappe.db.sql(
        """
    select 
        si.name voucher_no, rf.room_no
    from 
        `tabSales Invoice` si
        inner join `tabRoom Folio HMS` rf on rf.name = si.room_folio_cf
    union
    select 
        ea.parent, group_concat(distinct rf.room_no) room_no
    from 
        `tabJournal Entry Account` ea
        inner join `tabRoom Folio HMS` rf on rf.name = ea.reference_name
        group by ea.parent
    union
    select 
        ea.parent, group_concat(distinct rf.room_no) room_no
    from 
        `tabJournal Entry Account` ea
        inner join `tabSales Invoice` si on si.name = ea.reference_name
        inner join `tabRoom Folio HMS` rf on rf.name = si.room_folio_cf
        group by ea.parent
    union 
    select 
        per.parent, group_concat(distinct rf.room_no) room_no
    from
        `tabPayment Entry Reference` per
        inner join `tabSales Order` so on so.name = per.reference_name
        inner join `tabRoom Folio HMS` rf on rf.reservation = so.name
        group by per.parent
    union 
    select 
        per.parent, group_concat(distinct rf.room_no) room_no
        from `tabPayment Entry Reference` per
        inner join `tabSales Invoice` si on si.name = per.reference_name
        inner join `tabRoom Folio HMS` rf on rf.name = si.room_folio_cf
        group by per.parent
    """,
        dict(
            folio=folio,
        ),
    )
    voucher_rooom_map = {k: v for (k, v) in voucher_rooom_map}

    from erpnext.accounts.report.general_ledger.general_ledger import execute

    filters = filters[0]
    filters["party"] = [filters["party"]]
    filters["group_by"] = "Group by Voucher (Consolidated)"
    _, data = execute(filters)

    results = []
    for d in data:
        if "Closing" in d.account or "Total" in d.account:
            continue
        if not (d.voucher_no,) in folio_vouchers and not d.account == "'Opening'":
            continue
        item = dict(
            debit=d.debit,
            credit=d.credit,
            balance=d.balance,
            voucher_no=d.voucher_no or "",
            posting_date=d.posting_date,
            remarks=d.remarks or d.account,
        )
        if d.voucher_type == "Sales Invoice":
            item["remarks"] = sales_invoice_remarks.get(d.voucher_no)
        if voucher_rooom_map.get(d.voucher_no):
            item["room_no"] = voucher_rooom_map.get(d.voucher_no).split("-")[0]

        results.append(item)
    return results


def on_cancel_sales_invoice(doc, method=None):
    if doc.get("room_folio_cf"):
        frappe.get_doc(
            "Room Folio HMS", doc.get("room_folio_cf")
        ).update_charges_and_amounts()
