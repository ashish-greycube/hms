# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import nowdate
from erpnext.accounts.party import get_party_account, get_party_bank_account
from erpnext.accounts.utils import get_outstanding_invoices
import json
from hms.hms.doctype.room_ledger_entry_hms.room_ledger_entry_hms import make_room_ledger_entry
from hms.hms.doctype.room_status_ledger_entry_hms.room_status_ledger_entry_hms import update_room_status_ledger
from hms.hms.controllers.reservation import get_room_service_item


class RoomFolioHMS(Document):
    def validate(self):
        if self.is_new() and self.status == "Checked In":
            self.validate_room_reservation()
            self.validate_room_status()

    def validate_room_reservation(self):
        """WHERE NOT (From_date > @RangeTill OR To_date < @RangeFrom)"""
        for d in frappe.db.sql("""
        select name reservation, room_no_cf, check_in_cf, check_out_cf
        from `tabSales Order`
        where docstatus = 1 and room_no_cf = %s and name <> %s
        and not (check_in_cf >= %s or check_out_cf <= %s)
        """, (self.room_no, self.reservation, self.check_out, self.check_in), as_dict=True):
            frappe.throw(
                f"Reservation {d.reservation} exists for room {d.room_no} between {d.check_in_cf} and {d.check_out_cf} ")

    def validate_room_status(self):
        for d in frappe.db.sql("""
        select status, reference_type, reference_name
        from `tabRoom Status Ledger Entry HMS`
        where room_no = %s and docstatus <> 2""", (self.room_no), as_dict=True):
            frappe.throw(
                f"Room {self.room} is {d.status} for {self.check_in} ")

    def after_insert(self):
        "check in"
        make_room_ledger_entry(date=self.check_in, room_no=self.room_no, reference_type=self.doctype,
                               reference_name=self.name, entry_type="Room Folio Check In")
        update_room_status_ledger(self.as_dict(), action="check_in")
        self.create_charge_purchase(self.check_in)

    def create_charge_purchase(self, room_date):
        """create sales invoice for room_date date"""
        if not frappe.db.sql("""
        select 1 from `tabSales Invoice` where room_folio_cf = %s and room_date_cf = %s limit 1
        """, (self.name, room_date), debug=True):
            si_doc = frappe.new_doc('Sales Invoice')
            si_doc.room_folio_cf = self.name
            si_doc.customer = self.customer
            si_doc.due_date = self.check_out
            si_doc.room_date_cf = room_date
            item = si_doc.append("items")
            item.set('item_code', get_room_service_item(self.room_no))
            item.set("qty", 1)
            si_doc.save()
            return si_doc.name

    def make_check_out(self):
        self.validate_billing()
        self.status = "Checked Out"
        self.save()
        make_room_ledger_entry(date=self.check_out, room_no=self.room_no, reference_type=self.doctype,
                               reference_name=self.name, entry_type="Room Folio Check Out")
        update_room_status_ledger(self.as_dict(), action="check_out")
        return self.as_dict()

    def validate_billing(self):
        pass

    def set_advances(self):
        pass

    def get_payment_entry(self):
        pe = frappe.new_doc("Payment Entry")
        pe.party_type = "Customer"
        pe.payment_type = "Receive"
        pe.posting_date = nowdate()
        pe.company = self.company
        pe.party = self.customer
        pe.paid_to = "Bank Of Nigeria - SH"
        pe.paid_amount = self.balance

        for doc in get_outstanding_invoices("Customer", self.customer, account="Debtors - SH"):
            pe.append("references", {
                'reference_doctype': doc["voucher_type"],
                'reference_name': doc["voucher_no"],
                "due_date": doc.get("due_date"),
                'total_amount': doc.get('invoice_amount'),
                'outstanding_amount': doc.get('outstanding_amount'),
                'allocated_amount': doc.get('outstanding_amount'),
            })

        pe.setup_party_account_field()
        pe.set_missing_values()
        return pe


@frappe.whitelist()
def get_charge_and_purchase(docname):
    return frappe.db.sql("""
    select name, room_date_cf, posting_time, rounded_total, outstanding_amount
    from `tabSales Invoice` i
    where ifnull(i.room_folio_cf,'') = %s
    """, (docname, ), as_dict=True)
