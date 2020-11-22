// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Room Folio Statement"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("From"),
      fieldtype: "Date",
      default: [frappe.datetime.get_today()],
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("To"),
      fieldtype: "Date",
      default: [frappe.datetime.get_today()],
      reqd: 1,
    },
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
    },
    {
      fieldname: "customer",
      label: __("Customer"),
      fieldtype: "Link",
      options: "Customer",
    },
    {
      fieldname: "folio_status",
      label: __("Status"),
      fieldtype: "Select",
      options: ["Checked In", "Checked Out", "Cancelled"],
    },

    {
      fieldname: "room_folio",
      label: __("Room Folio"),
      fieldtype: "Link",
      options: "Room Folio HMS",
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

    gridOptions.rowSelection = "multiple";
    // gridOptions.context = { always_recreate: false };
    gridOptions.onRowDataChanged = function (params) {};
    gridOptions.onCellDoubleClicked = function (params) {};
    gridOptions.getRowClass = function (params) {
      return null;
      //   if (params.node.isSelected()) return null;
      //   return params.node.data.invoice ? "" : frappe.scrub(`hms-to-charge`);
    };
    //
  },
};
