# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class OnlineBookingHMS(Document):
    def validate(self):
        if not self.customer:
            for d in frappe.db.sql("""
            select 
                dl.link_name customer, co.name guest
            from 
                tabContact co
            inner join 
                `tabDynamic Link` dl
                on dl.parenttype = 'Contact' and dl.link_doctype = 'Customer'
                and dl.parent = co.name
            where 
                co.is_primary_contact = 1
                and co.email_id = %s and co.mobile_no = %s
            limit 1 """, (self.email, self.phone_no), as_dict=True):
                if not self.customer:
                    self.customer = d.customer
