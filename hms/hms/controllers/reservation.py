# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import (formatdate, get_link_to_form,
                          getdate, date_diff, add_to_date, add_days, cint, flt, today)
import erpnext


def validate_sales_order(doc, method):
    for d in frappe.db.sql("""
select led.date, reference_type, reference_name
from
(
    select ROW_NUMBER() over (PARTITION BY date ORDER BY creation desc) rn,
    reference_type, reference_name, date, entry_type
    from `tabRoom Ledger Entry HMS`
    where room_no = %s and entry_type <> 'Room Folio Check Out'
) led where led.rn = 1 and led.date >= %s  and led.date < %s""",
                           (doc.room_no_cf, doc.check_in_cf, doc.check_out_cf), as_dict=True,):
        doctype = 'Reservation' if d.reference_type == 'Sales Order' else d.reference_type
        frappe.throw(_("Reservation conflicts with {} on {}")
                     .format(get_link_to_form(d.reference_type, d.reference_name), frappe.bold(formatdate(d.date))))


def on_submit_sales_order(doc, method):
    from hms.hms.doctype.room_ledger_entry_hms.room_ledger_entry_hms import make_room_ledger_entry
    for d in [add_days(doc.check_in_cf, _)
              for _ in range(0, cint(doc.no_of_nights_cf))]:
        make_room_ledger_entry(date=d, room_no=doc.room_no_cf, reference_type=doc.doctype,
                               reference_name=doc.name, entry_type="Reservation")


def on_update_after_submit_sales_order(doc, method):
    frappe.db.sql(
        """update `tabRoom Ledger HMS` set status = 'Cancelled'
        where parent = %s and parenttype='Sales Order'""", (doc.name,))
    add_room_ledger_entry(doc)


def on_cancel_sales_order(doc, method):
    frappe.db.sql("""
    update `tabRoom Ledger Entry HMS`
    set status = 'Cancelled'
    where parent = %s and parenttype='Sales Order'
    """, (doc.name,))


@frappe.whitelist()
def get_holidays(company, check_in, check_out):
    holidays = frappe.db.sql("""select date_format(d.date,'%%Y-%%m-%%d')
        from `tabDate Lookup HMS` d
        inner join tabHoliday h on h.holiday_date = d.date and h.holiday_date BETWEEN %s and %s
        and EXISTS (select 1 from tabCompany where default_holiday_list = h.parent)
        """, (check_in, add_days(check_out, -1)), as_list=True)

    holiday_price_list = frappe.db.get_value(
        'Company', company, 'default_holiday_price_list_cf')

    return dict(holidays=[d[0] for d in holidays], holiday_price_list=holiday_price_list)


@frappe.whitelist()
def get_room_service_item(room):
    docs = frappe.db.sql_list("""select rt.service_item
from `tabRoom Type HMS` rt
inner join `tabRoom HMS` r on r.room_type = rt.name and r.name = %s""", (room,))
    return docs and docs[0]


@frappe.whitelist()
def make_room_folio(docname):
    so = frappe.get_doc("Sales Order", docname)
    folio = frappe.new_doc("Room Folio HMS")
    folio.update({
        "company": so.company,
        "naming_series": "HMS-RR-.YY.-",
        "company": so.company,
        "customer": so.customer,
        "room_no": so.room_no_cf,
        "check_in": so.check_in_cf,
        "check_out": so.check_out_cf,
    })
    folio.append("room_guest_detail", {
        "guest": so.guest_cf
    })
    # TODO: add advance payments
    folio.insert()
    return folio


@frappe.whitelist()
def get_reservation_details(room_no, date):
    data = frappe.db.sql("""
select d.date, r.name name, r.room_no room_no, r.room_type,
coalesce(a.no_nights,b.no_nights) total_nights, coalesce(a.customer,b.customer) customer,
coalesce(gd.guest, b.guest, a.customer, b.customer) guest,
a.name `folio`, b.name `reservation`, con.email_id, con.mobile_no, con.gender,
coalesce(a.total_advance_paid, b.advance_paid, 0) total_advance_paid,
coalesce(a.total_charges, b.rounded_total,0) total_charges
-- ,a.*, b.*
from
`tabDate Lookup HMS` d
cross join `tabRoom HMS` r
left outer join
(
    -- room folio
    select fo.room_no, fo.check_in, fo.check_out, fo.customer, fo.name, fo.status,
    datediff(fo.check_out, fo.check_in) no_nights, fo.total_charges, fo.total_advance_paid
    from `tabRoom Folio HMS` fo
) a on d.date BETWEEN a.check_in and a.check_out and r.name = a.room_no
left outer join `tabRoom Guest Detail HMS` gd on gd.name = (
    select x.name from `tabRoom Guest Detail HMS` x
    where x.parent = a.name limit 1
)
left outer join
(
    -- reservation
    select so.name, so.room_no_cf room_no, so.check_in_cf check_in, so.check_out_cf check_out,
    so.guest_cf guest, so.customer, no_of_nights_cf no_nights,
    so.advance_paid, so.rounded_total
    from `tabSales Order` so
    where not exists (select 1 from `tabRoom Folio HMS` x where x.reservation = so.name)
) b on d.date BETWEEN b.check_in and b.check_out and r.name = b.room_no
left outer join tabContact con on con.name = coalesce(gd.guest, b.guest,'')
where d.date = %(date)s and r.name = %(room_no)s
order by d.date, r.room_type, r.room_no
    """, dict(date=date, room_no=room_no), as_dict=True, debug=True)
    return data and data[0] or {}


@frappe.whitelist()
def make_transfer_jv_to_sales_order(customer, amount_to_transfer, docname):
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = erpnext.get_default_company()
    je.posting_date = today()
    je.remark = f"Advance towards reservation for {customer}. Reservation#: {docname}"

    default_desk_account = frappe.defaults.get_user_default(
        'default_desk_receivable_account')

    je.append("accounts", {
        "account":  default_desk_account,
        "party_type": 'Customer',
        'party': customer,
        'reference_type': 'Sales Order',
        'reference_name': docname,
        'debit_in_account_currency': 0,
        'credit_in_account_currency': flt(amount_to_transfer),
        'is_advance': 'Yes'
    })

    je.append("accounts", {
        "account": default_desk_account,
        "party_type": 'Customer',
        'party': customer,
        'debit_in_account_currency': flt(amount_to_transfer),
        'credit_in_account_currency': 0
    })
    je.insert(ignore_permissions=True)
    je.submit()


@frappe.whitelist()
def get_default_contact(customer):
    from frappe.contacts.doctype.contact.contact import get_default_contact
    return get_default_contact('Customer', customer)


@frappe.whitelist()
def get_item_rates(item_code, price_list, company, customer):
    from erpnext.stock.get_item_details import apply_price_list
    out = {}
    args = {
        "items": [
            {
                "parenttype": "Sales Order",
                "doctype": "Sales Order Item",
                "item_code": item_code,
                "qty": 1,
                "stock_uom": "Nos",
            }
        ],
        "doctype": "Sales Order",
        "transaction_date": today(),
        "company": company,
        "customer": customer,
        "price_list": frappe.db.get_value("Company", erpnext.get_default_company(), 'default_holiday_price_list_cf'),
        "conversion_rate": 1,
    }
# weekend rate
    _dict = apply_price_list(args)
    out.setdefault('weekend_rate', _dict.get(
        'children', [{}])[0].get("price_list_rate", 0))
# standard rate
    args["price_list"] = price_list
    _dict = apply_price_list(args)
    out.setdefault('rate', _dict.get(
        'children', [{}])[0].get("price_list_rate", 0))
    return out
