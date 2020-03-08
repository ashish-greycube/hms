
# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, date_diff, add_to_date, add_days
from pprint import pprint


def execute(filters=None):
    columns, data = get_data(filters)
    return columns, data


def get_first_of_year():
    from datetime import date
    return date(getdate().year, 1, 1)


def get_data(filters=None):

    filters = filters or {"from_date": get_first_of_year()}

    data = frappe.db.sql("""
select guest, f.customer, mobile, email, f.name, f.check_in, f.check_out, f.room_no, f.room_type, f.total_charges
from `tabRoom Guest Detail HMS` g
inner join `tabRoom Folio HMS` f on f.name = g.parent and f.docstatus <> 2
where f.check_in >= %(from_date)s
order by f.check_in, guest
    """, filters, as_dict=True, debug=True)

    columns = []
    # pinned columns
    columns += [dict(label="Guest Name", fieldname="guest",
                     fieldtype="Link/Contact", width=130,)]
    columns += [dict(label="Customer Name", fieldname="customer",
                     fieldtype="Link/Customer", width=130,)]
    columns += [dict(label="Mobile", fieldname="mobile",
                     fieldtype="Data", width=130,)]
    columns += [dict(label="Email", fieldname="email",
                     fieldtype="Data", width=130,)]
    columns += [dict(label="Check In", fieldname="check_in",
                     fieldtype="DateTime", width=100,)]
    columns += [dict(label="Check Out", fieldname="check_out",
                     fieldtype="DateTime", width=100,)]
    columns += [dict(label="Room", fieldname="room_no",
                     fieldtype="Link/Room HMS", width=130,)]
    columns += [dict(label="Room Type", fieldname="room_type",
                     fieldtype="Data", width=130,)]
    columns += [dict(label="Charges", fieldname="total_charges",
                     fieldtype="Currency", width=100,)]

    # print(columns, results)
    return columns, data
