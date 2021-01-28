# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    nowdate,
    flt,
    cint,
    today,
    date_diff,
    add_days,
    getdate,
    cstr,
    now,
    get_link_to_form,
)
from erpnext.accounts.party import get_party_account, get_party_bank_account
from frappe.contacts.doctype.contact.contact import (
    get_contact_details,
    get_default_contact,
)
from erpnext.accounts.utils import get_outstanding_invoices
import json
from hms.hms.doctype.room_status_ledger_entry_hms.room_status_ledger_entry_hms import (
    update_room_status_ledger,
)
from hms.hms.controllers.reservation import get_room_service_item
from erpnext.accounts.doctype.journal_entry.journal_entry import (
    get_default_bank_cash_account,
)
import erpnext
from six import iteritems, string_types
from frappe.utils.formatters import format_value
from erpnext.setup.doctype.item_group.item_group import get_child_item_groups
from hms.hms.report.night_audit.night_audit import validate_system_date


folio_checklist = {
    "guest_id": _("Please attach Identification for guest"),
    "advance_amount": _("Please make an advance payment for the folio."),
    "sign_in_sheet": _("Please create Sign In Sheet for guest."),
    "sign_in_sheet_incomplete": _("Please get Signature in Sign In Sheet."),
}


class RoomFolioHMS(Document):
    def before_insert(self):
        if getdate(self.check_in) == getdate():
            validate_system_date(getdate(), raise_exception=0)

    def validate(self):
        # check night audit completed for previous date
        # if self.is_new() and date_diff(getdate(), getdate(self.check_in)) > 0:
        # frappe.throw(_("Check In date cannot be earlier than today."))

        if self.is_new() and self.status == "Checked In":
            self.validate_room_reservation()
            self.validate_room_status()

        self.set_missing_values()
        self.validate_checklist()
        self.validate_duplicate_checkin()
        self.update_charges_and_amounts()

    def set_missing_values(self):
        contact_person = get_default_contact("Customer", self.customer)
        if contact_person:
            details = get_contact_details(contact_person)
            self.customer_email = details.get("contact_email")
            self.customer_mobile = details.get("contact_mobile") or details.get("phone")

    def validate_duplicate_checkin(self):
        for d in frappe.db.sql(
            """select name from `tabRoom Folio HMS`
        where reservation = %s and name <> %s limit 1""",
            (self.reservation, self.name),
        ):
            rf_link = get_link_to_form("Room Folio HMS", d[0])
            so_link = get_link_to_form("Sales Order", self.reservation)
            frappe.throw(
                _("Room Folio {} already created for reservation {}.").format(
                    rf_link, so_link
                )
            )
        for d in frappe.db.sql(
            """
select name
        from `tabRoom Folio HMS`
        where name <> %s
        and room_no = %s
        and status <> 'Checked Out'
        and not (check_in >= %s or check_out <= %s)
        limit 1""",
            (self.name, self.room_no, self.check_out, self.check_in),
        ):
            frappe.throw(
                _("Room Folio dates overlap with existing room folio {}.").format(
                    get_link_to_form("Room Folio HMS", d[0])
                )
            )

    def make_sign_in_sheet(self):
        from hms.hms.doctype.sign_in_sheet_hms.sign_in_sheet_hms import (
            make_sign_in_sheet,
        )

        return make_sign_in_sheet(self.name)

    def validate_room_reservation(self):
        """WHERE NOT (From_date > @RangeTill OR To_date < @RangeFrom)"""
        for d in frappe.db.sql(
            """
select name reservation, room_no_cf, check_in_cf, check_out_cf
        from `tabSales Order`
        where docstatus = 1 and room_no_cf = %s and name <> %s
        and not (check_in_cf >= %s or check_out_cf <= %s)
        """,
            (self.room_no, self.reservation, self.check_out, self.check_in),
            as_dict=True,
        ):
            frappe.throw(
                f"Reservation {d.reservation} exists for room {d.room_no} between {d.check_in_cf} and {d.check_out_cf} "
            )

    def validate_room_status(self):
        for d in frappe.db.sql(
            """
select status, reference_type, reference_name
        from `tabRoom Status Ledger Entry HMS`
        where room_no = %s and docstatus <> 2""",
            (self.room_no),
            as_dict=True,
        ):
            frappe.throw(f"Room {self.room_no} is {d.status} for {self.check_in} ")

    def validate_checklist(self):
        """
        1. Guest ID
        2. advance paid
        3. Sign In Sheet signed"""
        if cint(self.is_checklist_done):
            return ""

        checklist = []
        valid = frappe.db.sql(
            """
            select
            if(f.total_advance_paid > 0 or coalesce(cu.allow_checkin_without_advance_cf,0)=1,1,0) advance_amount,
            if(con.name is not null,1,0) guest_id,
            if(sg.name is not null,1,0) sign_in_sheet,
            if(sg.signature is not null, 1, 0) sign_in_sheet_incomplete
            from `tabRoom Folio HMS` f
            inner join tabCustomer cu on cu.name = f.customer
            inner join `tabSales Order` so on so.name = f.reservation
            left outer join tabContact con on con.name = so.guest_cf and con.image is not null
            left outer join `tabSign In Sheet HMS` sg on sg.name = f.sign_in_sheet
            where f.name = %s limit 1""",
            (self.name,),
            as_dict=True,
        )
        valid = (
            valid
            and valid[0]
            or {
                "advance_amount": 0,
                "guest_id": 0,
                "sign_in_sheet": 0,
                "sign_in_sheet_incomplete": 0,
            }
        )

        if not valid:
            checklist = "<br>".join(folio_checklist.values())
        else:
            checklist = [
                folio_checklist.get(k) for k, v in valid.items() if not cint(v)
            ]

        if folio_checklist.get("sign_in_sheet") in checklist:
            checklist = [
                d
                for d in checklist
                if not d == folio_checklist.get("sign_in_sheet_incomplete")
            ]

        if not checklist:
            self.db_set("is_checklist_done", 1)
        else:
            return "<br>".join(checklist)

    def make_check_in(self):
        "check in"
        if not self.docstatus == 1:
            frappe.throw("Please submit Folio before Check In.")

        if getdate(self.check_in) == getdate():
            validate_system_date(getdate(), raise_exception=0)

        self.db_set("status", "Checked In", update_modified=True)
        update_room_status_ledger(self.as_dict(), action="check_in")

    def after_insert(self):
        self.create_charge_purchase(self.check_in)

    def on_cancel(self):
        "cancel"
        update_room_status_ledger(self.as_dict(), action="cancel")

    def create_charge_purchase(self, room_date):
        """create sales invoice for room_date date"""
        # if frappe.db.exists("Sales Invoice", {'room_folio_cf': self.name, 'room_date_cf': room_date, 'docstatus': 1}):
        #     frappe.throw(
        #         _("Sales Invoice already created for %s") % (room_date,))
        #     return

        from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

        out = make_sales_invoice(source_name=self.reservation)
        out.room_folio_cf = self.name
        out.due_date = max(getdate(self.check_out), getdate(now()))
        out.room_date_cf = room_date
        out.debit_to = frappe.defaults.get_user_default(
            "default_folio_receivable_account"
        )
        out.ignore_pricing_rule = 1
        items = self.get_invoice_items(room_date, out)
        out.items = []
        for d in items:
            out.append(
                "items",
                {
                    "qty": d.qty,
                    "sales_order": d.sales_order,
                    "so_detail": d.so_detail,
                    # set item as Room Folio room_package
                    "item_code": self.room_package,
                    # set rate as per rate in Room Folio
                    "rate": self.room_rate,
                },
            )
        out.save()
        out.submit()
        return out.name

    def get_invoice_items(self, room_date, out):
        # remove lines for other dates in Sales Invoice, only bill for room_date
        so_items = frappe.db.get_all(
            "Sales Order Item",
            filters={
                "parent": self.reservation,
                "reservation_date_cf": room_date,
            },
            fields=["name", "qty"],
        )
        # qty will be less than 1 in cases where room rate was changed in Sales Invoice from Sales Order
        # filters dates that have already been invoiced
        items = [
            d
            for d in out.items
            if so_items and d.so_detail == so_items[0]["name"] and not d.qty < 1
        ]
        if not items:
            frappe.throw("No billable room charges for %s." % room_date)
        return items

    def make_check_out(self):
        self.update_charges_and_amounts()
        self.validate_room_folio_balance()
        self.db_set("status", "Checked Out", update_modified=True)
        if getdate(self.check_out) > getdate(now()):
            self.db_set("check_out", frappe.utils.now_datetime(), update_modified=True)
        update_room_status_ledger(self.as_dict(), action="check_out")
        return self.as_dict()

    def validate_room_folio_balance(self):
        if not self.guest_purchase_balance == 0:
            frappe.throw(
                _(
                    "Unsettled Guest Purchases in folio. Please settle outstanding amount {} before checkout."
                ).format(format_value(self.guest_purchase_balance, df="Currency"))
            )
        if not self.balance == 0:
            frappe.throw(
                _(
                    "Unsettled balance {} exists in folio. Please settle balance before checkout."
                ).format(format_value(self.balance, df="Currency"))
            )

    def make_folio_advance_entry(self):
        args = json.loads(frappe.local.form_dict["args"] or "{}")
        mode_of_payment = args.get("mode_of_payment")
        amount = flt(args.get("paid_amount", 0))
        je = frappe.new_doc("Journal Entry")
        je.posting_date = nowdate()
        je.mode_of_payment = mode_of_payment
        je.voucher_type = "Journal Entry"
        je.company = self.company
        if not mode_of_payment == "Cash":
            je.cheque_no = args.get("reference_no")
            je.cheque_date = args.get("reference_date")

        cash_bank_account = get_default_bank_cash_account(
            self.company, mode_of_payment=mode_of_payment
        )

        folio_account = frappe.defaults.get_user_default(
            "default_folio_receivable_account"
        )

        if args.get("payment_type") == "Receive":
            je.remark = f"Room Folio advance ({mode_of_payment}) against: {self.name}"
            je.append(
                "accounts",
                {
                    "account": folio_account,
                    "party_type": "Customer",
                    "party": self.customer,
                    "reference_type": self.doctype,
                    "reference_name": self.name,
                    "is_advance": "Yes",
                    "credit_in_account_currency": amount,
                },
            )

            je.append(
                "accounts",
                {
                    "account": cash_bank_account.account,
                    "account_currency": cash_bank_account.account_currency,
                    "account_type": cash_bank_account.account_type,
                    "debit_in_account_currency": amount,
                },
            )
        else:
            je.remark = "Room Folio refund against: " + self.name
            je.append(
                "accounts",
                {
                    "account": cash_bank_account.account,
                    "account_currency": cash_bank_account.account_currency,
                    "account_type": cash_bank_account.account_type,
                    "credit_in_account_currency": amount,
                },
            )

            je.append(
                "accounts",
                {
                    "account": folio_account,
                    "party_type": "Customer",
                    "party": self.customer,
                    "debit_in_account_currency": amount,
                    "reference_type": self.doctype,
                    "reference_name": self.name,
                },
            )

        je.insert(ignore_permissions=True)
        je.submit()
        self.update_charges_and_amounts()
        frappe.msgprint(_("Payment created."), alert=True)

    def update_charges_and_amounts(self):
        total_charges, total_advance_paid = 0, 0
        # set totals from charge purchase and advances
        for d in frappe.db.sql(
            """
select sum(si.rounded_total)
        from `tabSales Invoice` si
        where NULLIF(si.room_folio_cf, '') = %s""",
            (self.name),
        ):
            total_charges = d[0]

        default_folio_receivable_account = frappe.defaults.get_user_default(
            "default_folio_receivable_account"
        )

        for d in frappe.db.sql(
            """
            select 0-sum(debit-credit) total_advance
            from `tabGL Entry`
            where account = %(receivable_account)s
            and party = %(customer)s
            and against_voucher_type = 'Room Folio HMS'
            and against_voucher = %(folio)s
        """,
            dict(
                folio=self.name,
                customer=self.customer,
                receivable_account=default_folio_receivable_account,
            ),
        ):
            total_advance_paid += flt(d[0])

        total_charges = total_charges or 0
        total_advance_paid = total_advance_paid or 0

        self.db_set("total_charges", total_charges, update_modified=False)
        self.db_set("total_advance_paid", total_advance_paid, update_modified=False)
        self.db_set(
            "balance", total_advance_paid - total_charges, update_modified=False
        )

        guest_purchase_balance = frappe.db.sql(
            """
        select sum(si.outstanding_amount)
        from `tabSales Invoice` si
        inner join `tabRoom Folio HMS` rf on rf.name = si.room_folio_cf and rf.customer <> si.customer
        where si.docstatus = 1 and si.is_pos = 1 and si.room_folio_cf = %s""",
            (self.name,),
        )
        if guest_purchase_balance:
            self.db_set(
                "guest_purchase_balance",
                guest_purchase_balance[0][0] or 0,
                update_modified=False,
            )

    def get_print_doc(self):
        return get_folio_invoice_summary(self.name)


