# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, add_to_date, add_days, cint


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
