frappe.ui.form.on("Sales Order", {
  onload_post_render: function (frm) {},

  onload: function (frm) {},

  set_defaults: function (frm) {
    frm.set_value("no_of_nights_cf", 1);
    frm.set_value("check_in_cf", frappe.datetime.get_today());
    frm.set_value(
      "check_out_cf",
      frappe.datetime.add_days(frappe.datetime.get_today(), 1)
    );
  },

  customer: function (frm) {
    if (frm.doc.customer) {
      frappe.call({
        method: "hms.hms.controllers.reservation.get_default_contact",
        args: { customer: frm.doc.customer },
        callback: function (r) {
          frm.set_value("guest_cf", r.message);
        },
      });
    }
  },

  refresh: function (frm) {
    if (frm.is_new()) {
      // frm.trigger("set_defaults");
    }
    remove_so_buttons(frm);

    if (frm.doc.docstatus == 1) {
      frm.page.add_inner_button("Check In", function (params) {
        make_room_folio(frm);
      });
    }

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

  no_of_nights_cf: function (frm) {
    if (frm.doc.no_of_nights_cf) {
      frm.doc.check_out_cf = frappe.datetime.add_days(
        frm.doc.check_in_cf,
        frm.doc.no_of_nights_cf
      );
      frm.trigger("_room_no_cf");
    }
  },

  check_in_cf: function (frm) {
    frm.doc.no_of_nights_cf = 0;
    frm.doc.check_out_cf = "";
    frm.trigger("_room_no_cf");
  },

  check_out_cf: function (frm) {
    if (frm.doc.check_out_cf) {
      frm.doc.no_of_nights_cf = frappe.datetime.get_diff(
        frm.doc.check_out_cf,
        frm.doc.check_in_cf
      );
      frm.trigger("_room_no_cf");
    }
  },

  room_no_cf: function (frm) {
    frm.trigger("_room_no_cf");
  },

  validate: function (frm) {
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

  _room_no_cf: function (frm) {
    frm.set_value("items", []);
    if (
      frm.doc.room_no_cf &&
      frm.doc.check_in_cf &&
      frm.doc.no_of_nights_cf > 0
    ) {
      frappe.call({
        method: "hms.hms.controllers.reservation.get_holidays",
        args: {
          company: frm.doc.company,
          check_in: frm.doc.check_in_cf,
          check_out: frm.doc.check_out_cf,
        },
        callback: (r) => {
          //
          frappe.dom.freeze();
          for (let i = 0; i < frm.doc.no_of_nights_cf; i++) {
            let new_row = frm.add_child("items");
            new_row.item_code = frm.doc.service_item_cf;
            new_row.qty = 1;
            let cur_date = frappe.datetime.add_days(frm.doc.check_in_cf, i);
            new_row.reservation_date_cf = cur_date;
            new_row.is_holiday_cf = r.message.holidays.includes(cur_date)
              ? 1
              : 0;
            frm.script_manager.trigger(
              "item_code",
              new_row.doctype,
              new_row.name
            );
          }
          frm.refresh_fields();
          setTimeout(() => {
            apply_holiday_pricing_list(r.message.holiday_price_list);
          }, 50);
          //
        },
      });
    }
  },
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
    status: "Checked In",
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
        default: frm.doc.customer,
      },
      {
        label: "Desk Account Balance",
        fieldname: "balance",
        fieldtype: "Currency",
        read_only: 1,
        default: 0,
      },
      {
        fieldtype: "Currency",
        fieldname: "amount_to_transfer",
        label: "Amount to Transfer",
        default: "0",
      },
    ],
    primary_action: function () {
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
          amount_to_transfer: args.amount_to_transfer,
        },
        callback: (r) => {
          dialog.hide();
          frm.reload_doc();
        },
      });
    },
  });

  get_party_balance(frm.doc.company, frm.doc.customer).then((r) => {
    dialog.set_values({
      balance: r.message.desk.balance,
    });
    dialog.show();
  });
}

function get_party_balance(company, party) {
  return frappe.call({
    method: "hms.hms.doctype.room_folio_hms.room_folio_hms.get_party_balance",
    args: {
      company: company,
      party: party,
    },
  });
}

function remove_so_buttons(frm) {
  setTimeout(() => {
    frm.page.remove_inner_button("Update Items");
    frm.page.remove_inner_button("Quotation", "Get items from");
    frm.page.remove_inner_button("Hold", "Status");
    frm.page.remove_inner_button("Close", "Status");
    for (let btn of [
      "Pick List",
      "Delivery Note",
      "Work Order",
      "Material Request",
      "Request for Raw Materials",
      "Purchase Order",
      "Project",
      "Subscription",
      // "Payment Request"
    ]) {
      frm.page.remove_inner_button(btn, "Create");
    }
  }, 300);
}

function apply_holiday_pricing_list(price_list, reset_plc_conversion) {
  var me = cur_frm.cscript;
  // We need to reset plc_conversion_rate sometimes because the call to
  // `erpnext.stock.get_item_details.apply_price_list` is sensitive to its value
  if (!reset_plc_conversion) {
    me.frm.set_value("plc_conversion_rate", "");
  }
  var args = me._get_args();
  let holidays = [];
  for (let i of cur_frm.doc.items.filter((i) => i.is_holiday_cf == 1)) {
    holidays.push.apply(
      holidays,
      args.items.filter((t) => t.name == i.name)
    );
  }

  args.items = holidays;
  args.price_list = price_list;
  if (!((args.items && args.items.length) || args.price_list)) {
    return;
  }

  if (me.in_apply_price_list == true) return;

  me.in_apply_price_list = true;
  return me.frm
    .call({
      method: "erpnext.stock.get_item_details.apply_price_list",
      args: { args: args },
      callback: function (r) {
        if (!r.exc) {
          frappe.run_serially([
            () =>
              me.frm.set_value(
                "price_list_currency",
                r.message.parent.price_list_currency
              ),
            () =>
              me.frm.set_value(
                "plc_conversion_rate",
                r.message.parent.plc_conversion_rate
              ),
            () => {
              if (args.items.length) {
                me._set_values_for_item_list(r.message.children);
              }
            },
            () => {
              me.in_apply_price_list = false;
            },
          ]);
        } else {
          me.in_apply_price_list = false;
        }
      },
    })
    .always(() => {
      me.in_apply_price_list = false;
      frappe.dom.unfreeze();
    });
}
window.apply_holiday_pricing_list = apply_holiday_pricing_list;
