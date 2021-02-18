# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import (
    formatdate,
    get_link_to_form,
    cstr,
    getdate,
    date_diff,
    add_to_date,
    add_days,
    cint,
    flt,
    today,
)
import erpnext
from erpnext import get_company_currency, get_default_company
from erpnext.accounts.doctype.journal_entry.journal_entry import (
    get_default_bank_cash_account,
    get_balance_on,
)


def validate_sales_order(doc, method):
    if doc.docstatus == 0 and date_diff(today(), doc.check_in_cf) > 0:
        # frappe.throw(_("Check In date cannot be earlier than today."))
        pass

    validate_availability(doc.check_in_cf, doc.check_out_cf, doc.room_no_cf)
    if not doc.guest_cf:
        frappe.throw(_("Please select guest for Reservation."))

    if not doc.tc_name:
        doc.tc_name = frappe.db.get_single_value(
            "HMS Settings", "sign_in_terms_and_conditions"
        )


def validate_item_price(doc, method):
    if not doc.weekend_rate_cf:
        doc.weekend_rate_cf = doc.price_list_rate


def validate_availability(check_in, check_out, room_no):
    # If ( NOT (EndA <= StartB or StartA >= EndB) ; “Overlap”)
    args = dict(check_in=check_in, check_out=check_out, room_no=room_no)

    for d in frappe.db.sql(
        """
    select 'Reservation' doctype, 'Sales Order' ref_type, t.name, check_in_cf check_in, check_out_cf check_out
    from `tabSales Order` t
    where t.docstatus = 1 and room_no_cf = %(room_no)s
    and not exists (select 1 from `tabRoom Folio HMS` where reservation = t.name)
    and not (t.check_out_cf <= %(check_in)s or t.check_in_cf >= %(check_out)s)
    union all
    select 'Room Folio', 'Room Folio', t.name, t.check_in, t.check_out
    from `tabRoom Folio HMS` t
    where t.docstatus <> 2 and t.room_no = %(room_no)s
    and (t.status = 'Checked In' or t.status = 'Pre-Check In')
    and not (t.check_out <= %(check_in)s or t.check_in >= %(check_out)s)
    """,
        args,
        as_dict=True,
    ):
        frappe.throw(
            _("{0} {1} already exists for dates {2} to {3}").format(
                d["doctype"],
                get_link_to_form(d["ref_type"], d["name"]),
                frappe.bold(formatdate(d["check_in"])),
                frappe.bold(
                    formatdate(
                        d["check_out"],
                    )
                ),
            )
        )


@frappe.whitelist()
def get_holidays(company, check_in, check_out):
    day_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    weekends, holidays = [], []
    for d in frappe.db.sql(
        """select
        date_format(d.date,'%%Y-%%m-%%d') date, h.description
        from `tabDate Lookup HMS` d
        inner join tabHoliday h on h.holiday_date = d.date and h.holiday_date BETWEEN %s and %s
        and EXISTS (select 1 from tabCompany where default_holiday_list = h.parent)
        """,
        (check_in, add_days(check_out, -1)),
        as_dict=True,
    ):
        if d.description in day_names:
            weekends.append(d.date)
        else:
            holidays.append(d.date)

    holiday_price_list = frappe.db.get_value(
        "Company", company, "default_holiday_price_list_cf"
    )

    return dict(
        holidays=holidays, weekends=weekends, holiday_price_list=holiday_price_list
    )


@frappe.whitelist()
def get_room_service_item(room):
    docs = frappe.db.sql_list(
        """select rt.service_item
from `tabRoom Type HMS` rt
inner join `tabRoom HMS` r on r.room_type = rt.name and r.name = %s""",
        (room,),
    )
    return docs and docs[0]


@frappe.whitelist()
def make_room_folio(docname):
    so = frappe.get_doc("Sales Order", docname)
    folio = frappe.new_doc("Room Folio HMS")
    folio.update(
        {
            "company": so.company,
            "naming_series": "HMS-RR-.YY.-",
            "company": so.company,
            "customer": so.customer,
            "room_no": so.room_no_cf,
            "check_in": so.check_in_cf,
            "check_out": so.check_out_cf,
        }
    )
    folio.append("room_guest_detail", {"guest": so.guest_cf})
    # TODO: add advance payments
    folio.insert()
    return folio


