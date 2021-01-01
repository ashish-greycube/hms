// Copyright (c) 2020, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Online Booking HMS", {
  refresh: function (frm) {
    let grid = frm.fields_dict["items"].grid;
    grid.add_custom_button("Make Reservation", () => {
      // set route to new Sales Order
      let no_nights = frappe.datetime.get_day_diff(
        frm.doc.check_out,
        frm.doc.check_in
      );

      let guest_count = 0;
      if (grid.grid_rows.length) {
        let row = grid.get_selected_children()[0] || grid.grid_rows[0].doc;
        guest_count = (row.adult_count || 0) + (row.child_count || 0);
      }

      let args = {
        naming_series: "RES-.YYYY.-",
        company: frappe.defaults.get_default("company"),
        customer: frm.doc.customer || "",
        check_in_cf: frm.doc.check_in,
        check_out_cf: frm.doc.check_out,
        no_of_guest_cf: guest_count,
        no_of_nights_cf: no_nights || 1,
        room_type_cf: frm.doc.room_type,
        service_item_cf: frm.doc.package,
        source: "Website Online",
        reservation_reference_cf: frm.doc.name,
      };

      frappe.new_doc("Sales Order", {}).then((f) => {
        setTimeout(() => {
          for (let fld in args) {
            frappe.timeout(0.1).then(() => {
              cur_frm.set_value(fld, args[fld]);
            });
          }
        }, 100);
      });

      // Option-2
      // let new_booking = frappe.model.make_new_doc_and_get_name("Sales Order");
      // new_booking = locals["Sales Order"][new_booking];
      // Object.assign(new_booking, args);
      // frappe.set_route("Form", "Sales Order", new_booking.name).then((f) => {
      //   debugger;
      //   for (let fld in args) {
      //     cur_frm.set_value(fld, args[fld]);
      //   }
      // });
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
