// Copyright (c) 2020, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Room Folio HMS", {
  //
  //
  refresh: function(frm) {
    hms.make_grid_charge_and_purchase(frm);

    frm.events.load_charge_and_purchase(frm);

    frm.events.add_custom_buttons(frm);
  },

  add_custom_buttons: function(frm) {
    frm.page.add_inner_button(
      __("Transfer Funds"),
      function() {
        frm.events.show_transfer_dialog(frm);
      },
      __("Actions")
    );

    frm.page.add_inner_button(
      __("Create Payment"),
      function() {
        frm.events.make_payment_entry(frm);
      },
      __("Actions")
    );

    if (true || frm.doc.status == "Checked In") {
      frm.page.add_inner_button(
        __("Check Out"),
        function() {
          frm.events.make_check_out(frm);
        },
        __("Actions")
      );
    }
    frm.page.set_inner_btn_group_as_primary(__("Actions"));
  },

  show_transfer_dialog: function(frm) {
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
        default: frm.doc.customer
      },
      {
        fieldtype: "Data",
        fieldname: "folio",
        hidden: 1,
        default: frm.doc.name
      },
      { fieldtype: "Section Break", label: "" },
      {
        label: "Transfer Type",
        fieldname: "transfer_type",
        fieldtype: "Select",
        reqd: 1,
        options: ["Transfer to Room", "Transfer to Desk"].join("\n"),
        default: "Transfer to Room",
        onchange: () => {
          if (this.value == "Transfer to Room") {
            d.fields_dict["account_from"].set_value(desk_account);
            d.fields_dict["account_to"].set_value(folio_account);
          } else {
            d.fields_dict["account_from"].set_value(desk_account);
            d.fields_dict["account_to"].set_value(folio_account);
          }
        }
      },
      { fieldtype: "Column Break" },
      {
        fieldtype: "Currency",
        fieldname: "amount_to_transfer",
        label: "Amount to Transfer",
        default: "0"
      },
      { fieldtype: "Section Break", label: "Accounts" },
      {
        fieldtype: "ReadOnly",
        label: "Transfer From",
        default: desk_account,
        fieldname: "account_from"
      },
      {
        fieldtype: "Currency",
        fieldname: "available_from",
        read_only: 1,
        label: "Available Balance",
        default: "0"
      },
      { fieldtype: "Column Break" },
      {
        fieldtype: "ReadOnly",
        label: "Transfer To",
        default: folio_account,
        fieldname: "account_to"
      },
      {
        fieldtype: "Currency",
        fieldname: "available_to",
        read_only: 1,
        label: "Available Balance",
        default: "0"
      }
    ];
    var d = new frappe.ui.Dialog({
      title: __("Transfer Funds"),
      fields: fields,
      primary_action: function() {
        console.log(d.get_values());

        frappe.call({
          method:
            "hms.hms.doctype.room_folio_hms.room_folio_hms.make_transfer_jv",
          args: d.get_values(),
          callback: function(r) {
            if (!r.exc) {
              d.hide();
            }
          }
        });
      },
      primary_action_label: __("Submit")
    });
    d.show();
  },

  make_payment_entry: function(frm) {
    return frappe.call({
      doc: frm.doc,
      method: "get_payment_entry",
      callback: function(r) {
        if (r.message) {
          console.log(r.message);
          var doc = frappe.model.sync(r.message)[0];
          frappe.set_route("Form", doc.doctype, doc.name);
        }
      }
    });
  },

  make_check_out: function(frm) {
    return frappe.call({
      doc: frm.doc,
      method: "make_check_out",
      callback: function(r) {
        if (r.message) {
          // frappe.model.sync(r.message)[0];
          frm.reload_doc();
        }
      }
    });
  },

  load_charge_and_purchase: function(frm) {
    return frappe.call({
      method:
        "hms.hms.doctype.room_folio_hms.room_folio_hms.get_charge_and_purchase",
      args: { docname: frm.doc.name },
      callback: function(r) {
        if (r.message) {
          frm.gridOptions.api.setRowData(r.message);
        }
      }
    });
  }

  //
});