@frappe.whitelist()
def get_reservation_details(room_no, date):
    data = frappe.db.sql(
        """
select d.date, r.name name, r.room_no room_no, r.room_type,
coalesce(a.no_nights,b.no_nights) total_nights, coalesce(a.customer,b.customer) customer,
coalesce(gd.guest, b.guest, a.customer, b.customer) guest,
a.name `folio`, b.name `reservation`, con.email_id, con.mobile_no, con.gender,
coalesce(a.total_charges, b.rounded_total,0) total_charges, coalesce(b.room_rate_cf,0) rate,
coalesce(b.weekend_rate_cf,0) as weekend_rate
-- ,a.*, b.*
from
`tabDate Lookup HMS` d
cross join `tabRoom HMS` r
left outer join
(
    -- room folio
    select fo.room_no, fo.check_in, fo.check_out, fo.customer, fo.name, fo.status,
    datediff(fo.check_out, fo.check_in) no_nights, fo.total_charges
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
    so.guest_cf guest, so.customer, no_of_nights_cf no_nights, room_rate_cf, weekend_rate_cf,
    so.advance_paid, so.rounded_total
    from `tabSales Order` so
    -- where not exists (select 1 from `tabRoom Folio HMS` x where x.reservation = so.name)
) b on d.date BETWEEN b.check_in and b.check_out and r.name = b.room_no
left outer join tabContact con on con.name = coalesce(gd.guest, b.guest,'')
where d.date = %(date)s and r.name = %(room_no)s
order by d.date, r.room_type, r.room_no
    """,
        dict(date=date, room_no=room_no),
        as_dict=True,
        debug=0,
    )
    details = data and data[0] or {}
    if details:
        from frappe.contacts.doctype.contact.contact import (
            get_contact_details,
            get_default_contact,
        )

        details["guest"] = get_contact_details(details["guest"])["contact_display"]
    return details


@frappe.whitelist()
def make_transfer_jv_to_sales_order(customer, amount_to_transfer, docname):
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = erpnext.get_default_company()
    je.posting_date = today()
    je.remark = f"Advance towards reservation for {customer}. Reservation#: {docname}"

    default_desk_account = frappe.defaults.get_user_default(
        "default_desk_receivable_account"
    )

    je.append(
        "accounts",
        {
            "account": default_desk_account,
            "party_type": "Customer",
            "party": customer,
            "reference_type": "Sales Order",
            "reference_name": docname,
            "debit_in_account_currency": 0,
            "credit_in_account_currency": flt(amount_to_transfer),
            "is_advance": "Yes",
        },
    )

    je.append(
        "accounts",
        {
            "account": default_desk_account,
            "party_type": "Customer",
            "party": customer,
            "debit_in_account_currency": flt(amount_to_transfer),
            "credit_in_account_currency": 0,
        },
    )
    je.insert(ignore_permissions=True)
    je.submit()


@frappe.whitelist()
def get_default_contact(customer):
    from frappe.contacts.doctype.contact.contact import get_default_contact

    return get_default_contact("Customer", customer)


@frappe.whitelist()
def get_item_rates(item_code=None, price_list=None, company=None, customer=None):
    if not item_code or not price_list or not company or not customer:
        return {"weekend_rate": 0, "rate": 0}

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
        "price_list": frappe.db.get_value(
            "Company", company, "default_holiday_price_list_cf"
        ),
        "conversion_rate": 1,
    }
    # weekend rate
    _dict = apply_price_list(args)
    out.setdefault(
        "weekend_rate", _dict.get("children", [{}])[0].get("price_list_rate", 0)
    )
    # standard rate
    args["price_list"] = price_list
    _dict = apply_price_list(args)
    out.setdefault("rate", _dict.get("children", [{}])[0].get("price_list_rate", 0))
    return out


@frappe.whitelist()
def check_guest_id(contact):
    return frappe.db.get_value("Contact", contact, "image") or ""


@frappe.whitelist()
def attach_contact_id(docname, date, data_url):
    from six.moves.urllib.request import urlopen

    attachment = urlopen(data_url).read()
    file_name = f"{docname}_{date}.jpg"
    _file = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": file_name,
            "attached_to_doctype": "Contact",
            "attached_to_name": docname,
            "is_private": True,
            "content": attachment,
        }
    )
    _file.save()
    frappe.db.set_value("Contact", docname, "image", _file.file_url)
    return _file.name


