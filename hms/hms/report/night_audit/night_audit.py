# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.utils import getdate, date_diff, add_to_date, add_days
import frappe
import json
from six import string_types, iteritems


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
    select g.reference_name name, g.room_no, f.room_type, f.status, g.reference_name folio, f.customer,
f.check_in, f.check_out, f.total_charges, f.total_advance_paid, f.balance, gu.guests guest, '' mobile,
coalesce(si.name,'') invoice, coalesce(si.outstanding_amount, 0) outstanding_amount
from `tabRoom Status Ledger Entry HMS` g
inner join `tabRoom Folio HMS` f on f.name = g.reference_name
left outer join 
(
	select parent, concat_ws(',',guest)guests from `tabRoom Guest Detail HMS`
	group by parent
) gu on gu.parent = f.name
left outer join
(
    select name, room_date_cf, room_folio_cf, outstanding_amount
    from `tabSales Invoice`
    where room_folio_cf is not null and room_date_cf = %(audit_date)s
) si on room_folio_cf = f.name
where g.docstatus <> 2 and g.status = 'Occupied'
""", filters, as_dict=True, debug=False)

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
    columns += [dict(label="In", fieldname="check_in",
                     fieldtype="DateTime", width=140,)]
    columns += [dict(label="Out", fieldname="check_out",
                     fieldtype="DateTime", width=140,)]
    columns += [dict(label="Customer", fieldname="customer",
                     fieldtype="Link/Customer", width=180,)]
    columns += [dict(label="Invoice", fieldname="invoice",
                     fieldtype="Link/Sales Invoice", width=100,)]
    columns += [dict(label="Outstanding", fieldname="outstanding_amount",
                     fieldtype="Currency", width=100,)]
    columns += [dict(label="Total", fieldname="total_charges",
                     fieldtype="Currency", width=100,)]
    columns += [dict(label="Advance", fieldname="total_advance_paid",
                     fieldtype="Currency", width=100,)]
    columns += [dict(label="Balance", fieldname="balance",
                     fieldtype="Currency", width=100,)]
    # columns += [dict(label="Mobile", fieldname="mobile",
    #                  fieldtype="Data", width=120,)]

    return columns,  data


@frappe.whitelist()
def post_charges(filters=None, doclist=None):
    if filters and isinstance(filters, string_types):
        filters = json.loads(filters)

    doclist = doclist and json.loads(doclist) or []
    count = 0
    for d in doclist:
        doc = frappe.get_doc('Room Folio HMS', d)
        if doc.create_charge_purchase(filters.get("audit_date")):
            count += 1
    frappe.msgprint(f"Posted charges for {count} rooms.", alert=True)