@frappe.whitelist()
def get_charge_and_purchase(docname):
    return frappe.db.sql(
        """
    select si.name, rf.name room_folio, rf.room_no, 
    date_format(coalesce(room_date_cf, posting_date),'%%d %%b, %%y') room_date_cf,
    date_format(posting_time,'%%H:%%i') posting_time, rounded_total, outstanding_amount,
    sit.items charges_for
    from `tabRoom Folio HMS` rf
    inner join `tabSales Invoice` si on si.docstatus = 1 and rf.name = ifnull(si.room_folio_cf, '')
    inner join (
        select parent, group_concat(distinct item_name) items
        from `tabSales Invoice Item`
        group by parent
    ) sit on sit.parent = si.name
    where rf.name = %(folio)s or rf.master_folio = %(folio)s""",
        dict(
            folio=docname,
        ),
        as_dict=True,
    )


@frappe.whitelist()
def make_transfer_jv(**args):
    args = frappe._dict(args)
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = erpnext.get_default_company()
    je.posting_date = today()
    je.remark = f"Ref. folio# {args.folio}. Transfer of funds for {args.customer}."

    against_voucher, against_voucher_type = None, None

    if args.get("transfer_type") == "Transfer to Room":
        debit_account = args.desk_account
        credit_account = args.folio_account
    else:
        credit_account = args.desk_account
        debit_account = args.folio_account

    against_voucher = args.folio
    against_voucher_type = "Room Folio HMS"

    je.append(
        "accounts",
        {
            "account": credit_account,
            "party_type": "Customer",
            "party": args.customer,
            "debit_in_account_currency": 0,
            "credit_in_account_currency": flt(args.amount_to_transfer),
            "is_advance": "Yes",
            "reference_name": against_voucher,
            "reference_type": against_voucher_type,
        },
    )

    je.append(
        "accounts",
        {
            "account": debit_account,
            "party_type": "Customer",
            "party": args.customer,
            "debit_in_account_currency": flt(args.amount_to_transfer),
            "credit_in_account_currency": 0,
            "reference_name": against_voucher,
            "reference_type": against_voucher_type,
        },
    )

    je.insert(ignore_permissions=True)
    je.submit()
    frappe.get_doc("Room Folio HMS", args.folio).update_charges_and_amounts()


