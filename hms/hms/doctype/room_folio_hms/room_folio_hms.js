// Copyright (c) 2020, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Room Folio HMS", {
  //
  //
  after_save: function (frm) {},

  refresh: function (frm) {
    hms.make_grid_room_folio_advance(frm);
    hms.make_grid_charge_and_purchase(frm);
    hms.make_grid_guest_purchase(frm);
    frm.events.load_charge_and_purchase(frm);
    frm.events.set_guest_purchase(frm);
    frm.events.set_advance_payments(frm);
    frm.events.add_custom_buttons(frm);

    if (!frm.is_new() && !cint(frm.doc.is_checklist_done)) {
      frm.events.validate_room_folio_checklist(frm);
    }
    frm.events.set_css(frm);

    frm.set_query("room_package", () => {
      return {
        filters: {
          room_type_cf: frm.doc.room_type,
        },
      };
    });
  },

  set_css: function (frm) {
    let color = frm.doc.balance < 0 ? "mistyrose" : "lightgreen";
    frm.fields_dict["balance"].$input_wrapper
      .find(".control-value, input")
      .css("background-color", color);
  },

  add_custom_buttons: function (frm) {
    frm.page.add_inner_button(__("Frontdesk"), () => {
      frappe.set_route("ag-report/Frontdesk HMS");
    });

    if (frm.is_new()) {
      return;
    }

    if (frm.doc.status == "Pre-Check In" && frm.doc.is_checklist_done) {
      frm.page.add_inner_button(
        __("Check In"),
        function () {
          frappe.call({
            doc: frm.doc,
            method: "make_check_in",
            callback: function (r) {
              frm.reload_doc();
              frappe.show_alert("Folio checked in.");
            },
          });
        },
        __("Actions")
      );
    }

    if (!frm.doc.sign_in_sheet) {
      frappe.db.get_value(
        "Customer",
        { name: frm.doc.customer },
        "allow_checkin_without_advance_cf",
        (r) => {
          if (
            flt(frm.doc.total_advance_paid) > 0 ||
            r.allow_checkin_without_advance_cf == 1
          ) {
            frm.page.add_inner_button(
              __("Make Sign In Sheet"),
              function () {
                frm.events.make_sign_in_sheet(frm);
              },
              __("Actions")
            );
          }
        }
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
      __("Make Payment"),
      function () {
        frm.events.make_payment_entry(frm);
      },
      __("Actions")
    );

    if (frm.doc.status == "Checked In") {
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

  set_guest_purchase: function (frm) {
    frappe
      .call({
        method:
          "hms.hms.doctype.room_folio_hms.room_folio_hms.get_guest_purchase",
        args: {
          room_folio: frm.doc.name,
        },
      })
      .then((r) => {
        if (!r.exc) {
          frm.gridOptions_guest_purchase.api.setRowData(r.message);
          let guest_balance = r.message.reduce(
            (acc, i) => acc + (i.status == "Paid" ? 0 : i.base_rounded_total),
            0
          );
          frm.doc.guest_purchase_balance = guest_balance || 0;
          frm.refresh_field("guest_purchase_balance");
        }
      });
  },

  set_advance_payments: function (frm) {
    frappe
      .call({
        method:
          "hms.hms.doctype.room_folio_hms.room_folio_hms.get_nonreconciled_payment_entries",
        args: {
          room_folio: frm.doc.name,
          company: frm.doc.company,
          party_type: "Customer",
          party: frm.doc.customer,
          account: frappe.defaults.get_user_default(
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

    let balance = frm.doc.balance;

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
        formatter: cr_df_formatter,
      },
      { fieldtype: "Column Break" },
      {
        fieldtype: "Currency",
        read_only: 1,
        label: folio_account,
        fieldname: "folio_account_balance",
        formatter: cr_df_formatter,
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
        default: balance > 0 ? "Transfer to Desk" : "Transfer to Room",
        onchange: () => {},
      },
      { fieldtype: "Column Break" },
      {
        fieldtype: "Currency",
        fieldname: "amount_to_transfer",
        label: "Amount to Transfer",
        default: Math.abs(balance),
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

    get_folio_balance(frm.doc.name, frm.doc.company, frm.doc.customer).then(
      (r) => {
        d.balances = r.message;
        d.set_values({
          desk_account_balance: d.balances.desk.balance,
          folio_account_balance: d.balances.folio.balance,
        });

        d.show();
      }
    );
  },

  make_payment_entry: function (frm) {
    const fields = [
      {
        label: "Payment Type",
        fieldtype: "Select",
        fieldname: "payment_type",
        options: "Receive\nRefund",
        default: "Receive",
        reqd: 1,
      },
      { fieldtype: "Column Break" },
      { fieldtype: "Section Break", label: "Amount" },
      {
        label: "Mode of Payment",
        fieldtype: "Link",
        fieldname: "mode_of_payment",
        options: "Mode of Payment",
        default: "Cash",
        reqd: 1,
      },
      {
        label: "Cheque/Reference No",
        fieldtype: "Data",
        fieldname: "reference_no",
      },
      { fieldtype: "Column Break" },
      {
        label: "Paid Amount",
        fieldtype: "Currency",
        fieldname: "paid_amount",
        default: frm.doc.balance < 0 ? 0 - frm.doc.balance : 0,
        reqd: 1,
      },
      {
        label: "Cheque/Reference Date",
        fieldtype: "Date",
        fieldname: "reference_date",
        default: frappe.datetime.get_today(),
      },
    ];
    var dlg = new frappe.ui.Dialog({
      title: __("Folio Payment"),
      fields: fields,
      primary_action: function () {
        let data = dlg.get_values();

        if (data.paid_amount < 0) {
          frappe.throw(`Amount cannot be less than 0.`);
        }
        if (data.mode_of_payment != "Cash") {
          if (!data.reference_no || !data.reference_date) {
            frappe.throw(
              `Reference number, date required for ${data.mode_of_payment} payment.`
            );
            return;
          }
        }

        return frappe.call({
          doc: frm.doc,
          args: data,
          method: "make_folio_advance_entry",
          callback: function (r) {
            if (!r.exc) {
              dlg.hide();
              frm.reload_doc();
            }
          },
        });
      },
    });
    dlg.show();

    // return frappe.call({
    //   doc: frm.doc,
    //   method: "get_payment_entry",
    //   callback: function (r) {
    //     if (r.message) {
    //       var doc = frappe.model.sync(r.message)[0];
    //       frappe.set_route("Form", doc.doctype, doc.name);
    //     }
    //   },
    // });
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

function get_folio_balance(folio, company, party) {
  return frappe.call({
    method: "hms.hms.doctype.room_folio_hms.room_folio_hms.get_folio_balance",
    args: {
      folio: folio,
      company: company,
      party: party,
    },
  });
}

function cr_df_formatter(value, df, options, doc) {
  var currency = frappe.meta.get_field_currency(df, doc);
  var dr_or_cr = value
    ? "<label>" + (value > 0.0 ? __("Dr") : __("Cr")) + "</label>"
    : "";
  return (
    "<div style='text-align: right'>" +
    (value == null || value === ""
      ? ""
      : format_currency(Math.abs(value), currency)) +
    " " +
    dr_or_cr +
    "</div>"
  );
}
