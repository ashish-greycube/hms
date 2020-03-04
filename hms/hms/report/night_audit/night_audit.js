// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Night-Audit"] = {
  filters: [
    {
      fieldname: "audit_date",
      label: __("Date"),
      fieldtype: "Date",
      // default: "2020-02-20",
      default: [frappe.datetime.get_today()],
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
    //
    frappe.set_redirect_to_ag_report();

    report.page.add_inner_button(__("Post Charges"), function() {
      let doclist = [];
      let filters = report.get_filter_values();

      for (let r of frappe.ag_report.gridOptions.api.getSelectedNodes()) {
        doclist.push(r.data.name);
      }

      return frappe.call({
        method: "hms.hms.report.night_audit.night_audit.post_charges",
        args: { doclist: doclist, filters: filters },
        callback: function(r) {
          frappe.ag_report.refresh();
        }
      });
    });

    report.page.add_inner_button(
      __("<b>Select / Unselect All</b>"),
      function() {
        hms.utils.toggle_selection(report);
      }
    );

    //
  },

  set_gridOptions(gridOptions) {
    //
    let me = this;
    gridOptions.defaultColDef = {
      sortable: true,
      resizable: true
    };

    // gridOptions.getContextMenuItems = hms.utils.get_context_menu;
    gridOptions.context = { always_recreate: false };
    gridOptions.rowSelection = "multiple";

    gridOptions.isRowSelectable = function(rowNode) {
      return rowNode.data.invoice ? false : true;
    };

    gridOptions.onRowDataChanged = function(params) {};

    gridOptions.onCellDoubleClicked = function(params) {};

    gridOptions.getRowClass = function(params) {
      if (params.node.isSelected()) return null;
      return params.node.data.invoice ? "" : frappe.scrub(`hms-to-charge`);
    };
    //
  }
};
