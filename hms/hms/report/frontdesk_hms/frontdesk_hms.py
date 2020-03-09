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
    if not filters:
        filters = {}
        filters["date_range"] = ["2020-03-09", "2020-03-09"]
    filters["from_date"] = filters.get("date_range",)[0]
    filters["to_date"] = filters.get("date_range",)[1]

    data = frappe.db.sql("""
            select d.date, r.name name, r.room_no room_no, r.room_type, c.room_status,
            case
            when a.name is not null  and a.status='Checked In' then 'hms-in-house'
            when a.name is null and b.name is not null then 'hms-reserved'
            when d.date = curdate() then concat('hms-',coalesce(lower(c.room_status),''))
            else '' end status,
            coalesce(a.customer,b.customer) customer,
            coalesce(gd.guest, b.guest) guest,
            a.name folio, b.name `reservation`
            -- ,a.*, b.* 
            from 
            `tabDate Lookup HMS` d
            cross join `tabRoom HMS` r
            left outer join 
            (
                -- room folio
                select fo.room_no, fo.check_in, fo.check_out, fo.customer, fo.name, fo.status
                from `tabRoom Folio HMS` fo
                where not (fo.check_in >= %(to_date)s OR fo.check_out <= %(from_date)s)
                -- and fo.status = 'Checked In' 
            ) a on d.date BETWEEN a.check_in and a.check_out and r.name = a.room_no
            left outer join `tabRoom Guest Detail HMS` gd on gd.name = (
                select x.name from `tabRoom Guest Detail HMS` x 
                where x.parent = a.name limit 1
            )
            left outer join
            (
                -- reservation
                select so.name, so.room_no_cf room_no, so.check_in_cf check_in, so.check_out_cf check_out, so.guest_cf guest, so.customer
                from `tabSales Order` so
                where not (so.check_in_cf >= %(to_date)s OR so.check_out_cf <= %(from_date)s)
                and not exists (select 1 from `tabRoom Folio HMS` x where x.reservation = so.name)
            ) b on d.date BETWEEN b.check_in and b.check_out and r.name = b.room_no
            left outer join 
            (
                -- room status ledger: Dirty/Occupied/OOO/OOS
                select room_no, status, reference_type, reference_name, status room_status
                from `tabRoom Status Ledger Entry HMS`
                where docstatus <> 2
            ) c on c.room_no = r.name -- and d.date = curdate()
            where d.date BETWEEN %(from_date)s and %(to_date)s
            order by d.date, r.room_type, r.room_no
    """, filters, as_dict=True, debug=1)

    rows = {}
    for i, d in enumerate(data):
        tmp = rows.setdefault(d['name'], d)
        col = d['date'].strftime("%Y-%m-%d")

        tmp.update({f"{col}": d['guest']})
        tmp.update({f"{col}_css": d['status']})
        tmp.update({f"{col}_folio": d['folio']})
        tmp.update({f"{col}_reservation": d['reservation']})
    #     tmp.update({f"{col}_customer":d['customer'] })

    results = []
    for key, val in rows.items():
        val.update({"room": key})
        results += [val]

    columns = []
    # pinned columns
    columns += [dict(label="Room", fieldname="name",
                     fieldtype="Link/Room HMS", width=130, pinned='left')]
    columns += [dict(label="Room Type", fieldname="room_type",
                     fieldtype="Data", width=130, pinned='left')]
    columns += [dict(label="Room No", fieldname="room_no",
                     fieldtype="Data", width=130, pinned='left')]
    columns += [dict(label="Status", fieldname="room_status",
                     fieldtype="Data", width=100, pinned='left')]
    # dates
    for d in [add_days(filters.get('from_date'), _)
              for _ in range(0, date_diff(filters.get('to_date'), filters.get('from_date'))+1)]:
        columns += [dict(label=d, fieldname=d,
                         fieldtype="Data", width=120, )]

    # print(columns, results)
    return columns, results


@frappe.whitelist()
def set_room_status(room_no, status_action):
    from hms.hms.doctype.room_status_ledger_entry_hms.room_status_ledger_entry_hms import update_room_status_ledger
    update_room_status_ledger(dict(room_no=room_no), action=status_action)
