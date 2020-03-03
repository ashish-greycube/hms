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


class RoomFolioHMS(Document):

    def make_check_out(self):
        frappe.get_doc({
            "doctype": "Room Ledger Entry HMS",
            "parenttype": "Room Folio HMS",
            "parent": self.name,
            "date": self.check_out,
            "room_no": self.room_no,
            "status": "Check Out"
        }).insert(ignore_permissions=True)
        self.status = "Checked Out"
        self.save()
        return self.as_dict()

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
    select name, posting_date, posting_time, rounded_total, outstanding_amount
    from `tabSales Invoice` i
    where ifnull(i.room_folio_cf,'') = %s
    """, (docname, ), as_dict=True)
