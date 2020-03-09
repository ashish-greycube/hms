# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import nowdate, now_datetime
from frappe.model.document import Document


class RoomStatusLedgerEntryHMS(Document):
    pass


class update_room_status_ledger(object):
    """
        update room status ledger

        :param args: args as dict
        :param action: check_in, check_out, cleaned, services, add_to_service, set_dirty

            args = {
                "reference_type": "Sales Order",
                "reference_name": "",
                "room_no": "100-SH,
            }
    """

    def __init__(self, args, action):

        self.action = action
        self.args = args and {
            "room_no": args.get("room_no") or args.get("room_no_cf"),
            "reference_type": args.get("doctype"),
            "reference_name": args.get("name"),
            "modified": args.get("modified") or now_datetime(),
            "modified_by": args.get("modified_by") or frappe.session.user
        } or {}

        getattr(self, action)()

    def check_in(self):
        # create Occuied entry
        doc = frappe.get_doc({
            "doctype": "Room Status Ledger Entry HMS",
        })
        doc.update(self.args)
        doc.update({"status": "Occupied"})
        doc.insert(ignore_permissions=True)

    def check_out(self):
        # cancel Occupied entry
        frappe.db.sql("""
        update `tabRoom Status Ledger Entry HMS`
        set docstatus = 2, modified = %(modified)s, modified_by = %(modified_by)s
        where docstatus = 0 and status = 'Occupied' and room_no = %(room_no)s
        """, self.args)

        # create Dirty entry
        doc = frappe.get_doc({
            "doctype": "Room Status Ledger Entry HMS",
        })
        doc.update(self.args)
        doc.update({"status": "Dirty"})
        doc.insert(ignore_permissions=True)

    def set_dirty(self):
        # create Dirty entry
        doc = frappe.get_doc({
            "doctype": "Room Status Ledger Entry HMS",
        })
        doc.update(self.args)
        doc.update({"status": "Dirty"})
        doc.insert(ignore_permissions=True)

    def cleaned(self):
        # cancel Dirty entry
        frappe.db.sql("""
        update `tabRoom Status Ledger Entry HMS`
        set docstatus = 2, modified = %(modified)s, modified_by = %(modified_by)s
        where docstatus = 0 and status = 'Dirty' and room_no = %(room_no)s
        """, self.args)
        frappe.db.commit()

    def add_to_service(self):
        # create To Service entry
        doc = frappe.get_doc({
            "doctype": "Room Status Ledger Entry HMS",
        })
        doc.update(self.args)
        doc.update({"status": "To Service"})
        doc.insert(ignore_permissions=True)

    def serviced(self):
        # cancel To Service entry
        frappe.db.sql("""
        update `tabRoom Status Ledger Entry HMS`
        set docstatus = 2, modified = %(modified)s, modified_by = %(modified_by)s
        where docstatus = 0 and status = 'To Service' and room_no = %(room_no)s
        """, self.args)
        frappe.db.commit()