@frappe.whitelist()
def get_folio_balance(party, company=None, folio=None):
    from erpnext.accounts.utils import get_balance_on

    default_desk_account = frappe.defaults.get_user_default(
        "default_desk_receivable_account"
    )
    default_folio_account = frappe.defaults.get_user_default(
        "default_folio_receivable_account"
    )

    company = company or erpnext.get_default_company()
    folio_balance, balance = None, dict()

    if folio:
        for d in frappe.db.sql(
            """
select sum(debit - credit) balance
        from `tabGL Entry`
        where company = %(company)s
        and against_voucher_type = 'Room Folio HMS'
        and account = %(account)s
        and party =%(party)s
        and against_voucher = %(voucher)s""",
            dict(
                account=default_folio_account,
                company=company,
                voucher=folio,
                party=party,
            ),
        ):
            folio_balance = d[0]

    balance["folio"] = {"account": default_folio_account, "balance": flt(folio_balance)}
    balance["desk"] = {
        "account": default_desk_account,
        "balance": get_balance_on(
            account=default_desk_account,
            date=today(),
            party_type="Customer",
            party=party,
            ignore_account_permission=True,
            company=company,
        ),
    }
    return balance


@frappe.whitelist()
def get_nonreconciled_payment_entries(**args):
    """Only JVs against this room folio.
    Does not consider Payment Entries, other party advances without reference of this room_folio"""

    dr_or_cr = "credit_in_account_currency"
    journal_entries = frappe.db.sql(
        """
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
    """.format(
            **{
                "dr_or_cr": dr_or_cr,
            }
        ),
        args,
        as_dict=1,
    )
    return list(journal_entries)


