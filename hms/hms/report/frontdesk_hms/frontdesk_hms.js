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
    },
    {
      fieldname: "room_type",
      label: __("Room Type"),
      fieldtype: "Select",
      options: "\nCLAS-SH\nSUPR-SH"
    }
  ],

  onload(report) {
    frappe.set_redirect_to_ag_report();
  },

  set_gridOptions(gridOptions) {
    let me = this;
    set_column_defs(gridOptions);
    gridOptions.defaultColDef = defaultColDef;
    gridOptions.context = { always_recreate: true };
    gridOptions.rowSelection = "multiple";
    gridOptions.onRowDataChanged = function(params) {};
    gridOptions.onCellDoubleClicked = function(params) {
      open_reservation(params);
    };

    // gridOptions.getContextMenuItems = get_context_menu;
  }
};

//
const defaultColDef = {
  sortable: true,
  resizable: true
};

//
function set_column_defs(gridOptions) {
  for (let c of gridOptions.columnDefs) {
    c.cellClass = function(params) {
      return params.data[`${c.field}_css`] || "";
    };
  }
}

//
function open_reservation(params) {
  let data = params.data,
    date = params.colDef.colId;
  // goto folio
  if (data[`${date}_folio`]) {
    frappe.set_route("Form", "Room Folio HMS", data[`${date}_folio`]);
    return;
  }
  // goto reservation
  else if (data[`${date}_reservation`]) {
    frappe.set_route("Form", "Sales Order", data[`${date}_reservation`]);
    return;
  }
  // goto new reservation
  frappe.new_doc("Sales Order", {}).then(f => {
    cur_frm.set_value("customer", "Dummy Customer");
    cur_frm.set_value("check_in_cf", date);
    cur_frm.set_value("room_no_cf", data["room_no"]);
  });
}
