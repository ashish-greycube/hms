# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest


class TestRoomFolioHMS(unittest.TestCase):
    pass


def test_check_out():
    doc = frappe.get_doc('Room Folio HMS', "HMS-RR-20-00021")
    doc.make_check_out()


def test_create_charge_purchase():
    doc = frappe.get_doc('Room Folio HMS', "HMS-RR-20-00001")
    doc.create_charge_purchase("2020-03-04")


def test_split_bill(invoice):
    si = frappe.copy_doc(frappe.get_doc("Sales Invoice", invoice))
    si.save()
    frappe.db.commit()