def update_checklist_status(sign_in_sheet=None):
    if sign_in_sheet:
        for d in frappe.db.sql(
            """select name
        from `tabRoom Folio HMS` where sign_in_sheet = %s""",
            (sign_in_sheet),
        ):
            frappe.get_doc("Room Folio HMS", d[0]).validate_checklist()


def on_submit_sales_invoice(doc, method=None):
    if doc.room_folio_cf:
        frappe.get_doc("Room Folio HMS", doc.room_folio_cf).update_charges_and_amounts()


def on_validate_sales_invoice(doc, method=None):
    if doc.room_folio_cf and doc.is_pos:
        if doc.paid_amount > 0:
            frappe.throw("Cannot recieve payment when charging to folio.")
        doc.debit_to = frappe.defaults.get_user_default(
            "default_folio_receivable_account"
        )

        def _make_split_invoice(doc, customer, items):
            """split POS Invoice based on item-group set in reservation split bill."""
            si = frappe.new_doc("Sales Invoice")
            si.flags.is_split_bill = True
            si.room_folio_cf = doc.room_folio_cf
            si.posting_date = doc.posting_date or nowdate()
            si.company = doc.company
            si.customer = customer
            si.debit_to = doc.debit_to
            si.update_stock = doc.update_stock
            si.is_pos = doc.is_pos
            si.currency = doc.currency
            si.conversion_rate = doc.conversion_rate
            for d in doc.payments:
                si.append(
                    "payments",
                    {
                        "mode_of_payment": d.mode_of_payment,
                        "account": d.account,
                        "type": d.type,
                    },
                )
            for item in items:
                si.append(
                    "items",
                    {
                        "item_code": item.item_code,
                        "warehouse": item.warehouse,
                        "qty": item.qty,
                        "rate": item.rate,
                        "income_account": item.income_account,
                        "expense_account": item.expense_account,
                        "cost_center": item.cost_center,
                    },
                )
            si.calculate_taxes_and_totals()
            si.insert()
            si.submit()
            frappe.msgprint("Split Invoice %s created." % si.name, alert=True)

    if cint(doc.is_pos) and doc.room_folio_cf and not doc.flags.is_split_bill:
        customer_item_groups = frappe.db.sql(
            """
        select  a.customer, group_concat(a.item_group)
        from `tabRoom Folio Split Bill Detail HMS` a
        inner join `tabRoom Folio HMS` b on b.name = a.parent
        and b.name = %s and a.customer <> %s
        group by a.customer""",
            (doc.room_folio_cf, doc.customer),
            as_dict=False,
        )
        if customer_item_groups:
            split_invoices = []
            for customer, item_groups in customer_item_groups:
                _groups = item_groups.split(",")
                for g in item_groups.split(","):
                    _groups += get_child_item_groups(g)
                items = [i for i in doc.items if i.item_group in _groups]
                if items:
                    split_invoices.append((customer, items))
                    doc.items = [i for i in doc.items if not i.item_group in _groups]

            if not doc.items:
                doc.customer = split_invoices[0][0]
                doc.update(
                    {
                        "title": None,
                        "customer_name": None,
                        "contact_person": None,
                        "contact_display": None,
                        "contact_mobile": None,
                        "contact_email": None,
                    }
                )
                doc.set_missing_values()
                doc.items = split_invoices[0][1]
                split_invoices = split_invoices[1:]

            doc.calculate_taxes_and_totals()
            for d in split_invoices:
                _make_split_invoice(doc, d[0], d[1])


