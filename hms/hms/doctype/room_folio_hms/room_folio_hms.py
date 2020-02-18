# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class RoomFolioHMS(Document):
    pass


@frappe.whitelist()
def get_charge_and_purchase(docname):
    return frappe.db.sql("""
	select name, posting_date, posting_time, rounded_total, outstanding_amount
	from `tabSales Invoice` i
	where ifnull(i.room_folio_cf,'') = %s
	""", (docname, ), as_dict=True)
