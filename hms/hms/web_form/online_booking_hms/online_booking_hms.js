frappe.ready(function () {
  setTimeout(() => {
    // setup_pricing_table();
    set_filters();
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
    frappe.web_form.fields_dict["items"].grid.remove_all();
    // for testing
    // frappe.web_form.set_value("room_type", "LUX-SH");
    // frappe.web_form.set_value("package", "Gold Membership - 12");
    // frappe.web_form.set_value("check_in", "2020-12-16");
    // frappe.web_form.set_value("check_out", "2020-12-18");
    // frappe.web_form.set_value("items", []);
  });
});

set_items_description = function () {
  $('div.frappe-control[data-fieldname="items"] > div#guest-count')
    .detach()
    .appendTo($('div.frappe-control[data-fieldname="items"]'));

  $('div.frappe-control[data-fieldname="items"] > p').remove();
};

clear_buttons = function () {
  $(".web-form-actions .btn").remove();
  $(".web-form-footer .btn").remove();
  frappe.web_form.add_button("Make New Booking", "primary", function () {
    window.location.reload();
  });
};

function set_filters() {
  let package = frappe.web_form.fields_dict["package"];

  package.df.onchange = function () {
    let rate = package.df.options.filter((t) => {
      return t.value == frappe.web_form.doc.package;
    });
    frappe.web_form.set_value("room_rate", rate.length ? rate[0].room_rate : 0);
  };

  frappe.call({
    method: "hms.hms.controllers.reservation.get_online_packages",
    callback: function (r) {
      package.df.options = r.message;
      package.set_options();
    },
  });

  package.awesomplete.filter = function (text, input) {
    return (package.df.options || []).some((t) => {
      return (
        t.room_type_cf === frappe.web_form.doc.room_type &&
        text.label === t.value &&
        text.label.indexOf(input) === 0
      );
    });
  };
}

function add_custom_buttons() {
  frappe.web_form.add_button_to_header(
    "Check Availability",
    "light",
    check_availability
  );
  frappe.web_form.add_button_to_header("Confirm Booking", "primary", _save);
  //
  frappe.web_form.add_button_to_footer(
    "Check Availability",
    "light",
    check_availability
  );
  frappe.web_form.add_button_to_footer("Confirm Booking", "primary", _save);
}

function check_availability() {
  if (validate()) {
    frappe.call({
      method: "hms.hms.controllers.reservation.get_rooms_available",
      args: frappe.web_form.doc,
      callback: function (r) {
        let msg = __(
          `${r.message} rooms are available for the selected dates.`
        );
        frappe.web_form.set_form_description(msg);
        frappe.msgprint({
          message: msg,
          indicator: "green",
          title: __("Rooms Available"),
        });
      },
    });
  }
}

function validate() {
  let doc = frappe.web_form.doc;
  let fields = ["package", "check_in", "check_out"];
  let missing = [];
  for (const f of fields) {
    if (!doc[f]) missing.push(frappe.model.unscrub(f));
  }
  if (missing.length) {
    frappe.msgprint({
      title: "Validation Error",
      indicator: "red",
      message: "Please fill values for " + missing.join(", "),
    });
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
    frappe.msgprint({
      title: "Validation Error",
      indicator: "red",
      message: "Please fill values for " + missing.join(", "),
    });
  }

  if (!doc.items.length) {
    frappe.msgprint({
      title: "Validation Error",
      indicator: "red",
      message: "Please fill atleast 1 room detail to confirm booking.",
    });
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
        frappe.msgprint({
          message: msg,
          indicator: "green",
          title: __("Room Booking successful"),
        });

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

function setup_pricing_table() {
  $(`<div class="card-deck mb-3 text-center">
  <div class="card mb-3 box-shadow">
    <div class="card-header">
      <h4 class="my-0 font-weight-normal">Standard Premium</h4>
    </div>
    <div class="card-body">
      <h1 class="card-title pricing-card-title">$1200 <small class="text-muted">/ night</small></h1>
      <ul class="list-unstyled mt-3 mb-3">
        <li>Breakfast included</li>
        <li>Spa for 2</li>
        <li>Saloon and Gym</li>
      </ul>
      <button type="button" class="btn btn-lg btn-block btn-outline-primary">Select</button>
    </div>
  </div>
  <div class="card mb-3 box-shadow">
    <div class="card-header">
      <h4 class="my-0 font-weight-normal">Standard Premium</h4>
    </div>
    <div class="card-body">
      <h1 class="card-title pricing-card-title">$1200 <small class="text-muted">/ night</small></h1>
      <ul class="list-unstyled mt-3 mb-3">
        <li>Breakfast included</li>
        <li>Spa for 2</li>
        <li>Saloon and Gym</li>
      </ul>
      <button type="button" class="btn btn-lg btn-block btn-outline-primary">Select</button>
    </div>
  </div>
  <div class="card mb-3 box-shadow">
    <div class="card-header">
      <h4 class="my-0 font-weight-normal">Standard Premium</h4>
    </div>
    <div class="card-body">
      <h1 class="card-title pricing-card-title">$1200 <small class="text-muted">/ night</small></h1>
      <ul class="list-unstyled mt-3 mb-3">
        <li>Breakfast included</li>
        <li>Spa for 2</li>
        <li>Saloon and Gym</li>
      </ul>
      <button type="button" class="btn btn-lg btn-block btn-outline-primary">Select</button>
    </div>
  </div>
  <div class="card mb-3 box-shadow">
  <div class="card-header">
    <h4 class="my-0 font-weight-normal">Standard Premium</h4>
  </div>
  <div class="card-body">
    <h1 class="card-title pricing-card-title">$1200 <small class="text-muted">/ night</small></h1>
    <ul class="list-unstyled mt-3 mb-3">
      <li>Breakfast included</li>
      <li>Spa for 2</li>
      <li>Saloon and Gym</li>
    </ul>
    <button type="button" class="btn btn-lg btn-block btn-outline-primary">Select</button>
  </div>
</div>
</div>`).insertBefore(".web-form-wrapper");
}
