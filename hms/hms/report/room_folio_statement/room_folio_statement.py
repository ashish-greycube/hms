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
        dict(label="Invoice", fieldname="invoice",
                     fieldtype="Link/Sales Invoice", width=110,),
        dict(label="Room No", fieldname="room_no",
                     fieldtype="Data", width=110,),
        dict(label="Room Type", fieldname="room_type",
                     fieldtype="Data", width=110,),
        dict(label="Date", fieldname="date",
                     fieldtype="Data", width=110,),
        dict(label="Charge Description", fieldname="description",
                     fieldtype="Data", width=200,),
        dict(label="Payment", fieldname="payment_entry",
                     fieldtype="Link/Payment Entry", width=130,),
        dict(label="Dr", fieldname="debit",
                     fieldtype="Currency", width=110,),
        dict(label="Cr", fieldname="credit",
                     fieldtype="Currency", width=110,),
    ]

def get_data(filters):
    data = frappe.db.sql("""
        select rf.customer,  rf.name folio, si.name invoice, '' payment_entry,
        rf.room_no, rm.room_type, coalesce(si.room_date_cf,si.posting_date) date, sit.item_name description,
        nullif(je.debit,0) debit, nullif(je.credit,0) credit
        from `tabRoom Folio HMS` rf 
        inner join `tabSales Invoice` si on si.room_folio_cf = rf.name
        inner join `tabSales Invoice Item` sit on sit.parent = si.name
        inner join `tabRoom HMS` rm on rm.name = rf.room_no
        left outer join 
        (
            select reference_name, credit, debit 
            from `tabJournal Entry Account` x 
            where reference_type = 'Sales Invoice'
            group by reference_name
        ) je on je.reference_name = si.name
        where si.docstatus = 1
        union all
        select pe.party, '' folio, '' invoice, pe.name payment_entry,
        '', '', pe.posting_date date, '' description, 
        if(payment_type='Paid', pe.base_paid_amount,0) debit, 
        if(payment_type='Receive', pe.base_paid_amount,0) credit 
        -- per.reference_doctype, per.reference_name reservation, 
        -- coalesce(so.room_no_cf,rf.room_no) room_no
        from `tabPayment Entry` pe
        inner join `tabPayment Entry Reference` per on per.parent = pe.name
        order by date
    """, filters, as_dict=True, debug=False)
    return data
