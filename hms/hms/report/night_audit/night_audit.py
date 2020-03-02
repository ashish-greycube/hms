# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.utils import getdate, date_diff, add_to_date, add_days
import frappe


def execute(filters=None):
    columns, data = [], []
    return columns, data

# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt


def execute(filters=None):
    columns, data = get_data(filters)
    return columns, data


def get_data(filters):

    data = frappe.db.sql("""
select l.name, l.room_no, rf.room_type, l.status, l.parent folio, rf.customer,
rf.check_in, rf.check_out, rf.total_charges, rf.total_advance_paid, rf.balance, rg.guest, rg.mobile
from `tabRoom Ledger Entry HMS` l
inner join `tabRoom Folio HMS` rf on l.parenttype = 'Room Folio HMS' and rf.name = l.parent 
left outer join `tabRoom Guest Detail HMS` rg on rg.parent = rf.name
where l.date = %(room_date)s and rf.company = 'Sun Hotel'
order by room_type, room_no desc    
""", filters, as_dict=True, debug=True)

    columns = []
    # employee
    columns += [dict(label="Room No", fieldname="room_no",
                     fieldtype="Data", width=130, pinned='left', group="Room",
                     headerCheckboxSelection=True,
                     checkboxSelection=True)]
    columns += [dict(label="Room Type", fieldname="room_type",
                     fieldtype="Data", width=90, pinned='left', group="Room")]
    columns += [dict(label="Status", fieldname="status",
                     fieldtype="Data", width=90, pinned='left', group="Room")]
#
    columns += [dict(label="Folio", fieldname="folio",
                     fieldtype="Link/Room Folio HMS", width=130,)]
    columns += [dict(label="Guest", fieldname="guest",
                     fieldtype="Link/Contact", width=180,)]
    columns += [dict(label="Customer", fieldname="customer",
                     fieldtype="Link/Customer", width=180,)]
    columns += [dict(label="In", fieldname="check_in",
                     fieldtype="DateTime", width=140,)]
    columns += [dict(label="Out", fieldname="check_out",
                     fieldtype="DateTime", width=140,)]
    columns += [dict(label="Total", fieldname="total_charges",
                     fieldtype="Currency", width=100,)]
    columns += [dict(label="Advance", fieldname="total_advance_paid",
                     fieldtype="Currency", width=100,)]
    columns += [dict(label="Balance", fieldname="balance",
                     fieldtype="Currency", width=100,)]
    columns += [dict(label="Mobile", fieldname="mobile",
                     fieldtype="Data", width=120,)]

    return columns,  data
