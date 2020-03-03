# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class RoomLedgerEntryHMS(Document):
    pass


def make_room_ledger_entry(date, room_no, reference_type, reference_name, entry_type):
    frappe.get_doc({
        "doctype": "Room Ledger Entry HMS",
        "reference_type": reference_type,
        "reference_name": reference_name,
        "date": date,
        "room_no": room_no,
        "entry_type": entry_type
    }).insert(ignore_permissions=True)
