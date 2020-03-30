# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import (
    getdate, date_diff, add_to_date, add_days, cint, flt, today)
import erpnext


def on_submit_sales_order(doc, method):
    from hms.hms.doctype.room_ledger_entry_hms.room_ledger_entry_hms import make_room_ledger_entry
    for d in [add_days(doc.check_in_cf, _)
              for _ in range(0, cint(doc.no_of_nights_cf))]:
        make_room_ledger_entry(date=d, room_no=doc.room_no_cf, reference_type=doc.doctype,
                               reference_name=doc.name, entry_type="Reservation")


def on_update_after_submit_sales_order(doc, method):
    frappe.db.sql(
        """update `tabRoom Ledger HMS` set status = 'Cancelled' 
        where parent = %s and parenttype='Sales Order'""", (doc.name,))
    add_room_ledger_entry(doc)


def on_cancel_sales_order(doc, method):
    frappe.db.sql("""
    update `tabRoom Ledger Entry HMS` 
    set status = 'Cancelled' 
    where parent = %s and parenttype='Sales Order'
    """, (doc.name,))


@frappe.whitelist()
def get_room_service_item(room):
    docs = frappe.db.sql_list("""select rt.service_item
from `tabRoom Type HMS` rt
inner join `tabRoom HMS` r on r.room_type = rt.name and r.name = %s""", (room,))
    return docs and docs[0]


@frappe.whitelist()
def make_room_folio(docname):
    so = frappe.get_doc("Sales Order", docname)
    folio = frappe.new_doc("Room Folio HMS")
    folio.update({
        "company": so.company,
        "naming_series": "HMS-RR-.YY.-",
        "company": so.company,
        "customer": so.customer,
        "room_no": so.room_no_cf,
        "check_in": so.check_in_cf,
        "check_out": so.check_out_cf,
    })
    folio.append("room_guest_detail", {
        "guest": so.guest_cf
    })
    # TODO: add advance payments
    folio.insert()
    return folio


@frappe.whitelist()
def get_reservation_details(room_no, date):
    data = frappe.db.sql("""
    select name, room_type, customer, '' guest, check_out, check_in, room_no,
    reservation, status, total_charges, total_advance_paid
    from `tabRoom Folio HMS`
    limit 1
    """, as_dict=True)
    return data and data[0] or {}


@frappe.whitelist()
def make_transfer_jv_to_sales_order(customer, amount_to_transfer, docname):
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = erpnext.get_default_company()
    je.posting_date = today()
    je.remark = f"Advance towards reservation for {customer}. Reservation#: {docname}"

    default_desk_account = frappe.defaults.get_user_default(
        'default_desk_receivable_account')

    je.append("accounts", {
        "account":  default_desk_account,
        "party_type": 'Customer',
        'party': customer,
        'reference_type': 'Sales Order',
        'reference_name': docname,
        'debit_in_account_currency': 0,
        'credit_in_account_currency': flt(amount_to_transfer),
        'is_advance': 'Yes'
    })

    je.append("accounts", {
        "account": default_desk_account,
        "party_type": 'Customer',
        'party': customer,
        'debit_in_account_currency': flt(amount_to_transfer),
        'credit_in_account_currency': 0
    })
    je.insert(ignore_permissions=True)
    je.submit()
