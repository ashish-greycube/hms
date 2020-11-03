# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import nowdate, now_datetime
from frappe.model.document import Document


class RoomStatusLedgerEntryHMS(Document):
    def validate(self):
        '''Check for duplicates'''
        for d in frappe.db.sql("""
            select room_no, status
            from `tabRoom Status Ledger Entry HMS` g
            where docstatus <> 2 and room_no = %s and status = %s""", (self.room_no, self.status)):
            frappe.throw("Entry for %s in %s status already exists." % (self.room_no, self.status))


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

        self.set_dirty()

    def cancel(self):
        # on Cancel of Folio cancel Occupied entry
        frappe.db.sql("""
        update `tabRoom Status Ledger Entry HMS`
        set docstatus = 2, status = 'Cancelled', modified = %(modified)s, modified_by = %(modified_by)s
        where docstatus = 0 and status = 'Occupied' and room_no = %(room_no)s
        """, self.args)
        self.set_dirty()

    def set_dirty(self):
        # create Dirty entry
        doc = frappe.get_doc({
            "doctype": "Room Status Ledger Entry HMS",
        })
        doc.update(self.args)
        doc.update({"status": "Dirty"})
        doc.insert(ignore_permissions=True)

    def remove_dirty(self):
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

    def remove_to_service(self):
        # cancel To Service entry
        frappe.db.sql("""
        update `tabRoom Status Ledger Entry HMS`
        set docstatus = 2, modified = %(modified)s, modified_by = %(modified_by)s
        where docstatus = 0 and status = 'To Service' and room_no = %(room_no)s
        """, self.args)
        frappe.db.commit()

    def set_out_of_order(self):
        # create Dirty entry
        doc = frappe.get_doc({
            "doctype": "Room Status Ledger Entry HMS",
        })
        doc.update(self.args)
        doc.update({"status": "Out Of Order"})
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

    def remove_out_of_order(self):
        frappe.db.sql("""
        update `tabRoom Status Ledger Entry HMS`
        set docstatus = 2, modified = %(modified)s, modified_by = %(modified_by)s
        where docstatus = 0 and status = 'Out Of Order' and room_no = %(room_no)s
        """, self.args)
        frappe.db.commit()
