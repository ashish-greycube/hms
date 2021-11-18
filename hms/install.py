# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.desk.page.setup_wizard.setup_wizard import make_records


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
