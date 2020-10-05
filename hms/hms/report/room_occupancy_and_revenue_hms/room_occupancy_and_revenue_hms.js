// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Room Occupancy and Revenue HMS"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: hms.utils.get_first_of_month(),
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
    },
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: frappe.defaults.get_user_default("company"),
    },
  ],

  onload(report) {
    frappe.set_redirect_to_ag_report();
  },

  set_gridOptions(gridOptions) {
    let me = this;
    gridOptions.floatingFilter = false;
    gridOptions.defaultColDef = defaultColDef;

    gridOptions.getRowClass = function (params) {
      if (params.node.data.room_type == "Total") {
        return "hms-grid-total";
      }
      return null;
    };
  },
};

//
const defaultColDef = {
  sortable: true,
  resizable: true,
  // tooltipComponent: "customTooltip"
};
