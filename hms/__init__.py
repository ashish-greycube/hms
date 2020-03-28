# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__version__ = '0.0.1'

import frappe
import erpnext


def set_session_defaults():

    for d in frappe.db.get_values('Company', {'name': erpnext.get_default_company()},
                                  ['default_customer_cf', 'default_folio_receivable_account_cf', 'default_desk_receivable_account_cf'], as_dict=1):
        frappe.defaults.set_user_default(
            "default_ngtd_customer", d.default_customer_cf)
        frappe.defaults.set_user_default(
            "default_folio_receivable_account", d.default_folio_receivable_account_cf)
        frappe.defaults.set_user_default(
            "default_desk_receivable_account", d.default_desk_receivable_account_cf)


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


def clear_company(company="Sun Hotel"):
    from erpnext.setup.doctype.company.delete_company_transactions import delete_company_transactions
    delete_company_transactions(company)
