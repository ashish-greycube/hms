# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (nowdate, flt, cint, today,
                          getdate, cstr, now, get_link_to_form)
from erpnext.accounts.party import get_party_account, get_party_bank_account
from erpnext.accounts.utils import get_outstanding_invoices
import json
from hms.hms.doctype.room_ledger_entry_hms.room_ledger_entry_hms import make_room_ledger_entry
from hms.hms.doctype.room_status_ledger_entry_hms.room_status_ledger_entry_hms import update_room_status_ledger
from hms.hms.controllers.reservation import get_room_service_item
import erpnext


class RoomFolioHMS(Document):
    def validate(self):
        if self.is_new() and self.status == "Checked In":
            self.validate_room_reservation()
            self.validate_room_status()

        self.update_charges_and_amounts()
        self.validate_checklist()
        self.validate_duplicate_checkin()

    def validate_duplicate_checkin(self):
        for d in frappe.db.sql("""select name from `tabRoom Folio HMS`
        where reservation = %s and name <> %s limit 1""", (self.reservation, self.name)):
            rf_link = get_link_to_form("Room Folio HMS", d[0])
            so_link = get_link_to_form("Sales Order", self.reservation)
            frappe.throw(_("Room Folio {} already created for reservation {}.").format(
                rf_link, so_link))

    def make_sign_in_sheet(self):
        from hms.hms.doctype.sign_in_sheet_hms.sign_in_sheet_hms import make_sign_in_sheet
        return make_sign_in_sheet(self.name)

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

    def validate_checklist(self):
        '''
        1. Guest ID
        2. advance paid
        3. Sign In Sheet signed'''
        if cint(self.is_checklist_done):
            return ""

        checklist = []
        valid = frappe.db.sql("""
            select
            if(f.total_advance_paid>0,1,0) advance_amount,
            if(con.name is not null,1,0) guest_id,
            if(sg.name is not null,1,0) sign_in_sheet
            from `tabRoom Folio HMS` f
            inner join `tabSales Order` so on so.name = f.reservation
            left outer join tabContact con on con.name = so.guest_cf and con.image is not null
            left outer join `tabSign In Sheet HMS` sg on sg.name = f.sign_in_sheet and sg.signature is not null
            where f.name = %s limit 1""", (self.name,), as_dict=True)
        valid = valid and valid[0] or {
            'advance_amount': 0, "guest_id": 0, 'sign_in_sheet': 0}
        for k, v in valid.items():
            if not cint(v):
                checklist.append(folio_checklist[k])
        if not checklist:
            self.db_set('is_checklist_done', 1)

        return checklist and "<br>".join(checklist) or ""

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
        out.due_date = max(getdate(self.check_out), getdate(now()))
        out.room_date_cf = room_date
        out.debit_to = frappe.defaults.get_user_default(
            'default_folio_receivable_account')

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
        out.submit()
        return out.name

    def make_check_out(self):
        self.validate_room_folio_balance()
        self.status = "Checked Out"
        self.save()
        make_room_ledger_entry(date=self.check_out, room_no=self.room_no, reference_type=self.doctype,
                               reference_name=self.name, entry_type="Room Folio Check Out")
        update_room_status_ledger(self.as_dict(), action="check_out")
        return self.as_dict()

    def validate_room_folio_balance(self):
        # frappe.db.sql("""
        #     select debit,  voucher_type, voucher_no,  against_voucher_type, against_voucher, party, against, account, credit, debit
        #     from `tabGL Entry`
        #     where creation > '2020-04-27'
        # """)
        if False:
            frappe.throw(
                _('Balance is not settled in folio {}').format(self.name))

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
        paid_to = frappe.get_cached_value(
            'Company',  self.company,  "default_cash_account")
        pe.paid_to = paid_to
        pe.paid_amount = self.balance
        pe.received_amount = self.balance
        pe.room_folio_cf = self.name
        #
        default_desk_account = frappe.defaults.get_user_default(
            'default_desk_receivable_account')

        # Payment Reconciliation is used to set off invoice-payments at the time of checkout
        # uncomment below to show invoices to adjust payment against, if above workflow changes
        # for doc in get_outstanding_invoices("Customer", self.customer, account=default_desk_account):
        #     pe.append("references", {
        #         'reference_doctype': doc["voucher_type"],
        #         'reference_name': doc["voucher_no"],
        #         "due_date": doc.get("due_date"),
        #         'total_amount': doc.get('invoice_amount'),
        #         'outstanding_amount': doc.get('outstanding_amount'),
        #         'allocated_amount': doc.get('outstanding_amount'),
        #     })

        pe.setup_party_account_field()
        pe.set_missing_values()
        return pe

    def update_charges_and_amounts(self):
        # set totals from charge purchase and advances
        charges = frappe.db.sql("""
        select COALESCE(sum(si.rounded_total),0) from `tabSales Invoice` si where NULLIF(si.room_folio_cf, '') = %s
        """, (self.name))
        self.total_charges = charges[0][0] or 0
        self.balance = flt(self.total_charges) - flt(self.total_advance_paid)


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

    against_voucher, against_voucher_type = "", ""

    if args.get('transfer_type') == "Transfer to Room":
        debit_account = args.desk_account
        credit_account = args.folio_account
        against_voucher = args.folio
        against_voucher_type = 'Room Folio HMS'
    else:
        credit_account = args.desk_account
        debit_account = args.folio_account

    je.append("accounts", {
        "account":  credit_account,
        "party_type": 'Customer',
        'party': args.customer,
        'debit_in_account_currency': 0,
        'credit_in_account_currency': flt(args.amount_to_transfer),
        'is_advance': 'Yes',
        'reference_name': against_voucher,
        'reference_type': against_voucher_type
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
    # update folio total_advance_paid, amounts
    folio = frappe.get_doc('Room Folio HMS', args.folio)
    folio.total_advance_paid = folio.total_advance_paid + \
        flt(args.amount_to_transfer)
    folio.save()


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


folio_checklist = {
    "guest_id": _("Please attach Identification for guest"),
    "advance_amount": _("Please make an advance payment for the folio."),
    "sign_in_sheet": "Please complete Sign In Sheet for guest"


}


def update_checklist_status(sign_in_sheet=None):
    if sign_in_sheet:
        for d in frappe.db.sql("""select name
        from `tabRoom Folio HMS` where sign_in_sheet = %s""", (sign_in_sheet)):
            frappe.get_doc('Room Folio HMS', d[0]).validate_checklist()


def update_charges_and_amounts(doc, method):
    if doc.room_folio_cf:
        rf = frappe.get_doc("Room Folio HMS", doc.room_folio_cf)
        if rf.docstatus < 2:
            rf.save()


def on_submit_payment_entry(doc, method):
    pass
    # if doc.room_folio_cf and doc.payment_type == 'Receive':
    #     for d in doc.