@frappe.whitelist()
def make_payment_entry_from_sales_order(
    mode_of_payment,
    paid_amount,
    customer,
    sales_order=None,
    reference_no=None,
    reference_date=None,
):
    paid_amount = flt(paid_amount)
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

    company = erpnext.get_default_company()

    default_desk_account = frappe.defaults.get_user_default(
        "default_desk_receivable_account"
    )
    cash_bank_account = get_default_bank_cash_account(
        company, mode_of_payment=mode_of_payment
    )

    payments = []

    if sales_order:
        payment = get_payment_entry("Sales Order", sales_order)
        payment.paid_amount = payment.received_amount = abs(flt(paid_amount))
        if not payment.base_paid_amount == 0:
            for d in payment.references:
                d.allocated_amount = min(paid_amount, d.outstanding_amount)
            payments.append(payment)

        # rounded_total, advance_paid = frappe.db.get_value(
        #     "Sales Order",
        #     sales_order,
        #     ["rounded_total", "advance_paid"],
        # )
        # excess_amount = paid_amount + advance_paid - rounded_total
        # if excess_amount > 0:
        #     # Allow Payment more than SO amount, create in Desk Folio
        #     # create payment entry for excess amount with no reference
        #     pe = frappe.new_doc("Payment Entry")
        #     pe.paid_amount = pe.received_amount = abs(excess_amount)
        #     payments.append(pe)
    else:
        payment = frappe.new_doc("Payment Entry")
        payment.paid_amount = payment.received_amount = abs(flt(paid_amount))
        payments.append(payment)

    for payment in payments:
        payment.posting_date = frappe.flags.current_date
        payment.payment_type = "Receive"
        payment.mode_of_payment = mode_of_payment
        payment.party_type = "Customer"
        payment.party = customer
        payment.paid_to = cash_bank_account.account
        payment.paid_from = default_desk_account
        if not mode_of_payment == "Cash":
            payment.reference_no = reference_no
            payment.reference_date = reference_date
        payment.total_allocated_amount = (
            sum([d.allocated_amount for d in payment.get("references", [])]) or 0
        )
        # payment.difference_amount = 0

        # payment.base_paid_amount
        # payment.received_amount
        # payment.base_received_amount
        # payment.total_allocated_amount
        # payment.base_total_allocated_amount

        payment.setup_party_account_field()
        payment.set_missing_values()
        payment.save()
        payment.submit()
    return payments[0]


@frappe.whitelist()
def validate_sales_order_checklist(docname, guest, customer, company, advance_paid):
    validation = []
    if not frappe.db.get_value("Contact", guest, "image"):
        validation += [
            "Please capture ID for guest %s" % get_link_to_form("Contact", guest)
        ]
    default_desk_account = frappe.defaults.get_user_default(
        "default_desk_receivable_account"
    )
    allow_checkin_without_advance = cint(
        frappe.db.get_value("Customer", customer, "allow_checkin_without_advance_cf")
    )
    party_balance = get_balance_on(
        account=default_desk_account,
        date=today(),
        party_type="Customer",
        party=customer,
        company=company,
        ignore_account_permission=True,
    )
    party_balance = party_balance and flt(party_balance) > 0
    if (
        not cint(advance_paid)
        and not allow_checkin_without_advance
        and not party_balance
    ):
        validation += [
            "Please make payment against this Reservation to be able to Check In."
        ]
    return validation and "<br>".join([frappe.bold(d) for d in validation]) or ""


@frappe.whitelist()
def get_checked_in_folios():
    return frappe.db.sql(
        """
      select customer, room_type, room_no, date_format(check_in,'%d-%b') check_in,
      date_format(check_out,'%d-%b') check_out, name folio
      from `tabRoom Folio HMS` where status = 'Checked In'
    """,
        as_dict=True,
    )


@frappe.whitelist()
def get_available_rooms(doctype, txt, searchfield, start, page_len, filters):
    """
    filters = {
            item_code='Luxury Room Charge',
            room_type='DLX-SH',
            check_in='2020-10-01',
            check_out='2020-10-02',
            company='SH'
    }
    """
    filters["txt"] = "%%%s%%" % txt

    if not filters.get("check_in") or not filters.get("check_out"):
        frappe.msgprint(_("Please select dates for resevation."))

    where_clause = ""
    if filters.get("item_code"):
        where_clause = " where room_type = (select room_type_cf from tabItem where name = %(item_code)s)"
    elif filters.get("room_type"):
        where_clause = " where r.room_type = %(room_type)s"

    return frappe.db.sql(
        """
        select *
        from
            (
            select name
            from
                `tabRoom HMS` r
            {where_clause}
            except
            select fo.room_no
            from
                `tabRoom Folio HMS` fo
            where
                not (fo.check_in >= %(check_out)s OR fo.check_out <= %(check_in)s)
                and fo.docstatus = 1 and fo.status = 'Checked In'
            except
            select so.room_no_cf room_no
            from
                `tabSales Order` so
            where
                not (so.check_in_cf >= %(check_out)s OR so.check_out_cf <= %(check_in)s)
                and not exists (select 1 from `tabRoom Folio HMS` x where x.reservation = so.name)
                and so.docstatus = 1
            except
            select room_no
            from
                `tabRoom Status Ledger Entry HMS`
            where
                docstatus <> 2 and status = 'Out Of Order'
            ) t
        where
            t.name like %(txt)s
        """.format(
            where_clause=where_clause
        ),
        filters,
        debug=0,
    )


