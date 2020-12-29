# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, date_diff, add_to_date, add_days
from pprint import pprint


def execute(filters=None):
    columns, data = get_data(filters)
    return columns, data


def get_data(filters=None):
    data = frappe.db.sql("""
select name, first_name , last_name , gender ,
mobile_no , email_id , status 
from tabContact""", filters, as_dict=True, debug=False)

    columns = []
    # pinned columns
    columns += [dict(label="Guest Name", fieldname="name",
                     fieldtype="Link/Contact", width=230,)]
    columns += [dict(label="First Name", fieldname="first_name", width=130,)]
    columns += [dict(label="Last Name", fieldname="last_name", width=130,)]
    columns += [dict(label="M/F", fieldname="gender", width=130,)]
    columns += [dict(label="Mobile", fieldname="mobile", width=130,)]
    columns += [dict(label="Email", fieldname="email_id", width=190,)]
    columns += [dict(label="Status", fieldname="status", width=130,)]

    # print(columns, results)
    return columns, data
