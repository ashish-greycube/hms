// Copyright (c) 2020, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Laundry HMS", {
  onload: function (frm) {
    frm.set_query("room_folio", function () {
      return {
        filters: {
          status: "Checked In",
        },
      };
    });
    frappe.db.get_value(
      "Company",
      { name: frm.doc.company },
      "default_laundry_item_group_cf",
      (r) => {
        frm.set_query("item", "items", function (doc, cdt, cdn) {
          return {
            filters: {
              item_group: r.default_laundry_item_group_cf,
            },
          };
        });
      }
    );
  },

  refresh: function (frm) {
    if (frm.doc.docstatus == 1) {
      frm.page.add_inner_button(__("Make Delivery & Invoice"), function () {
        return frappe.call({
          doc: frm.doc,
          method: "make_delivery_and_invoice",
          callback: function () {
            frappe.show_alert("Invoice created for Laundry.");
            frm.refresh();
          },
        });
      });
    }
  },
});
