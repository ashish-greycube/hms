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
from hms.hms.doctype.room_status_ledger_entry_hms.room_status_ledger_entry_hms import update_room_status_ledger
from hms.hms.controllers.reservation import get_room_service_item
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account
import erpnext
from six import iteritems, string_types
from frappe.utils.formatters import format_value


class RoomFolioHMS(Document):
    def validate(self):
        if self.is_new() and self.status == "Checked In":
            self.validate_room_reservation()
            self.validate_room_status()

        self.validate_checklist()
        self.validate_duplicate_checkin()
        self.update_charges_and_amounts()

    def validate_duplicate_checkin(self):
        for d in frappe.db.sql("""select name from `tabRoom Folio HMS`
        where reservation = %s and name <> %s limit 1""", (self.reservation, self.name)):
            rf_link = get_link_to_form("Room Folio HMS", d[0])
            so_link = get_link_to_form("Sales Order", self.reservation)
            frappe.throw(_("Room Folio {} already created for reservation {}.").format(
                rf_link, so_link))
        for d in frappe.db.sql("""
select name
        from `tabRoom Folio HMS`
        where name <> %s
        and room_no = %s
        and status <> 'Checked Out'
        and not (check_in >= %s or check_out <= %s)
        limit 1""", (self.name, self.room_no, self.check_out, self.check_in)):
            frappe.throw(_("Room Folio dates overlap with existing room folio {}.").format(
                get_link_to_form("Room Folio HMS", d[0])))

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
        self.update_charges_and_amounts()
        self.validate_room_folio_balance()
        self.db_set('status', "Checked Out", update_modified=True)
        update_room_status_ledger(self.as_dict(), action="check_out")
        return self.as_dict()

    def validate_room_folio_balance(self):
        if not self.balance == 0:
            frappe.throw(
                _('Unsettled balance {} exists in folio. Please settle balance before checkout.').format(
                    format_value(self.balance, df="Currency")))

    def make_folio_advance_entry(self):
        args = json.loads(frappe.local.form_dict['args'] or "{}")
        mode_of_payment = args.get('mode_of_payment')
        amount = flt(args.get('paid_amount', 0))
        je = frappe.new_doc("Journal Entry")
        je.posting_date = nowdate()
        je.mode_of_payment = mode_of_payment
        je.voucher_type = 'Journal Entry'
        je.company = self.company
        if not mode_of_payment == "Cash":
            je.cheque_no = args.get('reference_no')
            je.cheque_date = args.get('reference_date')

        cash_bank_account = get_default_bank_cash_account(
            self.company, mode_of_payment=mode_of_payment)

        folio_account = frappe.defaults.get_user_default(
            'default_folio_receivable_account')

        if args.get('payment_type') == "Receive":
            je.remark = 'Room Folio advance against: ' + self.name
            je.append("accounts", {
                "account":  folio_account,
                "party_type": "Customer",
                "party": self.customer,
                "reference_type": self.doctype,
                "reference_name": self.name,
                "is_advance": "Yes",
                "credit_in_account_currency": amount,
            })

            je.append("accounts", {
                "account": cash_bank_account.account,
                "account_currency": cash_bank_account.account_currency,
                "account_type": cash_bank_account.account_type,
                "debit_in_account_currency": amount,
            })
        else:
            je.remark = 'Room Folio refund against: ' + self.name
            je.append("accounts", {
                "account":  cash_bank_account.account,
                "account_currency": cash_bank_account.account_currency,
                "account_type": cash_bank_account.account_type,
                "credit_in_account_currency": amount,
            })

            je.append("accounts", {
                "account": folio_account,
                "party_type": "Customer",
                "party": self.customer,
                "debit_in_account_currency": amount,
                "reference_type": self.doctype,
                "reference_name": self.name,
            })

        je.insert(ignore_permissions=True)
        je.submit()
        self.update_charges_and_amounts()
        frappe.msgprint(_("Payment created."), alert=True)

    def update_charges_and_amounts(self):
        total_charges, total_advance_paid = 0, 0
        # set totals from charge purchase and advances
        for d in frappe.db.sql("""
select sum(si.rounded_total)
        from `tabSales Invoice` si
        where NULLIF(si.room_folio_cf, '') = %s""", (self.name)):
            total_charges = d[0]

        for d in frappe.db.sql("""
            select 0-sum(debit-credit) total_advance
            from `tabGL Entry`
            where account = 'Room Folio Debtors - SH'
            and party = %(customer)s
            and against_voucher_type = 'Room Folio HMS'
            and against_voucher = %(folio)s
        """, dict(folio=self.name, customer=self.customer)):
            total_advance_paid += flt(d[0])

        total_charges = total_charges or 0
        total_advance_paid = total_advance_paid or 0

        self.db_set('total_charges', total_charges, update_modified=False)
        self.db_set('total_advance_paid', total_advance_paid,
                    update_modified=False)
        self.db_set('balance', total_advance_paid -
                    total_charges, update_modified=False)

    def get_print_doc(self):
        return get_folio_invoice_summary(self.name)


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
    je.remark = f"Ref. folio# {args.folio}. Transfer of funds for {args.customer}."

    against_voucher, against_voucher_type = None, None

    if args.get('transfer_type') == "Transfer to Room":
        debit_account = args.desk_account
        credit_account = args.folio_account
    else:
        credit_account = args.desk_account
        debit_account = args.folio_account

    against_voucher = args.folio
    against_voucher_type = 'Room Folio HMS'

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
        'credit_in_account_currency': 0,
        'reference_name': against_voucher,
        'reference_type': against_voucher_type
    })

    je.insert(ignore_permissions=True)
    je.submit()
    frappe.get_doc("Room Folio HMS", args.folio).update_charges_and_amounts()


