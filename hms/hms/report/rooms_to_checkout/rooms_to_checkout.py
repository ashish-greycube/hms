# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
    return get_columns(filters), get_data(filters)


def get_columns(filters):
    return [
        dict(label="Folio", fieldname="folio", fieldtype="Link/Room Folio HMS", width=140),
        dict(label="Room Type", fieldname="room_type", width=120),
        dict(label="Room #", fieldname="room_no", width=120),
        dict(label="Customer", fieldname="customer", fieldtype="Link/Customer", width=150),
        dict(label="Guest", fieldname="guest", fieldtype="Link/Contact", width=150),
        dict(label="Contact", fieldname="contact", width=120),
        dict(label="Check In", fieldname="check_in", width=120),
        dict(label="Check Out", fieldname="check_out", width=120),
        dict(label="Status", fieldname="status", width=120),
    ]
def get_data(filters):
    where_clause = ""
    if filters.get("status"):
        where_clause += " and f.status = %(status)s"
    return frappe.db.sql("""
    select 
        f.name folio, f.room_type, f.room_no, f.customer, 
        gu.guest, ct.mobile_no contact, 
        DATE_FORMAT(f.check_in, "%%d-%%m-%%y %%h:%%i") check_in, 
        DATE_FORMAT(f.check_out, "%%d-%%m-%%y %%h:%%i") check_out, 
        f.status  
    from 
        `tabRoom Folio HMS` f
        left outer join 
            `tabRoom Guest Detail HMS` gu on gu.parent = f.name and gu.idx = 1
        left outer join 
            tabContact ct on ct.name = gu.guest 
    where 
        f.docstatus = 1 and date(check_out) = %(check_out)s
    {where_clause} order by f.room_type, f.room_no, f.check_in, f.room_no""".format(where_clause=where_clause), filters)
