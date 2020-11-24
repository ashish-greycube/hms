# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.utils import getdate, date_diff, add_to_date, add_days
import frappe
import json
from six import string_types, iteritems

def execute(filters=None):
    columns, data = get_columns(filters), get_data(filters)
    return columns, data


def get_columns(filters):
    return [
        dict(label="Folio", fieldname="folio",
                     fieldtype="Link/Room Folio HMS", width=130,),
        dict(label="Customer", fieldname="customer",
                     fieldtype="Link/Customer", width=130,),
        dict(label="Invoice", fieldname="invoice",
                     fieldtype="Link/Sales Invoice", width=110,),
        dict(label="Room No", fieldname="room_no",
                     fieldtype="Data", width=110,),
        dict(label="Room Type", fieldname="room_type",
                     fieldtype="Data", width=110,),
        dict(label="Date", fieldname="date",
                     fieldtype="Data", width=110,),
        dict(label="Description", fieldname="description",
                     fieldtype="Data", width=200,),
        dict(label="Payment", fieldname="payment_entry",
                     fieldtype="Link/Payment Entry", width=130,),
        dict(label="Dr", fieldname="debit",
                     fieldtype="Currency", width=110,),
        dict(label="Cr", fieldname="credit",
                     fieldtype="Currency", width=110,),
    ]

def get_data(filters):
    where_clause = []
    if filters.get("company"):
        where_clause += ["si.company = %(company)s"]
    if filters.get("customer"):
        where_clause += ["si.customer = %(customer)s"]
    if filters.get("from_date"):
        where_clause += ["rf.check_in >= %(from_date)s"]
    if filters.get("to_date"):
        where_clause += ["rf.check_out <= %(to_date)s"]
    if filters.get("status"):
        where_clause += ["rf.status = %(status)s"]
    if filters.get("room_folio"):
        where_clause += ["rf.name = %(room_folio)s"]
    where_clause = " and " + " and ".join(where_clause) if where_clause else ""

    charges = frappe.db.sql("""
    select rf.customer,  rf.name folio, si.name invoice,rf.room_no, rm.room_type,
    coalesce(si.room_date_cf,si.posting_date) date, sit.item_name description,
    if(si.is_return=0,si.base_rounded_total,0) debit, if(si.is_return=1,si.base_rounded_total,0) credit
    from `tabRoom Folio HMS` rf
        inner join `tabSales Invoice` si on si.room_folio_cf = rf.name
        inner join (select parent, group_concat(item_name) item_name from `tabSales Invoice Item`
        group by parent) sit on sit.parent = si.name
        inner join `tabRoom HMS` rm on rm.name = rf.room_no
    where si.docstatus = 1  {where_clause}
    order by si.posting_date
    """.format(where_clause=where_clause), filters, as_dict=True, debug=False)

    where_clause = []
    if filters.get("company"):
        where_clause += ["pe.company = %(company)s"]
    if filters.get("customer"):
        where_clause += ["pe.party = %(customer)s"]
    if filters.get("from_date"):
        where_clause += ["pe.posting_date >= %(from_date)s"]
    if filters.get("to_date"):
        where_clause += ["pe.posting_date <= %(to_date)s"]
    where_clause = " and " + " and ".join(where_clause) if where_clause else ""

    payments = frappe.db.sql("""
    select pe.party customer, pe.name payment_entry, pe.posting_date date,
        concat_ws(' ', pe.mode_of_payment, concat(' - ', pe.reference_no)) description,
        if(payment_type='Paid', pe.base_paid_amount,0) debit,
        if(payment_type='Receive', pe.base_paid_amount,0) credit
    from `tabPayment Entry` pe
        inner join `tabPayment Entry Reference` per on per.parent = pe.name
    where pe.docstatus = 1 {where_clause}
    order by date
    """.format(where_clause=where_clause), filters, as_dict=True, debug=False)

    data = sorted(charges + payments, key=lambda x: x.date)

    total = [{
       "payment": "Total",
       "debit": sum([d.get("debit", 0) or 0 for d in data]),
       "credit": sum([d.get("credit", 0) or 0 for d in data]),
    }]

    return data + total