@frappe.whitelist()
def get_folio_balance(party, company=None, folio=None):
    from erpnext.accounts.utils import get_balance_on
    default_desk_account = frappe.defaults.get_user_default(
        'default_desk_receivable_account')
    default_folio_account = frappe.defaults.get_user_default(
        'default_folio_receivable_account')

    company = company or erpnext.get_default_company()
    folio_balance, balance = None, dict()

    if folio:
        for d in frappe.db.sql("""
select sum(debit - credit) balance
        from `tabGL Entry`
        where company = %(company)s
        and against_voucher_type = 'Room Folio HMS'
        and account = %(account)s
        and party =%(party)s
        and against_voucher = %(voucher)s""",
                               dict(account=default_folio_account,
                                    company=company, voucher=folio, party=party)):
            folio_balance = d[0]

    balance["folio"] = {
        'account': default_folio_account,
        'balance': flt(folio_balance)
    }
    balance["desk"] = {
        'account': default_desk_account,
        'balance': get_balance_on(account=default_desk_account, date=today(),
                                  party_type="Customer", party=party,
                                  ignore_account_permission=True,
                                  company=company),
    }
    print(balance, "balance")
    return balance


@frappe.whitelist()
def get_nonreconciled_payment_entries(**args):
    '''Only JVs against this room folio.
    Does not consider Payment Entries, other party advances without reference of this room_folio '''

    dr_or_cr = "credit_in_account_currency"
    journal_entries = frappe.db.sql("""
        select
            "Journal Entry" as reference_type, t1.name as reference_name,
            t1.posting_date, t1.remark as remarks, t2.name as reference_row,
            {dr_or_cr} as amount, t2.is_advance
        from
            `tabJournal Entry` t1, `tabJournal Entry Account` t2
        where
            t1.name = t2.parent and t1.docstatus = 1 and t2.docstatus = 1
            and t2.party_type = %(party_type)s and t2.party = %(party)s
            and t2.account = %(account)s and {dr_or_cr} > 0
            and t2.reference_type = 'Room Folio HMS' and t2.reference_name = %(room_folio)s
        order by t1.posting_date
    """.format(**{
        "dr_or_cr": dr_or_cr,
    }), args, as_dict=1,)
    return list(journal_entries)


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


def on_submit_sales_invoice(doc, method=None):
    if doc.room_folio_cf:
        frappe.get_doc("Room Folio HMS",
                       doc.room_folio_cf).update_charges_and_amounts()


@frappe.whitelist()
def update_room_folio_status(name, status):
    frappe.db.set_value("Room Folio HMS", name, "status",
                        status,  update_modified=True)


@frappe.whitelist()
def get_folio_invoice_summary(docname):
    doc = frappe.get_doc("Room Folio HMS", docname).as_dict()

    print_args = dict()

    print_args["company_description"] = frappe.db.get_value(
        "Company", doc['company'], "company_description")

    folios = frappe.db.sql("""
select f.name folio, r.room_no, f.check_in, f.check_out, f.balance, f.customer, case when f.master_folio is null then 1 else 0 end is_master
from `tabRoom Folio HMS` f
inner join `tabRoom HMS` r on r.name = f.room_no
where f.name = %(name)s or f.master_folio = %(name)s
    """, {"name": docname}, as_dict=True)

    print_args["folios"] = folios

    filters = dict(room_folio=doc["name"],
                   company=doc["company"],
                   party_type="Customer",
                   party=doc["customer"],
                   account=frappe.defaults.get_user_default(
        'default_folio_receivable_account')
    )

    items = frappe.db.sql("""
    with data as
    (
        select
    si.room_date_cf date, rm.room_no, sit.item_code voucher, si.base_rounded_total charges,
    0 credits, 0 balance, rm.name room_name, si.creation
            from
                `tabSales Invoice` si
                inner join `tabSales Invoice Item` sit on sit.parent = si.name
                inner join `tabRoom Folio HMS` fo on fo.name = si.room_folio_cf
                inner join `tabRoom HMS` rm on rm.name = fo.room_no
            where
                si.room_folio_cf = %(room_folio)s
    union all
    select t1.posting_date `date`,
    rm.room_no, t1.remark as voucher,
    0 charges, credit_in_account_currency - debit_in_account_currency as credits,
    0 balance,  rm.name room_name,
    t1.creation
            from
                `tabJournal Entry` t1, `tabJournal Entry Account` t2,
                `tabRoom Folio HMS` fo, `tabRoom HMS` rm
            where
                t1.name = t2.parent and t1.docstatus = 1 and t2.docstatus = 1
                and t2.party_type = 'Customer' and t2.party = %(party)s
                and t2.account = %(account)s
                and t2.reference_type = 'Room Folio HMS' and t2.reference_name = %(room_folio)s
                and fo.name = t2.reference_name
                and rm.name = fo.room_no
    order by creation
    )
select date, room_no, voucher, charges, credits, sum(credits-charges) over (order by creation) balance from data
""", filters, as_dict=True)

    print_args["items"] = items

    return print_args

    # html = frappe.render_template("templates/folio_invoice_summary.html", doc)
    # return html
