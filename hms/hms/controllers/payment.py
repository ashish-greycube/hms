# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe.utils import flt, today
from frappe import msgprint, _
from frappe.model.document import Document
from erpnext.accounts.utils import (
    get_outstanding_invoices,
    update_reference_in_payment_entry,
    reconcile_against_document,
)
from erpnext.controllers.accounts_controller import get_advance_payment_entries
import json


@frappe.whitelist()
def get_unreconciled_entries(**args):
    self = frappe._dict(args)
    dr_or_cr = "credit_in_account_currency"
    limit_cond = ""

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
            and (t2.reference_type is null or t2.reference_type = '' or
                (t2.reference_type in ('Sales Order', 'Purchase Order', 'Room Folio HMS')
                    and t2.reference_name is not null and t2.reference_name != ''))
        order by t1.posting_date {limit_cond}
        """.format(
            **{"dr_or_cr": dr_or_cr, "limit_cond": limit_cond}
        ),
        {
            "party_type": self.party_type,
            "party": self.party,
            "account": self.receivable_payable_account,
        },
        as_dict=1,
    )

    return list(journal_entries)


@frappe.whitelist()
def reconcile(doc):
    """
    Overrides the default erpnext payment_reconciliation reconcile.
    erpnext.accounts.utils.check_if_advance_entry_modified will not check jv with with reference_type Room Folio HMS
    so run check_if_advance_entry_modified for jv's with reference_type Room Folio HMS,
    then call original payment_reconciliation.reconcile
    Only change is adding Room Folio HMS in ln 84
    """

    from erpnext.accounts import utils

    @monkeypatch_method(utils)
    def check_if_advance_entry_modified(args):
        """
        check if there is already a voucher reference
        check if amount is same
        check if jv is submitted
        """
        if not args.get("unreconciled_amount"):
            args.update({"unreconciled_amount": args.get("unadjusted_amount")})

        ret = None
        if args.voucher_type == "Journal Entry":
            ret = frappe.db.sql(
                """
                select t2.{dr_or_cr} from `tabJournal Entry` t1, `tabJournal Entry Account` t2
                where t1.name = t2.parent and t2.account = %(account)s
                and t2.party_type = %(party_type)s and t2.party = %(party)s
                and (t2.reference_type is null or t2.reference_type in ("", "Sales Order", "Purchase Order", "Room Folio HMS"))
                and t1.name = %(voucher_no)s and t2.name = %(voucher_detail_no)s
                and t1.docstatus=1 """.format(
                    dr_or_cr=args.get("dr_or_cr")
                ),
                args,
            )
        else:
            party_account_field = (
                "paid_from"
                if erpnext.get_party_account_type(args.party_type) == "Receivable"
                else "paid_to"
            )

            if args.voucher_detail_no:
                ret = frappe.db.sql(
                    """select t1.name
                    from `tabPayment Entry` t1, `tabPayment Entry Reference` t2
                    where
                        t1.name = t2.parent and t1.docstatus = 1
                        and t1.name = %(voucher_no)s and t2.name = %(voucher_detail_no)s
                        and t1.party_type = %(party_type)s and t1.party = %(party)s and t1.{0} = %(account)s
                        and t2.reference_doctype in ("", "Sales Order", "Purchase Order")
                        and t2.allocated_amount = %(unreconciled_amount)s
                """.format(
                        party_account_field
                    ),
                    args,
                )
            else:
                ret = frappe.db.sql(
                    """select name from `tabPayment Entry`
                    where
                        name = %(voucher_no)s and docstatus = 1
                        and party_type = %(party_type)s and party = %(party)s and {0} = %(account)s
                        and unallocated_amount = %(unreconciled_amount)s
                """.format(
                        party_account_field
                    ),
                    args,
                )

        if not ret:
            throw(
                _(
                    """Payment Entry has been modified after you pulled it. Please pull it again."""
                )
            )

    doc = frappe.get_doc(json.loads(doc))
    doc.reconcile()
    frappe.response["message"] = "Reconciled successfully."
    frappe.response.docs.append(doc)


def monkeypatch_method(cls):
    """https://mail.python.org/pipermail/python-dev/2008-January/076194.html

    Usage:

    from erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation import PaymentReconciliation
    @monkeypatch_method(PaymentReconciliation)
    def reconcile(self, args):
        frappe.throw("I'm patched")


    doc = frappe.get_doc('Payment Reconciliation')
    doc.reconcile()

    """

    def decorator(func):
        setattr(cls, func.__name__, func)
        return func

    return decorator
