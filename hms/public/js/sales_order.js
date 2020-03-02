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

  refresh: function(frm) {
    if (frm.is_new()) {
      frm.trigger("set_defaults");
    }

    // toolbar buttons
    // frm.page.inner_toolbar.addClass("hide");

    frm.page.add_inner_button("Check In", function(params) {
      make_room_folio(frm);
    });

    // frm.page.add_inner_button(
    //   __("Payment"),
    //   function() {
    //     alert("Create Payment");
    //   },
    //   __("Create")
    // );

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
  frappe.call({
    method: "hms.hms.controllers.reservation.make_room_folio",
    args: {
      docname: frm.doc.name
    },
    callback: function(r) {
      if (!r.exc) {
        var doc = frappe.model.sync(r.message);
        frappe.set_route("Form", r.message.doctype, r.message.name);
      }
    }
  });
}

// },
