// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Shift Report"] = {
  filters: [
    {
      fieldname: "shift_date",
      label: __("Date"),
      fieldtype: "Date",
      default: [frappe.datetime.add_days(frappe.datetime.get_today(), 0)],
      // default: "2021-01-05",
      reqd: 0,
    },
    {
      fieldname: "user",
      label: __("User"),
      fieldtype: "Link",
      options: "User",
      //   default: frappe.user.name,
      reqd: 0,
    },
    {
      fieldname: "mode_of_payment",
      label: __("MoP"),
      fieldtype: "Select",
      options: "\nCash\nCredit",
    },
    {
      fieldname: "summary_view",
      label: __("Show Summary"),
      fieldtype: "Check",
      default: 0,
    },
  ],

  onload(report) {
    frappe.timeout(0.8).then(() => {
      set_print_shift_report(report);
    });
  },
};

function set_print_shift_report(report) {
  report.page.page_actions
    .find("li > a.grey-link span[data-label='Print']")
    .parent()
    .remove();
  report.page.add_menu_item("Print", () => {
    open_url_post(
      "/api/method/hms.hms.report.shift_report.shift_report.get_shift_report",
      { filters: report.get_filter_values() },
      true
    );
  });
}
