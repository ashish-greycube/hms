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
    from hms.hms.controllers.reservation import make_transfer_jv_to_sales_order, get_reservation_details
    # make_transfer_jv_to_sales_order(
    #     customer="Vijay Malaya", amount_to_transfer=2000, docname="SAL-ORD-2020-00013")
    # return get_reservation_details("301-SH", "2020-03-29")
    from hms.hms.controllers.reservation import get_reservation_items
    items = get_reservation_items(
        room_no="301-SH", check_in="2020-04-04", check_out="2020-04-06", customer='NGTD Customer')
    print(items)


def delete_doctypes(doctypes=[], company_name="Sun Hotel"):
    from erpnext.setup.doctype.company.delete_company_transactions import delete_for_doctype
    doctypes = ["Journal Entry"]
    for doctype in doctypes:
        delete_for_doctype(doctype, company_name)
