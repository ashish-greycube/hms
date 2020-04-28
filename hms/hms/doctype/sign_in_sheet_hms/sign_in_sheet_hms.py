# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.contacts.doctype.address.address import get_address_display
from frappe.utils import nowdate, flt, cint, today, getdate, cstr


class SignInSheetHMS(Document):
    def validate(self):
        if self.db_get('signature'):
            frappe.throw("Cannot modify Sign In Sheet after signature")


def make_sign_in_sheet(room_folio, no_letterhead=False):
    from bs4 import BeautifulSoup

    self = frappe.get_doc("Room Folio HMS", room_folio)

    html = frappe.get_print(self.doctype, self.name, print_format="Folio Sign In",
                            doc=self, no_letterhead=no_letterhead)

    soup = BeautifulSoup(html, 'lxml')
    for s in soup.select('script'):
        s.extract()
    html = soup.prettify()

    print_dict = {}
    # custom_fields = ["sub_heading", "guest_full_name", "total_guest", "guest_address_display", "total_amount_weekdays", "total_amount_weekends",
    #                  "total_room_charges", "total_other_charges", "mode_of_payment", "guest_mobile", "guest_email", "total_taxes_and_charges", ]
    for d in frappe.db.sql("""
            select reservation,car_make_model,registration_plate_no, gu.*
            from `tabRoom Folio HMS` f
            left outer join  
            (
                select gd.mobile guest_mobile, gd.email guest_email, 
                gd.guest guest_full_name, gd.parent
                from `tabRoom Guest Detail HMS` gd
                inner join tabContact co on co.name = gd.guest
                where gd.parent = %s
                limit 1
            ) gu on gu.parent = f.name
            where f.name = %s
        """, (self.name, self.name), as_dict=True):
        print_dict.update(d)

    for d in frappe.db.sql("""
            select 
            terms,
            so.customer_address address_name,
            max(so.rounded_total) total_charges,
            max(so.rounded_total) total_room_charges,
            max(so.discount_amount) discount_amount,
            0 total_other_charges,
            max(so.advance_paid) total_advance_paid,
            max(so.rounded_total - so.advance_paid) balance,
            coalesce(max(so.no_of_guest_cf),1) total_guest,
            max(total_taxes_and_charges) total_taxes_and_charges, 
            sum(if(is_holiday_cf=1 or is_weekend_cf=1,0,1)) total_amount_weekdays,
            sum(if(is_holiday_cf=1 or is_weekend_cf=1,1,0)) total_amount_weekends
            from `tabSales Order` so
            inner join `tabSales Order Item` soi on soi.parent = so.name 
            where so.name = %s
        """, (print_dict['reservation']), as_dict=True):
        print_dict.update(d)

    print_dict.setdefault('guest_address_display', "-")

    if print_dict['address_name']:
        print_dict['guest_address_display'] = get_address_display(
            print_dict['address_name'])

    for k, v in print_dict.items():
        html = html.replace("{doc.%s}" % k, cstr(v))

    doc = frappe.new_doc("Sign In Sheet HMS")
    doc.content = html
    doc.save()
    self.db_set("sign_in_sheet", doc.name)
    return doc
