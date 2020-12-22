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
        # self.content = make_sign_in_sheet(self.folio)

def make_sign_in_sheet(room_folio, no_letterhead=False):
    doc = frappe.new_doc("Sign In Sheet HMS")
    doc.folio = room_folio
    doc.content = get_content_html(room_folio, no_letterhead)
    doc.save()

    folio = frappe.get_doc("Room Folio HMS", room_folio)
    folio.db_set("sign_in_sheet", doc.name)
    return doc

def get_content_html(room_folio, no_letterhead=False):
    # from bs4 import BeautifulSoup
    # bench execute .hms.hms.doctype.sign_in_sheet_hms.sign_in_sheet_hms.make_sign_in_sheet('HMS-RR-20-00018')
    folio = frappe.get_doc("Room Folio HMS", room_folio)
    template = "hms/templates/folio_sign_in.html"

    # html = frappe.get_print(self.doctype, self.name, print_format="Folio Sign In",
    #                         doc=self, no_letterhead=no_letterhead)

    # soup = BeautifulSoup(html, 'lxml')
    # for s in soup.select('script'):
    #     s.extract()
    # html = soup.prettify()

    print_context = {}
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
        """, (folio.name, folio.name), as_dict=True):
        print_context.update(d)

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
        """, (print_context['reservation']), as_dict=True):
        print_context.update(d)

    for d in frappe.db.sql("""
    select t1.mode_of_payment
    from `tabPayment Entry`t1
    inner join `tabPayment Entry Reference` t2 on t2.parent = t1.name 
    and t2.reference_doctype = 'Sales Order' and t2.reference_name = %s
    union all
    select t1.mode_of_payment
    from 
    `tabJournal Entry` t1 inner join `tabJournal Entry Account` t2 on t2.parent = t1.name 
    and t2.reference_type = 'Room Folio HMS' and t1.mode_of_payment is not null
    where reference_name = %s
    limit 1 
    """, (folio.reservation, folio.name)):
        print_context.setdefault('mode_of_payment', d[0])

    print_context.setdefault('guest_address_display', "-")
    print_context.setdefault('sign_in_date', getdate())

    if print_context['address_name']:
        print_context['guest_address_display'] = get_address_display(
            print_context['address_name'])
    html = frappe.render_template(
        template, {"doc": folio, "ctx": print_context})

    print(html, "*" * 100)

    return html
