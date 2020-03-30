frappe.listview_settings["Date Lookup HMS"] = {
  onload: function(listview) {
    listview.page.set_title(__("Dates Lookup"));
    listview.page.add_menu_item(__("Create Dates"), () => {
      show_dialog();
    });
  },

  add_fields: ["date", "year", "month_name", "weekday_name"]
};

var show_dialog = function() {
  var fields = [
    { fieldname: "start_date", label: "Start", fieldtype: "Date" },
    { fieldname: "end_date", label: "End", fieldtype: "Date" }
  ];

  var dialog = new frappe.ui.Dialog({
    title: __("Create Lookup Dates"),
    fields: fields,
    primary_action_label: __("Submit"),
    primary_action: function() {
      var args = dialog.get_values();
      frappe.call({
        method: "hms.hms.doctype.date_lookup_hms.date_lookup_hms.create_dates",
        args: args,
        callback: function(r) {
          dialog.hide();
        }
      });
    }
  });
  dialog.show();
};
