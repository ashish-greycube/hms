frappe.ui.form.on("Sales Order", {
  onload_post_render: function(frm) {},

  onload: function(frm) {},

  no_of_nights_cf: function(frm) {
    if (frm.doc.no_of_nights_cf < 1) {
      frappe.throw(__("One night is the minimum stay period allowed."));
    }

    let check_out = frappe.datetime.add_days(
      frm.doc.check_in_cf,
      frm.doc.no_of_nights_cf
    );
    frm.doc.check_out_cf = check_out;
    frm.events.set_nights(frm);
  },

  set_nights: function(frm) {
    if ((frm.doc.items || []).length > 0) {
      let item = frm.doc.items[0];
      frappe.model.set_value(
        item.doctype,
        item.name,
        "qty",
        frm.doc.no_of_nights_cf
      );
    }
  },

  check_out_cf: function(frm) {
    let d = frm.doc;

    if (frappe.datetime.get_diff(d.check_out_cf, d.check_in_cf) < 0) {
      frappe.throw(__("Please select checkout after {0}", [d.check_in_cf]));
    }
    let no_of_nights_cf = frappe.datetime.get_diff(
      d.check_out_cf,
      d.check_in_cf
    );
    frm.doc.no_of_nights_cf = no_of_nights_cf > 0 ? no_of_nights_cf : 1;
    frm.events.set_nights(frm);
  },

  room_no_cf: function(frm) {
    if (frm.doc.room_no_cf) {
      frm.doc.items = [];
      frappe.call({
        method: "hms.hms.controllers.reservation.get_room_service_item",
        args: {
          room: frm.doc.room_no_cf
        },
        callback: function(r) {
          if (r.message) {
            var item = frappe.model.add_child(
              frm.doc,
              "Sales Order Item",
              "items"
            );
            frappe.model.set_value(
              item.doctype,
              item.name,
              "item_code",
              r.message
            );
            frappe.model.set_value(item.doctype, item.name, "qty", 1);
            frm.event.set_weekend_rate(frm);
            frm.refresh();
          }
        }
      });
    }
  },

  set_weekend_rate: function(frm) {
    // frappe.model.with_doc("")
  },

  refresh: function(frm) {
    frm.page.clear_inner_toolbar();

    frm.page.add_inner_button("Check In", function(params) {
      alert("Check In");
    });

    frm.page.add_inner_button(
      __("Payment"),
      function() {
        alert("Create Payment");
      },
      __("Create")
    );

    frm.page.set_inner_btn_group_as_primary(__("Create"));
  }
});
