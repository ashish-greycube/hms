# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.desk.page.setup_wizard.setup_wizard import make_records
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
    records = [
        # Lead Source
        {
            "doctype": "Lead Source",
            "source_name": "Website Online",
            "details": "Booking through website",
        },
    ]

    make_records(records)

    custom_fields = {
        "POS Invoice": [
            dict(
                fieldname="room_folio_cf",
                label="Room Folio",
                fieldtype="Data",
                insert_after="tax_id",
                no_copy=1,
                print_hide=1,
                read_only=1,
            )
        ]
    }

    create_custom_fields(custom_fields)
