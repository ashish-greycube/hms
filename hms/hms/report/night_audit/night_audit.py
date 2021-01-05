# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.utils import getdate, date_diff, add_to_date, add_days, cint
import frappe
from frappe import _
import json
from six import string_types, iteritems


def execute(filters=None):
    columns, data = get_data(filters)
    return columns, data


def get_data(filters):
    data, columns, where_clause = [], [], []

    op = filters.get("operation")
    if op == "Rooms to CheckIn":
        return get_data_rooms_to_checkin(filters)

    else:
        if op == "Rooms to CheckOut":
            where_clause += [
                " and date(f.check_out) <= %(audit_date)s and f.status='Checked In'"
            ]
        elif op == "Rooms to Charge":
            where_clause += [
                " and f.status='Checked In' and %(audit_date)s between date(f.check_in) and date(f.check_out)"
            ]

        data = frappe.db.sql(
            """
    select g.reference_name name, g.room_no, f.room_type, f.status, g.reference_name folio, f.customer,
    f.check_in, f.check_out, f.total_charges, f.total_advance_paid, f.balance, gu.guests guest, '' mobile,
    coalesce(si.name,'') invoice, coalesce(si.outstanding_amount, 0) outstanding_amount
    from `tabRoom Status Ledger Entry HMS` g
    inner join `tabRoom Folio HMS` f on f.name = g.reference_name
    and date(f.check_in) <= %(audit_date)s
    left outer join
    (
        select parent, concat_ws(',',guest)guests from `tabRoom Guest Detail HMS`
        group by parent
    ) gu on gu.parent = f.name
    left outer join
    (
        select name, room_date_cf, room_folio_cf, outstanding_amount
        from `tabSales Invoice`
        where docstatus = 1 and room_folio_cf is not null and room_date_cf = %(audit_date)s
    ) si on room_folio_cf = f.name
    where g.docstatus <> 2 and g.status = 'Occupied' and f.status = 'Checked In'
    {where_clause}""".format(
                where_clause=" and ".join(where_clause)
            ),
            filters,
            as_dict=True,
            debug=False,
        )

    # employee
    columns += [
        dict(
            label="Room No",
            fieldname="room_no",
            fieldtype="Data",
            width=130,
            pinned="left",
            group="Room",
            headerCheckboxSelection=True,
            checkboxSelection=True,
        )
    ]
    columns += [
        dict(
            label="Room Type",
            fieldname="room_type",
            fieldtype="Data",
            width=90,
            pinned="left",
            group="Room",
        )
    ]
    columns += [
        dict(
            label="Status",
            fieldname="status",
            fieldtype="Data",
            width=90,
            pinned="left",
            group="Room",
        )
    ]
    #
    columns += [
        dict(
            label="Folio",
            fieldname="folio",
            fieldtype="Link/Room Folio HMS",
            width=140,
        )
    ]
    columns += [
        dict(label="Guest", fieldname="guest", fieldtype="Link/Contact", width=180,)
    ]
    columns += [
        dict(label="In", fieldname="check_in", fieldtype="DateTime", width=140,)
    ]
    columns += [
        dict(label="Out", fieldname="check_out", fieldtype="DateTime", width=140,)
    ]
    columns += [
        dict(
            label="Customer",
            fieldname="customer",
            fieldtype="Link/Customer",
            width=180,
        )
    ]
    columns += [
        dict(
            label="Invoice",
            fieldname="invoice",
            fieldtype="Link/Sales Invoice",
            width=100,
        )
    ]
    columns += [
        dict(
            label="Outstanding",
            fieldname="outstanding_amount",
            fieldtype="Currency",
            width=100,
        )
    ]
    columns += [
        dict(label="Total", fieldname="total_charges", fieldtype="Currency", width=100,)
    ]
    columns += [
        dict(
            label="Advance",
            fieldname="total_advance_paid",
            fieldtype="Currency",
            width=100,
        )
    ]
    columns += [
        dict(label="Balance", fieldname="balance", fieldtype="Currency", width=100,)
    ]
    # columns += [dict(label="Mobile", fieldname="mobile",
    #                  fieldtype="Data", width=120,)]

    return columns, data


