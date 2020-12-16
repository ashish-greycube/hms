frappe.ready(function () {
  setTimeout(() => {
    add_custom_buttons();
    set_items_description();
  }, 600);

  frappe.web_form.validate = () => {
    let data = frappe.web_form.get_values();
    frappe.web_form.doc["items"] = data.items || [];
    return validate_confirm();
  };

  frappe.web_form.events.on("after_load", function () {
    $(".btn.btn-primary:contains('Save')").remove();
    // for testing
    frappe.web_form.set_value("room_type", "LUX-SH");
    frappe.web_form.set_value("package", "Gold Membership - 12");
    frappe.web_form.set_value("check_in", "2020-12-16");
    frappe.web_form.set_value("check_out", "2020-12-18");
    frappe.web_form.set_value("items", []);
  });
});

set_items_description = function () {
  $('div.frappe-control[data-fieldname="items"] > div#guest-count')
    .detach()
    .appendTo($('div.frappe-control[data-fieldname="items"]'));
};

clear_buttons = function () {
  $(".web-form-actions .btn").remove();
};

function add_custom_buttons() {
  frappe.web_form.add_button("Check Availability", "light", function () {
    if (validate()) {
      frappe.call({
        method: "hms.hms.controllers.reservation.get_rooms_available",
        args: frappe.web_form.doc,
        callback: function (r) {
          frappe.web_form.set_form_description(
            `${r.message} rooms are available for the selected dates.`
          );
        },
      });
    }
  });
  //
  frappe.web_form.add_button("Confirm Booking", "primary", _save);
}

function validate() {
  let doc = frappe.web_form.doc;
  let fields = ["room_type", "package", "check_in", "check_out"];
  let missing = [];
  for (const f of fields) {
    if (!doc[f]) missing.push(frappe.model.unscrub(f));
  }
  if (missing.length) {
    frappe.msgprint("Please fill values for " + missing.join(", "));
  }
  return missing.length == 0;
}

function validate_confirm() {
  let doc = frappe.web_form.doc;
  let fields = [
    "guest_name",
    "email",
    "phone_no",
    "address_line_1",
    "address_line_2",
    "city",
    "pincode",
  ];

  let missing = [];
  for (const f of fields) {
    if (!doc[f]) missing.push(frappe.model.unscrub(f));
  }
  if (missing.length) {
    frappe.msgprint("Please fill values for " + missing.join(", "));
  }
  if (!doc.items.length) {
    frappe.msgprint("Please fill atleast 1 room detail to confirm booking.");
  }

  return missing.length == 0 && doc.items.length > 0;
}

function _save() {
  let wf = frappe.web_form;
  if (wf.validate && !wf.validate()) {
    return;
  }

  if (window.saving) return;
  let for_payment = Boolean(wf.accept_payment && !wf.doc.paid);

  wf.doc.doctype = wf.doc_type;
  wf.doc.web_form_name = wf.name;

  // Save
  window.saving = true;
  frappe.form_dirty = false;

  frappe.call({
    type: "POST",
    method: "frappe.website.doctype.web_form.web_form.accept",
    args: {
      data: wf.doc,
      web_form: wf.name,
      docname: wf.doc.name,
      for_payment,
    },
    callback: (response) => {
      // Check for any exception in response
      if (!response.exc) {
        // Success
        let msg = __("Your booking has been submitted successfully.");
        frappe.web_form.set_form_description(msg);
        clear_buttons();
        // console.log(response.message);
      }
    },
    always: function () {
      window.saving = false;
    },
  });
  return true;
}
