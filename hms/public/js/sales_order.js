frappe.ui.form.on("Sales Order", {
  onload_post_render: function(frm) {},

  onload: function(frm) {},

  set_defaults: function(frm) {
    frm.set_value("no_of_nights_cf", 1);
    frm.set_value("check_in_cf", frappe.datetime.get_today());
    frm.set_value(
      "check_out_cf",
      frappe.datetime.add_days(frappe.datetime.get_today(), 1)
    );
  },

  customer: function(frm) {
    frappe.call({
      method: "hms.hms.controllers.reservation.get_default_contact",
      args: { customer: frm.doc.customer },
      callback: function(r) {
        frm.set_value("guest_cf", r.message);
      }
    });
  },

  refresh: function(frm) {
    if (frm.is_new()) {
      // frm.trigger("set_defaults");
    }

    // toolbar buttons
    // frm.page.inner_toolbar.addClass("hide");
    // setTimeout(() => {
    //   cur_frm.page.remove_inner_button('')
    // }, 400);

    frm.page.add_inner_button("Check In", function(params) {
      make_room_folio(frm);
    });

    if (
      frm.doc.docstatus == 1 &&
      flt(frm.doc.advance_paid) < flt(frm.doc.rounded_total)
    ) {
      frm.page.add_inner_button(__("Transfer Funds"), () => {
        show_transfer_dialog(frm);
      });
    }

    frm.page.set_inner_btn_group_as_primary(__("Create"));
  },

  no_of_nights_cf: function(frm) {
    frm.trigger("set_items");
  },

  check_out_cf: function(frm) {
    frm.trigger("set_items");
  },

  room_no_cf: function(frm) {
    frm.trigger("set_items");
  },

  validate: function(frm) {
    if (frm.doc.no_of_nights_cf < 1) {
      frappe.throw(__("One night is the minimum stay period allowed."));
    }
    if (
      frappe.datetime.get_diff(frm.doc.check_out_cf, frm.doc.check_in_cf) < 0
    ) {
      frappe.throw(
        __("Please select checkout after {0}", [frm.doc.check_in_cf])
      );
    }
  },

  set_items: function(frm) {
    let field = event.srcElement.dataset && event.srcElement.dataset.fieldname;

    if (field == "no_of_nights_cf") {
      frm.set_value(
        "check_out_cf",
        frappe.datetime.add_days(frm.doc.check_in_cf, frm.doc.no_of_nights_cf)
      );
    } else if (field == "check_out_cf") {
      frm.set_value(
        "no_of_nights_cf",
        frappe.datetime.get_diff(d.check_out_cf, d.check_in_cf)
      );
    }
    frm.trigger("room_no_cf");
  },

  room_no_cf: function(frm) {
    if (frm.doc.room_no_cf) {
      frappe.call({
        method: "hms.hms.controllers.reservation.get_room_service_item",
        args: {
          room: frm.doc.room_no_cf
        },
        callback: function(r) {
          if (r.message) {
            frm.doc.items = [];
            let new_row = frm.add_child("items");
            new_row.item_code = r.message;
            new_row.qty = frm.doc.no_of_nights_cf;
            frm.script_manager.trigger(
              "item_code",
              new_row.doctype,
              new_row.name
            );
            frm.refresh_field("items");
          }
        }
      });
    }
  }

  //
  //   set_weekend_rate: function(frm) {
  //     // frappe.model.with_doc("")
  //   },
  //
});

function make_room_folio(frm) {
  var folio = frappe.model.make_new_doc_and_get_name("Room Folio HMS");
  folio = locals["Room Folio HMS"][folio];

  $.extend(folio, {
    reservation: frm.doc.name,
    check_in: frm.doc.check_in_cf,
    check_out: frm.doc.check_out_cf,
    customer: frm.doc.customer,
    company: frm.doc.company,
    room_no: frm.doc.room_no_cf,
    naming_series: "HMS-RR-.YY.-",
    status: "Checked In"
  });

  let guest_detail = frappe.model.add_child(
    folio,
    "Room Guest Detail HMS",
    "room_guest_detail"
  );
  guest_detail.guest = frm.doc.guest_cf;
  frappe.set_route("Form", folio.doctype, folio.name);
}

function show_transfer_dialog(frm) {
  var dialog = new frappe.ui.Dialog({
    title: __("Transfer Funds"),
    fields: [
      {
        label: "Customer",
        fieldname: "customer",
        fieldtype: "ReadOnly",
        default: frm.doc.customer
      },
      {
        label: "Desk Account Balance",
        fieldname: "balance",
        fieldtype: "Currency",
        read_only: 1,
        default: 0
      },
      {
        fieldtype: "Currency",
        fieldname: "amount_to_transfer",
        label: "Amount to Transfer",
        default: "0"
      }
    ],
    primary_action: function() {
      let args = dialog.get_values();

      if (args.amount_to_transfer > 0 - args.balance) {
        frappe.throw(
          `Amount to transfer cannot be greater than ${args.balance}`
        );
        return;
      }

      return frappe.call({
        method:
          "hms.hms.controllers.reservation.make_transfer_jv_to_sales_order",
        args: {
          customer: frm.doc.customer,
          docname: frm.doc.name,
          amount_to_transfer: args.amount_to_transfer
        },
        callback: r => {
          dialog.hide();
          frm.reload_doc();
        }
      });
    }
  });

  get_party_balance(frm.doc.company, frm.doc.customer).then(r => {
    dialog.set_values({
      balance: r.message.desk.balance
    });
    dialog.show();
  });
}

function get_party_balance(company, party) {
  return frappe.call({
    method: "hms.hms.doctype.room_folio_hms.room_folio_hms.get_party_balance",
    args: {
      company: company,
      party: party
    }
  });
}
