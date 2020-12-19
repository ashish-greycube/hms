// Copyright (c) 2020, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Online Booking HMS", {
  refresh: function (frm) {
    let grid = frm.fields_dict["items"].grid;
    grid.add_custom_button("Make Reservation", () => {
      let no_nights = frappe.datetime.get_day_diff(
        frm.doc.check_out,
        frm.doc.check_in
      );
      frappe.new_doc("Sales Order", {}).then((f) => {
        cur_frm.set_value("customer", frm.doc.customer || "");
        cur_frm.set_value("check_in_cf", frm.doc.check_in);
        cur_frm.set_value("no_of_nights_cf", no_nights);
        cur_frm.set_value("service_item_cf", frm.doc.package);
        cur_frm.set_value("source", "Website Online");
        cur_frm.set_value("reservation_reference_cf", frm.doc.name);
      });
    });
  },

  create_customer: function (frm) {
    let args = {
      customer_name: frm.doc.guest_name,
      email_id: frm.doc.email,
      mobile_no: frm.doc.phone_no,
      address_line1: frm.doc.address_line_1,
      address_line2: frm.doc.address_line_2,
      pincode: frm.doc.pincode,
      city: frm.doc.city,
    };
    frappe.ui.form
      .make_quick_entry(
        "Customer",
        (new_doc) => {
          frm.set_value("customer", new_doc.name);
        },
        null,
        null
      )
      .then((qe) => {
        for (let [key, value] of Object.entries(args)) {
          qe.dialog.set_value(key, value);
        }
      });
  },
});
