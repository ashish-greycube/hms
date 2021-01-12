# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext import get_default_company
from frappe.utils.pdf import get_pdf
import json


def execute(filters=None):
    return get_columns(filters), get_data(filters)


def get_columns(filters=None):
    if not filters.get("summary_view", 0):
        return [
            dict(
                label="Folio",
                fieldname="folio",
                fieldtype="Link",
                options="Room Folio HMS",
                width=200,
            ),
            dict(
                label="Audit Date", fieldname="audit_date", fieldtype="Date", width=100,
            ),
            dict(
                label="Cashier", fieldname="modified_by", fieldtype="Data", width=110,
            ),
            dict(label="Account", fieldname="account", fieldtype="Data", width=210,),
            dict(label="Date", fieldname="posting_date", fieldtype="Date", width=100,),
            dict(label="Time", fieldname="time", fieldtype="Data", width=100,),
            dict(label="Debit", fieldname="debit", fieldtype="Currency", width=100,),
            dict(label="Credit", fieldname="credit", fieldtype="Currency", width=100,),
            dict(
                label="MoP", fieldname="mode_of_payment", fieldtype="Data", width=100,
            ),
            dict(
                label="Amount",
                fieldname="base_received_amount",
                fieldtype="Currency",
                width=100,
            ),
        ]
    else:
        return [
            dict(
                label="MoP", fieldname="mode_of_payment", fieldtype="Data", width=100,
            ),
            dict(label="Transactions", fieldname="count", fieldtype="Int", width=100,),
            dict(label="Amount", fieldname="amount", fieldtype="Currency", width=100,),
        ]


def get_data(filters=None):
    data = []
    where_conditions = get_conditions(filters)

    if not filters.get("summary_view", 0):
        data = frappe.db.sql(
            """
    select  folio.folio, posting_date audit_date, '201' `type`, 
    case when mode_of_payment = 'Cash' then 'Cash'
    else concat(mode_of_payment, ' : ', remarks) end account, posting_date, 
    date_format(modified,'%%H:%%i %%p') `time`, 
    case when payment_type = 'Receive' then base_received_amount else 0 end debit, 
    case when payment_type = 'Pay' then base_received_amount else 0 end credit, 
    party_name, mode_of_payment, base_received_amount, payment_type, remarks, modified_by
    from `tabPayment Entry`
    inner join (
        select per.parent, coalesce(si.room_folio_cf, concat(so.name,':',so.customer)) folio
        from `tabPayment Entry Reference` per
        left outer join `tabSales Invoice` si on si.name = per.reference_name and per.reference_doctype = 'Sales Invoice'
        left outer join `tabSales Order` so on so.name = per.reference_name and per.reference_doctype = 'Sales Order'
        group by parent
    ) folio on folio.parent = `tabPayment Entry`.name
    {where_conditions}
        """.format(
                where_conditions=where_conditions
            ),
            filters,
            as_dict=True,
            debug=True,
        )
    else:
        data = frappe.db.sql(
            """
    select mode_of_payment, count(*) `count`, sum(base_received_amount) amount
    from `tabPayment Entry`
    {where_conditions}
    group by mode_of_payment
        """.format(
                where_conditions=where_conditions
            ),
            filters,
            as_dict=True,
            debug=True,
        )

    return data


def get_conditions(filters):
    where_conditions = [
        "docstatus = 1 and company = '{}' ".format(get_default_company())
    ]

    if not frappe.utils.has_common(
        ["System Manager", "Accounts Manager", "Sales Manager"], frappe.get_roles()
    ):
        filters["user"] = frappe.session.user

    if filters.get("user"):
        where_conditions += ["modified_by = %(user)s"]
    if filters.get("shift_date"):
        where_conditions += ["posting_date = %(shift_date)s"]
    if filters.get("mode_of_payment"):
        where_conditions += ["posting_date = %(mode_of_payment)s"]

    return where_conditions and " where {}".format(" and ".join(where_conditions)) or ""


@frappe.whitelist()
def get_shift_report(filters):
    filters = frappe._dict(json.loads(filters))
    filters["summary_view"] = 1
    _, data = execute(filters)

    from frappe.www.printview import get_letter_head

    letter_head = get_letter_head(frappe._dict(), 0)

    template_path = "hms/hms/report/shift_report/shift_report.html"
    context = dict(data=data, company=get_default_company(), letter_head=letter_head)
    report_html = frappe.render_template(template_path, context)

    if not filters.get("user"):
        filters["user"] = "Summary"
    frappe.response.filename = "Shift Report {shift_date} {user}.pdf".format(**filters)
    frappe.response.filecontent = get_pdf(report_html)
    frappe.response.type = "download"

