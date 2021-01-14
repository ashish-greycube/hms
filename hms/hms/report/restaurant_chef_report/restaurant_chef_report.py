# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext import get_default_company
from frappe.utils.pdf import get_pdf
import json
from frappe.utils import cint
import pandas
from operator import itemgetter


def execute(filters=None):
    return get_columns(filters), get_data(filters)


def get_columns(filters=None):
    return [
        dict(label="Room No", fieldname="room_no", width=130,),
        dict(
            label="Item",
            fieldname="item_code",
            fieldtype="Link",
            options="Item",
            width=150,
        ),
        dict(label="Qty", fieldname="qty", fieldtype="Int", width=130,),
    ]


def get_data(filters=None):
    data = []
    where_conditions = get_conditions(filters)
    data = frappe.db.sql(
        """
        select 
            rf.room_no, pbi.item_code, pbi.qty
        from 
            `tabRoom Folio HMS` rf  
            left outer join `tabProduct Bundle Item` pbi on pbi.parent = rf.room_package 
            left outer join `tabItem` it on it.item_code = pbi.item_code and it.room_type_cf is null
        {where_conditions} 		
    """.format(
            where_conditions=where_conditions
        ),
        filters,
        as_dict=True,
        debug=True,
    )

    if data and not cint(filters.get("show_room_no")):
        df = pandas.DataFrame.from_records(data)
        df1 = df[["item_code", "qty"]]
        g = df1.groupby("item_code", as_index=False).agg("sum")
        data = g.to_dict("r")
        data = sorted(data, key=itemgetter("item_code"))

    return data


def get_conditions(filters):
    where_conditions = [
        """
        rf.docstatus = 1 
        and rf.status = 'Checked In'
        and rf.company = '{}' 
        """.format(
            format(get_default_company())
        )
    ]

    if filters.get("room_date"):
        where_conditions += [
            "rf.check_in >= %(room_date)s and rf.check_out <= %(room_date)s"
        ]
    if filters.get("item_code"):
        where_conditions += ["pbi.item_code = %(item_code)s"]

    return where_conditions and " where {}".format(" and ".join(where_conditions)) or ""
