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

    frm.events.set_party_balance(frm);
    frm.events.set_oustanding_charges(frm);
    frm.events.set_advance_against_reservation(frm);

    frm.set_query("room_package", () => {
      return {
        filters: {
          room_type_cf: frm.doc.room_type,
        },
      };
    });

    frm.set_query("room_no", () => {
      return {
        filters: {
          check_in: frm.doc.check_in,
          check_out: frm.doc.check_out,
          company: frm.doc.company,
        },
        query: "hms.hms.controllers.reservation.get_available_rooms",
      };
    });
  },

  set_oustanding_charges: function (frm) {
    frappe.call({
      method:
        "hms.hms.doctype.room_folio_hms.room_folio_hms.get_folio_outstanding_charges",
      args: { folio: frm.doc.name },
      callback: function (r) {
        if (!r.exc) {
          frm.fields_dict["outstanding_charges"].set_input(cint(r.message));
        }
      },
    });
  },

  set_advance_against_reservation: function (frm) {
    frappe.call({
      method:
        "hms.hms.doctype.room_folio_hms.room_folio_hms.get_advance_against_reservation",
      args: { folio: frm.doc.name },
      callback: function (r) {
        if (!r.exc) {
          frm.fields_dict["total_advance_paid"].set_input(cint(r.message));
        }
      },
    });
  },

  set_party_balance: function (frm) {
    frappe.call({
      method: "hms.hms.doctype.room_folio_hms.room_folio_hms.get_party_balance",
      args: { customer: frm.doc.customer, company: frm.doc.company },
      callback: function (r) {
        if (!r.exc) {
          let party_balance = r.message || 0;
          frm.fields_dict["balance"].set_input(party_balance);
          frm.fields_dict["balance"].$input_wrapper
            .find(".control-value, input")
            .addClass(party_balance <= 0 ? "hms-credit" : "hms-debit")
            .removeClass(party_balance > 0 ? "hms-credit" : "hms-debit");
        }
      },
    });
  },

  add_custom_buttons: function (frm) {
    frm.page.add_inner_button(__("Frontdesk"), () => {
      frappe.set_route("ag-report/Frontdesk HMS");
    });

    if (frm.is_new()) {
      return;
    }

    if (
      frm.doc.status == "Pre-Check In" &&
      frm.doc.is_checklist_done & (frm.doc.docstatus == 1)
    ) {
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
      frappe.call({
        method: "hms.hms.doctype.room_folio_hms.room_folio_hms.allow_check_in",
        args: { customer: frm.doc.customer, company: frm.doc.company },
        callback: function (r) {
          if (!r.exc && r.message == 1) {
            frm.page.add_inner_button(
              __("Make Sign In Sheet"),
              function () {
                frm.events.make_sign_in_sheet(frm);
              },
              __("Actions")
            );
          }
        },
      });
    }

    // Transfer Funds is discontinued, as same account used for Desk and Folio
    // frm.page.add_inner_button(
    //   __("Transfer Funds"),
    //   function () {
    //     frm.events.show_transfer_dialog(frm);
    //   },
    //   __("Actions")
    // );

    frm.page.add_inner_button(
      __("Make Payment"),
      function () {
        frm.events.make_payment_entry(frm);
      },
      __("Actions")
    );

    if (frm.doc.status == "Checked In") {
      frappe.call({
        method: "hms.hms.doctype.room_folio_hms.room_folio_hms.allow_check_out",
        args: {
          folio: frm.doc.name,
          customer: frm.doc.customer,
          company: frm.doc.company,
        },
        callback: function (r) {
          if (!r.exc && r.message == 1) {
            frm.page.add_inner_button(
              __("Check Out"),
              function () {
                frm.events.make_check_out(frm);
              },
              __("Actions")
            );
          }
        },
      });
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
        default: 0,
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
