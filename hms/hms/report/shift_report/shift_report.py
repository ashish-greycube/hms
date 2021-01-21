# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from numpy.core.fromnumeric import mean
import frappe
from erpnext import get_default_company
from frappe.utils.pdf import get_pdf
import json
import pandas
import numpy as np
from operator import itemgetter


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
            dict(label="Amount", fieldname="amount", fieldtype="Currency", width=100,),
        ]
    else:
        return [
            dict(label="Date", fieldname="posting_date", fieldtype="Date", width=100,),
            dict(
                label="MoP", fieldname="mode_of_payment", fieldtype="Data", width=100,
            ),
            dict(
                label="Transactions",
                fieldname="transaction_count",
                fieldtype="Int",
                width=100,
            ),
            dict(label="Amount", fieldname="amount", fieldtype="Currency", width=100,),
        ]


def get_data(filters=None):
    data = []
    where_conditions = get_conditions(filters)

    data = frappe.db.sql(
        """
            with fn as (
    select  folio.folio, posting_date audit_date, '201' `type`, 
    case when mode_of_payment = 'Cash' then 'Cash'
    else concat(mode_of_payment, ' : ', remarks) end account, posting_date, 
    date_format(modified,'%%H:%%i %%p') `time`, 
    case when payment_type = 'Pay' then base_received_amount else 0 end debit, 
    case when payment_type = 'Receive' then base_received_amount else 0 end credit, 
    party_name, mode_of_payment, base_received_amount, payment_type, remarks, modified_by, company,
    case when payment_type = 'Pay' then 0-base_received_amount else base_received_amount end amount
    from `tabPayment Entry`
    inner join (
        select per.parent, coalesce(si.room_folio_cf, concat(so.name,':',so.customer)) folio
        from `tabPayment Entry Reference` per
        left outer join `tabSales Invoice` si on si.name = per.reference_name and per.reference_doctype = 'Sales Invoice'
        left outer join `tabSales Order` so on so.name = per.reference_name and per.reference_doctype = 'Sales Order'
        group by parent
    ) folio on folio.parent = `tabPayment Entry`.name
    where `tabPayment Entry`.docstatus = 1
    union all
    select concat_ws(':',t2.reference_name,t2.party) folio, t1.posting_date audit_date, '201' type,
    mpa.parent account, t1.posting_date, date_format(t1.modified,'%%H:%%i %%p') `time`, 
    t2.debit debit, t2.credit credit, 
    t2.party party_name, mpa.parent mode_of_payment,  
    abs(t2.credit-t2.debit) base_received_amount, case when debit > 0 then 'Receive' else 'Pay' end payment_type, 
    t1.remark,  t1.modified_by, t1.company, t2.credit-t2.debit amount
            from
                `tabJournal Entry` t1, `tabJournal Entry Account` t2, `tabMode of Payment Account` mpa
            where
                t1.name = t2.parent and t1.docstatus = 1 
                and mpa.default_account = t2.against_account
        )
    select * from fn
    {where_conditions}
    order by posting_date,`time`
        """.format(
            where_conditions=where_conditions
        ),
        filters,
        as_dict=True,
        # debug=0,
    )
    if data and filters.get("summary_view", 0):
        df = pandas.DataFrame.from_records(data)
        g = (
            df.groupby(["posting_date", "mode_of_payment"], as_index=False)
            .agg({"amount": "sum", "payment_type": "count"})
            .rename(columns={"amount": "amount", "payment_type": "transaction_count"})
        )
        data = g.to_dict("r")
    return data


def get_conditions(filters):
    where_conditions = ["company = '{}' ".format(get_default_company())]

    if not frappe.utils.has_common(
        ["System Manager", "Accounts Manager", "Sales Manager"], frappe.get_roles()
    ):
        filters["user"] = frappe.session.user

    if filters.get("user"):
        where_conditions += ["modified_by = %(user)s"]
    if filters.get("shift_date"):
        where_conditions += ["posting_date = %(shift_date)s"]
    if filters.get("mode_of_payment"):
        where_conditions += ["mode_of_payment = %(mode_of_payment)s"]

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

