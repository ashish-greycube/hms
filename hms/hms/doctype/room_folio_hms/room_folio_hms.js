// Copyright (c) 2020, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Room Folio HMS", {
  //
  //
  after_save: function (frm) {},

  refresh: function (frm) {
    hms.make_grid_room_folio_advance(frm);
    hms.make_grid_charge_and_purchase(frm);
    frm.events.load_charge_and_purchase(frm);
    frm.events.set_advance_payments(frm);
    frm.events.add_custom_buttons(frm);

    if (!frm.is_new() && !cint(frm.doc.is_checklist_done)) {
      frm.events.validate_room_folio_checklist(frm);
    }
    frm.events.set_css(frm);
  },

  set_css: function (frm) {
    let color = frm.doc.balance > 0 ? "mistyrose" : "lightgreen";
    frm.fields_dict["balance"].$input.css("background-color", color);
  },

  add_custom_buttons: function (frm) {
    if (frm.doc.status == "Pre-Check In" && frm.doc.is_checklist_done) {
      frm.page.add_inner_button(
        __("Check In"),
        function () {
          frm.doc.status = "Checked In";
          frm.save();
        },
        __("Actions")
      );
    }

    if (!frm.doc.sign_in_sheet && flt(frm.doc.total_advance_paid) > 0) {
      frm.page.add_inner_button(
        __("Make Sign In Sheet"),
        function () {
          frm.events.make_sign_in_sheet(frm);
        },
        __("Actions")
      );
    }

    frm.page.add_inner_button(
      __("Transfer Funds"),
      function () {
        frm.events.show_transfer_dialog(frm);
      },
      __("Actions")
    );

    frm.page.add_inner_button(
      __("Create Payment"),
      function () {
        frm.events.make_payment_entry(frm);
      },
      __("Actions")
    );

    if (true || frm.doc.status == "Checked In") {
      frm.page.add_inner_button(
        __("Check Out"),
        function () {
          frm.events.make_check_out(frm);
        },
        __("Actions")
      );
    }
    frm.page.set_inner_btn_group_as_primary(__("Actions"));
  },

  set_advance_payments: function (frm) {
    frappe
      .call({
        method:
          "hms.hms.doctype.room_folio_hms.room_folio_hms.get_nonreconciled_payment_entries",
        args: {
          company: frm.doc.company,
          party_type: "Customer",
          party: frm.doc.customer,
          receivable_payable_account: frappe.defaults.get_user_default(
            "default_folio_receivable_account"
          ),
        },
      })
      .then((r) => {
        if (!r.exc) {
          frm.room_folio_advance_gridOptions.api.setRowData(r.message);
        }
      });
  },

  show_transfer_dialog: function (frm) {
    let desk_account = frappe.defaults.get_user_default(
      "default_desk_receivable_account"
    );
    let folio_account = frappe.defaults.get_user_default(
      "default_folio_receivable_account"
    );

    const fields = [
      {
        fieldtype: "Data",
        read_only: 1,
        label: "Customer",
        fieldname: "customer",
        default: frm.doc.customer,
      },
      { fieldtype: "Section Break", label: "Party Balance" },
      {
        fieldtype: "Data",
        fieldname: "desk_account",
        hidden: 1,
        default: desk_account,
      },
      {
        fieldtype: "Data",
        fieldname: "folio_account",
        hidden: 1,
        default: folio_account,
      },
      {
        fieldtype: "Currency",
        read_only: 1,
        label: desk_account,
        fieldname: "desk_account_balance",
      },
      { fieldtype: "Column Break" },
      {
        fieldtype: "Currency",
        read_only: 1,
        label: folio_account,
        fieldname: "folio_account_balance",
      },
      {
        fieldtype: "Data",
        fieldname: "folio",
        hidden: 1,
        default: frm.doc.name,
      },
      { fieldtype: "Section Break", label: "" },
      {
        label: "Transfer Type",
        fieldname: "transfer_type",
        fieldtype: "Select",
        reqd: 1,
        options: ["Transfer to Room", "Transfer to Desk"].join("\n"),
        default: "Transfer to Room",
        onchange: () => {},
      },
      { fieldtype: "Column Break" },
      {
        fieldtype: "Currency",
        fieldname: "amount_to_transfer",
        label: "Amount to Transfer",
        default: "0",
      },
    ];
    var d = new frappe.ui.Dialog({
      title: __("Transfer Funds"),
      fields: fields,
      primary_action: function () {
        let data = d.get_values();

        if (data.amount_to_transfer < 0) {
          frappe.throw("Amount to transfer should be greater than 0.");
          return;
        }

        let is_valid = !(
          data.amount_to_transfer >
          0 -
            (data.transfer_type == "Transfer to Room"
              ? data.desk_account_balance || 0
              : data.folio_account_balance || 0)
        );

        if (!is_valid) {
          frappe.throw("Amount to transfer cannot exceed balanace.");
          return;
        }

        frappe.call({
          method:
            "hms.hms.doctype.room_folio_hms.room_folio_hms.make_transfer_jv",
          args: d.get_values(),
          callback: function (r) {
            if (!r.exc) {
              d.hide();
              frm.reload_doc();
            }
          },
        });
      },
      primary_action_label: __("Submit"),
    });

    get_party_balance(frm.doc.company, frm.doc.customer).then((r) => {
      d.balances = r.message;
      d.set_values({
        desk_account_balance: d.balances.desk.balance,
        folio_account_balance: d.balances.folio.balance,
      });
      d.show();
    });
  },

  make_payment_entry: function (frm) {
    return frappe.call({
      doc: frm.doc,
      method: "get_payment_entry",
      callback: function (r) {
        if (r.message) {
          var doc = frappe.model.sync(r.message)[0];
          frappe.set_route("Form", doc.doctype, doc.name);
        }
      },
    });
  },

  validate_room_folio_checklist: function (frm) {
    return frappe.call({
      doc: frm.doc,
      method: "validate_checklist",
      callback: function (r) {
        if (!r.exc) {
          frm.set_intro(null);
          frm.set_intro(r.message, "yellow");
        }
      },
    });
  },

  make_sign_in_sheet: function (frm) {
    return frappe.call({
      doc: frm.doc,
      method: "make_sign_in_sheet",
      callback: function (r) {
        if (r.message) {
          var new_doc = frappe.model.sync(r.message)[0];
          frm.reload_doc();
          frappe.set_route("Form", new_doc.doctype, new_doc.name);
        }
      },
    });
  },

  make_check_out: function (frm) {
    return frappe.call({
      doc: frm.doc,
      method: "make_check_out",
      callback: function (r) {
        if (r.message) {
          // frappe.model.sync(r.message)[0];
          frm.reload_doc();
        }
      },
    });
  },

  load_charge_and_purchase: function (frm) {
    return frappe.call({
      method:
        "hms.hms.doctype.room_folio_hms.room_folio_hms.get_charge_and_purchase",
      args: { docname: frm.doc.name },
      callback: function (r) {
        if (r.message) {
          frm.gridOptions.api.setRowData(r.message);
        }
      },
    });
  },

  //
});

function get_party_balance(company, party) {
  return frappe.call({
    method: "hms.hms.doctype.room_folio_hms.room_folio_hms.get_party_balance",
    args: {
      company: company,
      party: party,
    },
  });
}