@frappe.whitelist()
def move_room(reservation, room_no):
    so = frappe.db.get_value(
        "Sales Order",
        filters={
            "name": reservation,
        },
        fieldname=["docstatus", "check_in_cf", "check_out_cf", "room_no_cf"],
        as_dict=True,
    )
    if not so:
        frappe.throw("Reservation %s cannot be modified.", (reservation,))
    validate_availability(so.check_in_cf, so.check_out_cf, room_no)

    frappe.db.sql(
        """
    update `tabSales Order`
    set room_no_cf= %s
    where name = %s""",
        (room_no, reservation),
    )
    frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def get_rooms_available(**args):
    args["company"] = get_default_company()
    args["room_type"] = frappe.db.get_value(
        "Item", {"name": args.get("package", None)}, "room_type_cf"
    )
    rooms = get_available_rooms(None, "", None, 0, 100, args)
    return rooms and len(rooms) or 0


def autoname_contact(doc, method):
    # concat first and last name
    doc.name = " ".join(
        filter(None, [cstr(doc.get(f)).strip() for f in ["first_name", "last_name"]])
    )
    from frappe.model.naming import append_number_if_name_exists

    if frappe.db.exists("Contact", doc.name):
        doc.name = append_number_if_name_exists("Contact", doc.name)


@frappe.whitelist(allow_guest=True)
def __get_online_packages():
    return frappe.db.sql(
        """
    select i.item_code label, i.item_code value, i.room_type_cf, 
    123 room_rate, '₦ 250.00' description
    from tabItem i
    where i.item_group = 'Room Charges'""",
        as_dict=True,
    )


@frappe.whitelist(allow_guest=True)
def get_online_room_types():
    return frappe.get_all(
        "Room Type HMS", fields=["room_type as value", "room_type as label", "name"]
    )


@frappe.whitelist(allow_guest=True)
def get_online_packages():
    return frappe.db.sql(
        """
        select i.item_code label, i.item_code value, 
        rt.room_type, 
        COALESCE(ip.price_list_rate,0) room_rate,
        concat(i.item_name, ', ₦', round(COALESCE(ip.price_list_rate,0))) description
        from tabItem i
        inner join `tabRoom Type HMS` rt on rt.name = i.room_type_cf
        inner join `tabItem Price` ip on ip.item_code = i.item_code and ip.selling = 1
        and %(today)s BETWEEN  ifnull(ip.valid_from, '1900-01-01') and ifnull(valid_upto, '2500-12-31')
        and ip.price_list = (select sing.value from tabSingles sing where sing.field = 'selling_price_list'
        and sing.doctype = 'Selling Settings')""",
        dict(company=get_default_company(), today=getdate()),
        as_dict=True,
    )


def update_room_folio_charges():
    room_folios = dict()
    for d in frappe.get_all(
        "Sales Invoice",
        filters=[["room_folio_cf", "not in", (None)]],
        fields=["name", "outstanding_amount", "base_rounded_total", "room_folio_cf"],
    ):
        item = room_folios.setdefault(
            d.room_folio_cf, dict(total_charges=0.0, outstanding_charges=0.0)
        )
        item["total_charges"] += flt(d.base_rounded_total)
        item["outstanding_charges"] += flt(d.outstanding_amount)

    for folio, values in room_folios.items():
        print(folio, values)
        frappe.db.set_value(
            "Room Folio HMS", folio, "total_charges", values["total_charges"]
        )
        frappe.db.set_value(
            "Room Folio HMS",
            folio,
            "outstanding_charges",
            values["outstanding_charges"],
        )

    frappe.db.commit()
