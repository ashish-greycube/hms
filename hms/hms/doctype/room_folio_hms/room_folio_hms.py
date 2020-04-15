# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, flt, cint, today, getdate, cstr
from erpnext.accounts.party import get_party_account, get_party_bank_account
from erpnext.accounts.utils import get_outstanding_invoices
import json
from hms.hms.doctype.room_ledger_entry_hms.room_ledger_entry_hms import make_room_ledger_entry
from hms.hms.doctype.room_status_ledger_entry_hms.room_status_ledger_entry_hms import update_room_status_ledger
from hms.hms.controllers.reservation import get_room_service_item
import erpnext
from frappe.contacts.doctype.address.address import get_address_display


class RoomFolioHMS(Document):
    def validate(self):
        if not self.sign_in_sheet:
            self.make_sign_in_sheet()

        if self.is_new() and self.status == "Checked In":
            self.validate_room_reservation()
            self.validate_room_status()

    def make_sign_in_sheet(self, no_letterhead=False):
        from bs4 import BeautifulSoup

        html = frappe.get_print(self.doctype, self.name, print_format="Folio Sign In",
                                doc=self, no_letterhead=no_letterhead)

        soup = BeautifulSoup(html, 'lxml')
        for s in soup.select('script'):
            s.extract()
        html = soup.prettify()

        print_dict = {}
        # custom_fields = ["sub_heading",
        #                  "guest_full_name",
        #                  "total_guest",
        #                  "guest_address_display",
        #                  "total_amount_weekdays",
        #                  "total_amount_weekends",
        #                  "total_room_charges",
        #                  "total_other_charges",
        #                  "mode_of_payment",
        #                  "guest_mobile",
        #                  "guest_email",
        #                  "total_taxes_and_charges", ]
        for d in frappe.db.sql("""
            select reservation, terms, gu.*
            from `tabRoom Folio HMS` f
            left outer join  
            (
                select gd.mobile guest_mobile, gd.email guest_email, gd.guest guest_full_name,
                gd.parent, co.address address_name
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
            
            max(so.rounded_total) total_charges,
            max(so.rounded_total) total_room_charges,
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
            print_dict.setdefault(
                'guest_address_display', get_address_display(print_dict['address_name']))

        for k, v in print_dict.items():
            html = html.replace("{doc.%s}" % k, cstr(v))

        doc = frappe.new_doc("Sign In Sheet HMS")
        doc.name = self.name
        doc.content = html
        doc.save()
        self.sign_in_sheet = doc.name

    def validate_room_reservation(self):
        """WHERE NOT (From_date > @RangeTill OR To_date < @RangeFrom)"""
        for d in frappe.db.sql("""
        select name reservation, room_no_cf, check_in_cf, check_out_cf
        from `tabSales Order`
        where docstatus = 1 and room_no_cf = %s and name <> %s
        and not (check_in_cf >= %s or check_out_cf <= %s)
        """, (self.room_no, self.reservation, self.check_out, self.check_in), as_dict=True):
            frappe.throw(
                f"Reservation {d.reservation} exists for room {d.room_no} between {d.check_in_cf} and {d.check_out_cf} ")

    def validate_room_status(self):
        for d in frappe.db.sql("""
        select status, reference_type, reference_name
        from `tabRoom Status Ledger Entry HMS`
        where room_no = %s and docstatus <> 2""", (self.room_no), as_dict=True):
            frappe.throw(
                f"Room {self.room_no} is {d.status} for {self.check_in} ")

    def after_insert(self):
        "check in"
        make_room_ledger_entry(date=self.check_in, room_no=self.room_no, reference_type=self.doctype,
                               reference_name=self.name, entry_type="Room Folio Check In")
        update_room_status_ledger(self.as_dict(), action="check_in")
        self.create_charge_purchase(self.check_in)

    def create_charge_purchase(self, room_date):
        """create sales invoice for room_date date"""
        if frappe.db.exists("Sales Invoice", {'room_folio_cf': self.name, 'room_date_cf': room_date}):
            frappe.throw(
                _("Sales Invoice already created for %s") % (room_date,))
            return

        from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
        out = make_sales_invoice(source_name=self.reservation)
        out.room_folio_cf = self.name
        out.due_date = self.check_out
        out.room_date_cf = room_date

        # remove lines for other dates in Sales Invoice, only bill for room_date
        so_detail = frappe.db.sql("""
        select soi.name from `tabRoom Folio HMS` f
        inner join `tabSales Order Item` soi on soi.parent = f.reservation 
        and ifnull(soi.reservation_date_cf,'') = %s
        where f.name = %s""", (getdate(room_date), self.name, ), debug=True)
        so_detail = so_detail and so_detail[0][0] or None
        for d in out.items:
            if not d.so_detail == so_detail:
                out.remove(d)
        out.save()
        return out.name

    def make_check_out(self):
        self.validate_billing()
        self.status = "Checked Out"
        self.save()
        make_room_ledger_entry(date=self.check_out, room_no=self.room_no, reference_type=self.doctype,
                               reference_name=self.name, entry_type="Room Folio Check Out")
        update_room_status_ledger(self.as_dict(), action="check_out")
        return self.as_dict()

    def validate_billing(self):
        pass

    def get_advances(self):
        """get unallocated advances by customer in Room Folio account"""
        pass

    def get_payment_entry(self):
        pe = frappe.new_doc("Payment Entry")
        pe.party_type = "Customer"
        pe.payment_type = "Receive"
        pe.posting_date = nowdate()
        pe.company = self.company
        pe.party = self.customer
        pe.paid_to = "Bank Of Nigeria - SH"
        pe.paid_amount = self.balance

        for doc in get_outstanding_invoices("Customer", self.customer, account="Debtors - SH"):
            pe.append("references", {
                'reference_doctype': doc["voucher_type"],
                'reference_name': doc["voucher_no"],
                "due_date": doc.get("due_date"),
                'total_amount': doc.get('invoice_amount'),
                'outstanding_amount': doc.get('outstanding_amount'),
                'allocated_amount': doc.get('outstanding_amount'),
            })

        pe.setup_party_account_field()
        pe.set_missing_values()
        return pe

    def update_charges_and_amounts(self):
        # TODO: set totals from charge purchase and advances
        pass


@frappe.whitelist()
def get_charge_and_purchase(docname):
    return frappe.db.sql("""
    select si.name, rf.name room_folio, rf.room_no, date_format(room_date_cf,'%%d %%b, %%y') room_date_cf, 
    date_format(posting_time,'%%H:%%i') posting_time, rounded_total, outstanding_amount
    from `tabRoom Folio HMS` rf
    inner join `tabSales Invoice` si on rf.name = ifnull(si.room_folio_cf, '')
    where rf.name = %(folio)s or rf.master_folio = %(folio)s""", dict(folio=docname, ), as_dict=True)


@frappe.whitelist()
def make_transfer_jv(**args):
    args = frappe._dict(args)
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = erpnext.get_default_company()
    je.posting_date = today()
    je.remark = f"Transfer of funds for {args.customer}. Folio#: {args.folio}"

    if args.get('transfer_type') == "Transfer to Room":
        debit_account = args.desk_account
        credit_account = args.folio_account
    else:
        credit_account = args.desk_account
        debit_account = args.folio_account

    je.append("accounts", {
        "account":  credit_account,
        "party_type": 'Customer',
        'party': args.customer,
        'debit_in_account_currency': 0,
        'credit_in_account_currency': flt(args.amount_to_transfer)
    })

    je.append("accounts", {
        "account": debit_account,
        "party_type": 'Customer',
        'party': args.customer,
        'debit_in_account_currency': flt(args.amount_to_transfer),
        'credit_in_account_currency': 0
    })
    je.insert(ignore_permissions=True)
    je.submit()


@frappe.whitelist()
def get_party_balance(party, company):
    from erpnext.accounts.utils import get_balance_on
    default_desk_account = frappe.defaults.get_user_default(
        'default_desk_receivable_account')
    default_folio_account = frappe.defaults.get_user_default(
        'default_folio_receivable_account')

    balance = dict()

    balance["desk"] = {
        'account': default_desk_account,
        'balance': get_balance_on(account=default_desk_account, date=today(),
                                  party_type="Customer", party=party,
                                  ignore_account_permission=True,
                                  company=erpnext.get_default_company(), ),
    }
    balance["folio"] = {
        'account': default_folio_account,
        'balance': get_balance_on(account=default_folio_account, date=today(),
                                  party_type="Customer", party=party,
                                  ignore_account_permission=True,
                                  company=erpnext.get_default_company(), )
    }

    print(balance, "balance")
    return balance


@frappe.whitelist()
def get_nonreconciled_payment_entries(**args):
    doc = frappe.new_doc('Payment Reconciliation')
    doc.update(args)
    doc.get_nonreconciled_payment_entries()
    return doc.payments or []
