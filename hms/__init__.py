# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__version__ = '0.0.1'

import frappe


def clear():
    for doctype in ["Sales Invoice", "Journal Entry", "Payment Entry", "Room Folio HMS", "Sales Order"]:
        for d in frappe.db.get_all(doctype, fields=['name', 'docstatus'], filters={}):
            print(f"Deleting {doctype} {d.name}")
            if d.docstatus == 1:
                frappe.get_doc(doctype, d.name).cancel()
            frappe.delete_doc(doctype, d.name)

    for d in ["Room Ledger Entry HMS", "Room Status Ledger Entry HMS"]:
        print(f"Deleting {d}")
        frappe.db.sql("delete from `tab{}`".format(d))

    frappe.db.commit()