def get_data_rooms_to_checkin(filters):
    data, columns = [], []

    data = frappe.db.sql(
        """
        select
            so.name, so.room_no_cf room_no, rm.room_type, so.check_in_cf check_in, so.check_out_cf check_out,
            so.guest_cf guest, so.customer, so.advance_paid
        from
            `tabSales Order` so
            inner join `tabRoom HMS` rm on rm.name = so.room_no_cf
            left outer join `tabRoom Folio HMS` x on x.reservation = so.name
        where
            so.docstatus = 1 and date(so.check_in_cf) = %(audit_date)s""",
        filters,
        as_dict=True,
    )

    columns += [
        dict(
            label="Reservation",
            fieldname="name",
            fieldtype="Link/Sales Order",
            width=150,
        )
    ]
    columns += [dict(label="Room #", fieldname="room_no", width=120,)]
    columns += [dict(label="Room Type", fieldname="room_type", width=120,)]
    columns += [
        dict(label="Guest", fieldname="guest", fieldtype="Link/Contact", width=180,)
    ]
    columns += [
        dict(label="In", fieldname="check_in", fieldtype="DateTime", width=140,)
    ]
    columns += [
        dict(label="Out", fieldname="check_out", fieldtype="DateTime", width=140,)
    ]
    columns += [
        dict(
            label="Customer",
            fieldname="customer",
            fieldtype="Link/Customer",
            width=180,
        )
    ]
    columns += [
        dict(
            label="Advance",
            fieldname="total_advance_paid",
            fieldtype="Currency",
            width=100,
        )
    ]

    return columns, data


@frappe.whitelist()
def post_charges(filters=None, doclist=None):
    if filters and isinstance(filters, string_types):
        filters = json.loads(filters)

    doclist = doclist and json.loads(doclist) or []
    count = 0
    for d in doclist:
        doc = frappe.get_doc("Room Folio HMS", d)
        if doc.create_charge_purchase(filters.get("audit_date")):
            count += 1
    frappe.msgprint(f"Posted charges for {count} rooms.", alert=True)


@frappe.whitelist()
def validate_system_date(system_date, raise_exception=0):
    messages = []
    audit_date = add_days(getdate(system_date), -1)
    # check night audit complete till system date
    rooms_to_check_in = frappe.db.sql(
        """
    select
            so.name, so.room_no_cf room_no, rm.room_type, so.check_in_cf check_in, so.check_out_cf check_out,
            so.guest_cf guest, so.customer, so.advance_paid
        from
            `tabSales Order` so
            inner join `tabRoom HMS` rm on rm.name = so.room_no_cf
        where
            so.docstatus = 1 
            and date(so.check_in_cf) = %(audit_date)s
            and not exists (select 1 from `tabRoom Folio HMS` x where x.reservation = so.name)""",
        dict(audit_date=audit_date),
        as_dict=True,
    )

    if rooms_to_check_in:
        message = "<h6>Please check-in or cancel the reservations.</h6>"
        message += ", ".join(
            [
                frappe.utils.get_link_to_form("Sales Order", d["name"])
                + f": {d['customer']} {d['room_no']} "
                for d in rooms_to_check_in
            ]
        )
        messages += [message]

    rooms_to_charge = frappe.db.sql(
        """
        select f.name folio, f.room_no, dt.date
        from `tabRoom Folio HMS` f
        inner join `tabDate Lookup HMS` dt on date(f.check_in) <= dt.date and date(f.check_out) > dt.date
        where
        f.docstatus =1
        and f.status = 'Checked In'
        and  exists(
            select 1 from `tabSales Invoice` x 
            where x.room_folio_cf = f.name and x.docstatus = 1)
        and dt.date = %(audit_date)s""",
        dict(audit_date=audit_date),
        as_dict=True,
    )
    if rooms_to_charge:
        message = "<h6>Please create invoice for these folios.</h6>"
        message += ", ".join(
            [
                frappe.utils.get_link_to_form("Room Folio HMS", d["folio"])
                + f"{d['room_no']} {d['date']}"
                for d in rooms_to_charge
            ]
        )
        messages += [message]

    rooms_to_check_out = frappe.db.sql(
        """
        select f.name folio, f.room_no
        from `tabRoom Folio HMS` f
        where
        f.docstatus =1
        and f.status = 'Checked In' and date(f.check_out) = %(audit_date)s""",
        dict(audit_date=audit_date),
        as_dict=True,
    )
    if rooms_to_check_out:
        message = "<h6>Please check out these folios.</h6>"
        message += ", ".join(
            [f"{d['folio']} {d['room_no']}" for d in rooms_to_check_out]
        )
        messages += [message]

    if messages:
        if cint(raise_exception):
            frappe.throw(
                _("Night Audit is not completed for " + "%s.<br>" % audit_date)
                + "<br>".join(messages)
            )
        else:
            return "<br>".join(messages)

    # set System Date in HMS Settings
    # frappe.db.set_value("HMS Settings", None, "hms_system_date", system_date)
    # frappe.db.commit()

    return True
