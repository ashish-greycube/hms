frappe.ready(function () {
  add_custom_buttons();
});

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
}

function validate() {
  let doc = frappe.web_form.doc,
    messages = [];
  if (!doc.room_type) {
    messages.push("Please select Room Type");
  }
  if (!doc.check_in) {
    messages.push("Please select Check In Date");
  }
  if (!doc.check_out) {
    messages.push("Please select Check Out Date");
  }
  if (!doc.package) {
    messages.push("Please select Package");
  }
  if (messages.length) {
    frappe.throw(messages.join("<br>"));
    return false;
  }
  return true;
}
