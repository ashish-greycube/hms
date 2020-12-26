// Copyright (c) 2020, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Laundry HMS", {
  refresh: function (frm) {
    if (frm.doc.docstatus == 0) {
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
