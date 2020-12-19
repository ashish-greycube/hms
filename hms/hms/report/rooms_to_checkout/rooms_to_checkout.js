// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Rooms To Checkout"] = {
  filters: [
    {
      fieldname: "check_out",
      label: __("Checkout Date"),
      fieldtype: "Date",
      default: [frappe.datetime.get_today()],
      reqd: 1,
    },
    {
      fieldname: "status",
      label: __("Status"),
      fieldtype: "Select",
      options: "\nChecked In\nChecked Out",
    },
  ],

  onload(report) {
    //
    frappe.set_redirect_to_ag_report();
    //
  },

  set_gridOptions(gridOptions) {
    //
    let me = this;
    gridOptions.defaultColDef = {
      sortable: true,
      resizable: true,
    };

    gridOptions.getRowClass = function (params) {
      return params.node.data.status == "Checked In"
        ? frappe.scrub(`hms-in-house`)
        : "";
    };
    //
  },
};
