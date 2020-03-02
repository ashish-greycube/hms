// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Frontdesk HMS"] = {
  filters: [
    {
      fieldname: "date_range",
      label: __("Date Range"),
      fieldtype: "DateRange",
      default: [
        frappe.datetime.get_today(),
        frappe.datetime.add_days(frappe.datetime.get_today(), 10)
      ],
      reqd: 1
    }
  ],

  onload(report) {
    frappe.set_redirect_to_ag_report();
  },

  set_gridOptions(gridOptions) {
    let me = this;
    gridOptions.defaultColDef = {
      sortable: true,
      resizable: true
    };

    gridOptions.context = { always_recreate: true };
    gridOptions.rowSelection = "multiple";
    // gridOptions.getContextMenuItems = hrms.utils.get_context_menu;

    // get_column_defs(gridOptions);

    gridOptions.onRowDataChanged = function(params) {
      // frappe.add_row_numbers(frappe.ag_report);
    };

    gridOptions.onCellDoubleClicked = function(params) {
      // hrms.utils.open_attendance(params);
    };
  }
};
