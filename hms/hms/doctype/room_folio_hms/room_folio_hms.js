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
      __("Create Payment"),
      function() {
        frm.events.make_payment_entry(frm);
      },
      __("Actions")
    );

    if (true || !frm.doc.status) {
      frm.page.add_inner_button(
        __("Check In"),
        function() {
          frm.events.check_in(frm);
        },
        __("Actions")
      );
    }

    if (true || frm.doc.status == "Checked In") {
      frm.page.add_inner_button(
        __("Check Out"),
        function() {
          frm.events.check_out(frm);
        },
        __("Actions")
      );
    }
    frm.page.set_inner_btn_group_as_primary(__("Actions"));
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

  check_in: function(frm) {
    return frappe.call({
      doc: frm.doc,
      method: "make_check_in",
      callback: function(r) {
        if (r.message) {
          // frappe.model.sync(r.message)[0];
          frm.reload_doc();
        }
      }
    });
  },

  check_out: function(frm) {
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
          console.log(r.message);
          frm.gridOptions.api.setRowData(r.message);
        }
      }
    });
  }

  //
});
