// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Night-Audit"] = {
  filters: [
    {
      fieldname: "room_date",
      label: __("Date"),
      fieldtype: "Date",
      default: "2020-02-20",
      // default:  [frappe.datetime.get_today()],
      reqd: 1
    },
    {
      fieldname: "status",
      label: __("Status"),
      fieldtype: "Select",
      options: "\nNot Charged\nCheck In\nCheck Out"
    }
  ],

  onload(report) {
    frappe.set_redirect_to_ag_report();

    report.page.add_inner_button(__("<b>Select/Clear All</b>"), function() {
      hms.utils.toggle_selection(report);
    });
  },

  set_gridOptions(gridOptions) {
    let me = this;
    gridOptions.defaultColDef = {
      sortable: true,
      resizable: true
    };

    gridOptions.context = { always_recreate: false };
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