@frappe.whitelist()
def update_room_folio_status(name, status):
    frappe.db.set_value("Room Folio HMS", name, "status", status, update_modified=True)


@frappe.whitelist()
def get_guest_purchase(room_folio):
    return frappe.db.sql(
        """
        select si.name invoice, concat(si.posting_date, ' ', left(si.posting_time,5)) posting_date,
        si.base_rounded_total, si.remarks, si.customer_name, si.status, group_concat(distinct sit.item_group) items
        from `tabSales Invoice` si
        inner join `tabRoom Folio HMS` rf on rf.name = si.room_folio_cf and rf.customer <> si.customer
        inner join `tabSales Invoice Item` sit on sit.parent = si.name
        where si.docstatus = 1 and si.is_pos = 1 and si.room_folio_cf = %s
        group by si.name, si.posting_date, si.posting_time, si.base_rounded_total,
        si.remarks, si.customer_name, si.status
        """,
        (room_folio),
        as_dict=True,
    )


@frappe.whitelist()
def get_folio_invoice_summary(docname):
    doc = frappe.get_doc("Room Folio HMS", docname).as_dict()

    print_args = dict()

    print_args["company_description"] = frappe.db.get_value(
        "Company", doc["company"], "company_description"
    )

    print_args["currency"] = frappe.get_cached_value(
        "Company", doc["company"], "default_currency"
    )

    folios = frappe.db.sql(
        """
select f.name folio, r.room_no, f.check_in, f.check_out, f.balance, f.customer, case when f.master_folio is null then 1 else 0 end is_master
from `tabRoom Folio HMS` f
inner join `tabRoom HMS` r on r.name = f.room_no
where f.name = %(name)s or f.master_folio = %(name)s
    """,
        {"name": docname},
        as_dict=True,
    )

    print_args["folios"] = folios

    filters = dict(
        room_folio=doc["name"],
        company=doc["company"],
        party_type="Customer",
        party=doc["customer"],
        account=frappe.defaults.get_user_default("default_folio_receivable_account"),
    )

    items = frappe.db.sql(
        """
    with data as
    (
        select si.name invoice,
    coalesce(si.room_date_cf, si.posting_date) date, rm.room_no, sit.voucher, si.base_rounded_total charges,
    0 credits, 0 balance, rm.name room_name, si.creation
            from
                `tabSales Invoice` si
                inner join (
                        select parent, group_concat(item.item_code) voucher from `tabSales Invoice Item` item
                        group by parent) sit on sit.parent = si.name
                inner join `tabRoom Folio HMS` fo on fo.name = si.room_folio_cf
                inner join `tabRoom HMS` rm on rm.name = fo.room_no
            where
                si.docstatus = 1 and si.room_folio_cf = %(room_folio)s
    union all
    select '' invoice, t1.posting_date `date`,
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
select invoice, date, room_no, voucher, charges, credits, 
sum(credits-charges) over (order by creation) balance from data
""",
        filters,
        as_dict=True,
    )

    print_args["items"] = items

    invoice_html = ""
    for d in items:
        if not d["invoice"]:
            continue
        invoice_html += frappe.get_print(
            "Sales Invoice", d["invoice"], "Standard", no_letterhead=0
        )

    print_args["invoice_html"] = invoice_html or "**" * 10

    return print_args

    # html = frappe.render_template("templates/folio_invoice_summary.html", doc)
    # return html
