// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Guest Master HMS"] = {
  filters: [],

  onload(report) {
    frappe.set_redirect_to_ag_report();
  },

  set_gridOptions(gridOptions) {
    gridOptions.defaultColDef = defaultColDef;
    gridOptions.context = { always_recreate: true };
    gridOptions.rowSelection = "single";
    gridOptions.onRowDataChanged = function (params) {};
    gridOptions.onCellDoubleClicked = function (params) {};

    // gridOptions.getContextMenuItems = get_context_menu;
  },
};

//
const defaultColDef = {
  sortable: true,
  resizable: true,
};
