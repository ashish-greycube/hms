// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Guest History HMS"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("FromDate"),
      fieldtype: "Date",
      default: "2020-01-01",
      reqd: 1
    }
  ],

  onload(report) {
    frappe.set_redirect_to_ag_report();
  },

  set_gridOptions(gridOptions) {
    gridOptions.defaultColDef = defaultColDef;
    gridOptions.context = { always_recreate: true };
    gridOptions.rowSelection = "single";
    gridOptions.onRowDataChanged = function(params) {};
    gridOptions.onCellDoubleClicked = function(params) {};

    // gridOptions.getContextMenuItems = get_context_menu;
  }
};

//
const defaultColDef = {
  sortable: true,
  resizable: true
};
