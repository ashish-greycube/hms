// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Restaurant Chef Report"] = {
  filters: [
    {
      fieldname: "room_date",
      label: __("Date"),
      fieldtype: "Date",
      default: [frappe.datetime.add_days(frappe.datetime.get_today(), 1)],
      reqd: 1,
    },
    {
      fieldname: "show_room_no",
      label: __("Show Room No"),
      fieldtype: "Check",
      default: 0,
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
