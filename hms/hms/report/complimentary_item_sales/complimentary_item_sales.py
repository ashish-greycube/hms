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
    return [
        dict(
            label="Item",
            fieldname="item_name",
            fieldtype="Link",
            options="Item",
            width=400,
        ),
        dict(label="Qty", fieldname="qty", fieldtype="Int", width=130,),
        dict(label="Rate", fieldname="selling_rate", fieldtype="Currency", width=130,),
        dict(
            label="Total Amount", fieldname="amount", fieldtype="Currency", width=130,
        ),
    ]


def get_data(filters=None):
    data = []
    where_conditions = get_conditions(filters)
    data = frappe.db.sql(
        """
    select 
        it.item_name, it.item_code, round(sum(sit.qty*pbi.qty),0) qty,
        0 selling_rate, 0 amount
    from 
        `tabSales Invoice` si
        inner join `tabSales Invoice Item` sit on sit.parent = si.name
        inner join tabItem pit on pit.item_code = sit.item_code and pit.room_type_cf is not null
        inner join `tabProduct Bundle Item` pbi on pbi.parent = sit.item_code 
        inner join `tabItem` it on it.item_code = pbi.item_code and it.room_type_cf is null
        {where_conditions} 		
    group by 
        it.item_name    
    """.format(
            where_conditions=where_conditions
        ),
        filters,
        as_dict=True,
        debug=0,
    )

    from erpnext.stock.report.item_price_stock.item_price_stock import get_data

    for d in data:
        selling_rate = 0
        for stock in get_data({"item_code": d.item_code}, columns=None):
            selling_rate = stock.get("selling_rate", 0)
            d.update({"selling_rate": selling_rate, "amount": selling_rate * d.qty})

    return data


def get_conditions(filters):
    where_conditions = [
        "si.docstatus = 1 and si.company = '{}' ".format(get_default_company())
    ]

    if filters.get("from_date"):
        where_conditions += ["si.posting_date >= %(from_date)s"]
    if filters.get("to_date"):
        where_conditions += ["si.posting_date <= %(to_date)s"]
    if filters.get("item_code"):
        where_conditions += ["pbi.item_code = %(item_code)s"]

    return where_conditions and " where {}".format(" and ".join(where_conditions)) or ""


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def complimentary_items_query(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql(
        """ 
        select 
            it.item_code, it.item_name
        from  
            `tabProduct Bundle Item` pbi
            inner join tabItem it on it.item_code = pbi.item_code and it.room_type_cf is null
            and it.item_code like %(txt)s
		limit %(start)s, %(page_len)s""",
        {"start": start, "page_len": page_len, "txt": "%%%s%%" % txt,},
    )
