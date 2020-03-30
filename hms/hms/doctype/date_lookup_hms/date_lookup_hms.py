# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, date_diff, add_to_date
from frappe.model.document import Document


class DateLookupHMS(Document):
    def autoname(self):
        self.name = getdate(self.date).strftime("%Y-%m-%d")

    def validate(self):
        pass


def create_dates(start_date="2021-01-01", end_date="2025-12-31"):
    # bench --site hotels execute hms.hms.doctype.date_lookup_hms.date_lookup_hms.create_dates --args "['2020-01-01','2025-01-01']"
    now = frappe.utils.today()
    user = frappe.session.user
    for d in range(date_diff(end_date, start_date)+1):
        date = add_to_date(start_date, days=d)
        frappe.db.sql("""
INSERT INTO sun.`tabDate Lookup HMS`
(name, creation, modified, modified_by, owner, docstatus, parent, parentfield, parenttype, idx, weekday_name,
month_name, `date`, weekday, `month`, `year`, `_user_tags`, `_comments`, `_assign`, `_liked_by`)
VALUES(%s, %s, %s, %s, %s, 0, NULL, NULL, NULL, 0, NULL, NULL, %s, 0, 0, 0, NULL, NULL, NULL, NULL);
        """, (date, now, now, user, user, date))

    frappe.db.sql("""
    update `tabDate Lookup HMS` set
    weekday = dayofweek(date), weekday_name = dayname(date),
    month = Month(date), month_name = MonthName(date), year = Year(date)
    """)
