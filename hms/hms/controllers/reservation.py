# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days


def on_submit_sales_order(doc, method):
    add_room_ledger_entry(doc)


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


def add_room_ledger_entry(doc):
    for d in [add_days(doc.check_in_cf, _)
              for _ in range(0, doc.no_of_nights_cf)]:
        frappe.get_doc({
            "doctype": "Room Ledger Entry HMS",
            "parenttype": "Sales Order",
            "parent": doc.name,
            "date": d,
            "room_no": doc.room_no_cf,
            "status": "Reserved"
        }).insert(ignore_permissions=True)


@frappe.whitelist()
def get_room_service_item(room):
    docs = frappe.db.sql_list("""select rt.service_item
from `tabRoom Type HMS` rt
inner join `tabRoom HMS` r on r.room_type = rt.name and r.name = %s""", (room,))
    return docs and docs[0]
