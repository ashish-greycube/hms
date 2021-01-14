// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Night-Audit"] = {
  filters: [
    {
      fieldname: "audit_date",
      label: __("Date"),
      fieldtype: "Date",
      default: [frappe.datetime.add_days(frappe.datetime.get_today(), -1)],
      reqd: 1,
    },
    {
      fieldname: "operation",
      label: __("Operation"),
      fieldtype: "Select",
      options: "Rooms to Charge\nRooms to CheckIn\nRooms to CheckOut",
      default: "Rooms to Charge",
      reqd: 1,
      on_change: function (me) {
        me.page.inner_toolbar
          .find(
            'button[data-label="' + encodeURIComponent("Post Charges") + '"]'
          )
          .toggle(me.get_filter_value("operation") === "Rooms to Charge");
        me.refresh();
      },
    },
  ],

  onload(report) {
    //
    frappe.set_redirect_to_ag_report();

    report.page.add_inner_button(__("Post Charges"), function () {
      let doclist = [];
      let filters = report.get_filter_values();

      for (let r of frappe.ag_report.gridOptions.api.getSelectedNodes()) {
        doclist.push(r.data.name);
      }

      return frappe.call({
        method: "hms.hms.report.night_audit.night_audit.post_charges",
        args: { doclist: doclist, filters: filters },
        callback: function (r) {
          frappe.ag_report.refresh();
        },
      });
    });

    report.page.add_inner_button(
      __("<b>Select / Unselect All</b>"),
      function () {
        hms.utils.toggle_selection(report);
      }
    );

    // report.page.add_inner_button(__("<b>Set System Date</b>"), function () {
    //   let fields = [
    //     {
    //       fieldtype: "Date",
    //       label: __("System Date"),
    //       fieldname: "system_date",
    //       default: frappe.datetime.get_today(),
    //     },
    //   ];

    //   frappe.prompt(fields, function (filters) {
    //     //
    //     return frappe.call({
    //       method: "hms.hms.report.night_audit.night_audit.set_system_date",
    //       args: filters,
    //       callback: function (r) {
    //         frappe.msgprint(`System date is set to ${filters.system_date}`);
    //       },
    //     });
    //   });
    // });

    //
  },

  set_gridOptions(gridOptions) {
    //
    let me = this;
    gridOptions.defaultColDef = {
      sortable: true,
      resizable: true,
    };

    gridOptions.context = { always_recreate: true };
    // gridOptions.getContextMenuItems = hms.utils.get_context_menu;
    gridOptions.rowSelection = "multiple";

    gridOptions.isRowSelectable = function (rowNode) {
      return rowNode.data.invoice ? false : true;
    };

    gridOptions.onRowDataChanged = function (params) {};

    gridOptions.onCellDoubleClicked = function (params) {};

    gridOptions.getRowClass = function (params) {
      if (params.node.isSelected()) return null;
      return params.node.data.invoice ? "" : frappe.scrub(`hms-to-charge`);
    };
    //
  },
};
