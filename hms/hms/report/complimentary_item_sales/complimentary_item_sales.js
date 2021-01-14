// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Complimentary Item Sales"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("Date"),
      fieldtype: "Date",
      default: [frappe.datetime.month_start()],
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("Date"),
      fieldtype: "Date",
      default: [frappe.datetime.get_today()],
      reqd: 1,
    },
    {
      fieldname: "item_code",
      label: __("Item"),
      fieldtype: "Link",
      options: "Item",
      get_query: function () {
        return {
          query:
            "hms.hms.report.complimentary_item_sales.complimentary_item_sales.complimentary_items_query",
        };
      },
      reqd: 0,
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
    //
  },
};
