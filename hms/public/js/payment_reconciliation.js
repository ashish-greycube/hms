var get_unreconciled_entries = function () {
  var me = this;
  let frm = me.frm;
  this._get_unreconciled_entries().then((r) => {
    frappe.call({
      method: "hms.hms.controllers.payment.get_unreconciled_entries",
      freeze: true,
      args: {
        party: frm.doc.party,
        party_type: "Customer",
        receivable_payable_account: frm.doc.receivable_payable_account,
      },
      callback: function (r) {
        for (const p of r.message) {
          let payment = me.frm.add_child("payments");
          $.extend(payment, p);
        }
        me.frm.refresh_field("payments");
      },
    });
  });
};

var reconcile_payment_entries = function () {
  let me = this;
  return frappe.call({
    method: "hms.hms.controllers.payment.reconcile",
    freeze: true,
    args: {
      doc: me.frm.doc,
    },
    callback: function (r) {
      me.set_invoice_options();
      me.toggle_primary_action();
    },
  });
};

// Make this in to a Custom Script - version 12 does not pick up js file but executes Custom Script.
/*

frappe.ui.form.on("Payment Reconciliation", {
  onload: function (frm) {
    let me = frm.cscript;
    me._get_unreconciled_entries = me.get_unreconciled_entries;
    me._reconcile_payment_entries = me.reconcile_payment_entries;

    frappe.require(["assets/hms/js/payment_reconciliation.js"], function () {
      me.get_unreconciled_entries = get_unreconciled_entries;
      me.reconcile_payment_entries = reconcile_payment_entries;
    });
  },

  refresh: function (frm) {
    frm.doc.company = "Sun Hotel";
    frm.doc.party_type = "Customer";
    frm.doc.party = "Tata Airlines";
    frm.doc.receivable_payable_account = "Room Folio Debtors - SH";
    frm.refresh_fields();
  },
});

 */
