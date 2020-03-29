# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__version__ = '0.0.1'

import frappe
import erpnext
from frappe.utils import (today, cint, flt)


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


def delete_company_transactions(company_name="Sun Hotel"):
    from erpnext.setup.doctype.company.delete_company_transactions import (
        delete_for_doctype, clear_notifications, delete_bins, delete_lead_addresses)
    doc = frappe.get_doc("Company", company_name)

    delete_bins(company_name)
    delete_lead_addresses(company_name)

    exclude = ("Account", "Cost Center", "Warehouse", "Budget",
               "Party Account", "Employee", "Sales Taxes and Charges Template",
               "Purchase Taxes and Charges Template", "POS Profile", 'BOM',
               #
               'Room Type HMS', 'Room HMS'
               )

    for doctype in frappe.db.sql_list("""select parent from
    tabDocField where fieldtype='Link' and options='Company'"""):
        if doctype not in exclude:
            delete_for_doctype(doctype, company_name)

    # reset company values
    doc.total_monthly_sales = 0
    doc.sales_monthly_history = None
    doc.save()
    # Clear notification counts
    clear_notifications()


def test():
    from hms.hms.doctype.room_folio_hms.room_folio_hms import make_transfer_jv
    args = {
        "customer": "Tata Airlines",
        "transfer_type": "Transfer to Desk",
        "amount_to_transfer": "1000",
        "desk_account": "Debtors - SH",
        "folio_account": "Room Folio Debtors - SH",
        "folio": "HMS-RR-20-00005",
        # "desk_account_balance": "-15",
        # "folio_account_balance": "-11985",
    }

    make_transfer_jv(**args)


def delete_doctypes(doctypes=[], company_name="Sun Hotel"):
    from erpnext.setup.doctype.company.delete_company_transactions import delete_for_doctype
    doctypes = ["Journal Entry"]
    for doctype in doctypes:
        delete_for_doctype(doctype, company_name)
