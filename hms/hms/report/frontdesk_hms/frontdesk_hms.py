# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, date_diff, add_to_date, add_days, today
from pprint import pprint
from erpnext import get_default_company


def execute(filters=None):
    columns, data = get_data(filters)
    return columns, data


def get_data(filters=None):
    if not filters:
        filters = {}

    where_clause = []
    where_clause.append("d.date BETWEEN %(from_date)s and %(to_date)s")
    if filters.get('room_type'):
        where_clause.append('r.room_type = %(room_type)s')
    if filters.get('company'):
        where_clause.append('r.company = %(company)s')
    if filters.get('room_status'):
        if filters.get('room_status') == 'Available':
            where_clause.append('c.room_status is null')
        else:
            where_clause.append('c.room_status = %(room_status)s')

    where_clause = " and ".join(where_clause)

    data = frappe.db.sql("""
            select d.date, r.name name, r.room_no room_no, r.room_type, c.room_status,
            case
            when a.name is not null  and (a.status='Checked In' or a.status='Pre-Check In') then 'hms-in-house'
            when a.name is null and b.name is not null 
                then case when b.advance_paid > 0 then 'hms-gtd-reservation' else 'hms-ngtd-reservation' end
            when d.date = curdate() then concat('hms-',coalesce(lower(c.room_status),''))
            else '' end status,
            coalesce(a.customer,b.customer) customer,
            coalesce(gd.guest, b.guest, a.customer, b.customer) guest,
            a.name folio, b.name `reservation`
            from 
            `tabDate Lookup HMS` d
            cross join `tabRoom HMS` r
            left outer join 
            (
                -- room folio
                select fo.room_no, fo.check_in, fo.check_out, fo.customer, fo.name, fo.status
                from `tabRoom Folio HMS` fo
                where not (fo.check_in >= %(to_date)s OR fo.check_out <= %(from_date)s)
                and (fo.status = 'Checked In' or fo.status = 'Pre-Check In') 
                and fo.docstatus <> 2
            ) a on d.date BETWEEN date(a.check_in) and date_sub(date(a.check_out), INTERVAL 1 DAY) and r.name = a.room_no
            left outer join `tabRoom Guest Detail HMS` gd on gd.name = (
                -- guest details
                select x.name from `tabRoom Guest Detail HMS` x 
                where x.parent = a.name limit 1
            )
            left outer join
            (
                -- reservation
                select so.name, so.room_no_cf room_no, so.check_in_cf check_in, so.check_out_cf check_out, 
                so.guest_cf guest, so.customer, so.advance_paid
                from `tabSales Order` so
                where not (so.check_in_cf >= %(to_date)s OR so.check_out_cf <= %(from_date)s)
                and not exists (select 1 from `tabRoom Folio HMS` x where x.reservation = so.name)
                and so.docstatus <> 2
            ) b on d.date BETWEEN date(b.check_in) and date_sub(date(b.check_out), INTERVAL 1 DAY) and r.name = b.room_no
            left outer join 
            (
                -- room status ledger: Dirty/Occupied/OOO/OOS
                select room_no, status, reference_type, reference_name, status room_status
                from `tabRoom Status Ledger Entry HMS`
                where docstatus <> 2
            ) c on c.room_no = r.name 
            where {where_clause}
            order by d.date, r.room_type, r.room_no
    """.format(where_clause=where_clause), filters, as_dict=True, debug=1)

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
    columns += [dict(label="Status", fieldname="room_status",
                     fieldtype="Data", width=40, pinned='left')]
    columns += [dict(label="Room", fieldname="name",
                     fieldtype="Link/Room HMS", width=130, pinned='left', hide=True)]
    columns += [dict(label="Room Type", fieldname="room_type",
                     fieldtype="Data", width=130, pinned='left')]
    columns += [dict(label="Room No", fieldname="room_no",
                     fieldtype="Data", width=130, pinned='left')]
    # dates
    holidays = get_holidays(filters.get('from_date'), filters.get('to_date'))

    for d in [add_days(filters.get('from_date'), _)
              for _ in range(0, date_diff(filters.get('to_date'), filters.get('from_date')) + 1)]:
        col_date = getdate(d)
        day_type = "today" if d == today() else ""
        if d in holidays.keys():
            day_type = "weekend" if holidays[d] == col_date.strftime(
                "%A") else "holiday"
        columns += [dict(label=col_date.strftime('%d-%b (%a)'), fieldname=d,
                         fieldtype="Data", width=120, day_type=day_type)]

    return columns, results


@frappe.whitelist()
def set_room_status(room_no, status_action):
    from hms.hms.doctype.room_status_ledger_entry_hms.room_status_ledger_entry_hms import update_room_status_ledger
    update_room_status_ledger(dict(room_no=room_no), action=status_action)


def get_holidays(from_date, to_date):
    holiday_list = frappe.get_cached_value(
        'Company', get_default_company(), "default_holiday_list")
    holidays = {}
    for d in frappe.db.sql("""select date_format(holiday_date,'%%Y-%%m-%%d') holiday_date, description 
    from tabHoliday where parent = %s
    and holiday_date between %s and %s""", (holiday_list, from_date, to_date),):
        holidays.setdefault(d[0], d[1])
    return holidays
