# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, date_diff, add_to_date, add_days


def execute(filters=None):
    columns, data = get_data(filters)
    return columns, data


def get_data(filters):
    start_date, end_date = filters.get("date_range")
    # start_date, end_date = '2020-02-19', '2020-02-28'

    columns_clause = []

    for d in range(date_diff(end_date, start_date)+1):
        curdate = add_to_date(start_date, days=d, as_string=True)
        columns_clause.append(
            ", max(case when t1.date = '%s' then coalesce(t1.name,'') else '' end) `%s`" % (curdate, curdate,))

    data = frappe.db.sql("""
    select t.name, t.room_type, t.room_no
    {columns_clause}
    from `tabRoom HMS` t
    left outer join `tabRoom Ledger Entry HMS` t1 on t1.room_no = t.name
    group by t.name, t.room_type, t.room_no
    """.format(columns_clause=" ".join(columns_clause)), as_dict=True, debug=True)

    columns = []
    # employee
    columns += [dict(label="Room", fieldname="name",
                     fieldtype="Link/Room HMS", width=130, pinned='left', group="Room")]
    columns += [dict(label="Room Type", fieldname="room_type",
                     fieldtype="Data", width=130, pinned='left', group="Room")]
    columns += [dict(label="Room No", fieldname="room_no",
                     fieldtype="Data", width=130, pinned='left', group="Room")]
    for d in [x for x in data[0] if x not in ["name", "room_type", "room_no"]]:
        columns += [dict(label=d, fieldname=d,
                         fieldtype="Data", width=120, )]

    return columns,  data


@frappe.whitelist()
def get_frontdesk(start_date=None, end_date=None, room_type=None):
    start_date, end_date = '2020-02-19', '2020-02-27'

    columns = []

    for d in range(date_diff(end_date, start_date)+1):
        curdate = add_to_date(start_date, days=d, as_string=True)
        columns.append(", coalesce(t1.status,'') `%s`" % (curdate,))

    data = frappe.db.sql("""
    select t.name, t.room_type, t.room_no
    {columns}
    from `tabRoom HMS` t
    left outer join `tabRoom Ledger Entry HMS` t1 on t1.room_no = t.name
    """.format(columns=" ".join(columns)), as_dict=True, debug=True)

    return data
