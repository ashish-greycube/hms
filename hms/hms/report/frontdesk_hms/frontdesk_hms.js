// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Frontdesk HMS"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.add_days(frappe.datetime.get_today(), -1),

      reqd: 1
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.add_days(frappe.datetime.get_today(), 10),
      reqd: 1
    },
    {
      fieldname: "room_type",
      label: __("Room Type"),
      fieldtype: "Select",
      options: "\nCLAS-SH\nSUPR-SH"
    },
    {
      fieldname: "room_status",
      label: __("Room Status"),
      fieldtype: "Select",
      options: "\nDirty\nCheckedIn\nAvailable\nUnavailable"
    }
  ],

  onload(report) {
    frappe.set_redirect_to_ag_report();
  },

  set_gridOptions(gridOptions) {
    let me = this;
    set_column_defs(gridOptions);
    gridOptions.tooltipShowDelay = 200;
    gridOptions.tooltipShowDelay = 100;
    gridOptions.floatingFilter = false;
    gridOptions.defaultColDef = defaultColDef;
    gridOptions.context = { always_recreate: true };
    gridOptions.rowSelection = "multiple";
    gridOptions.onRowDataChanged = function(params) {};
    gridOptions.onCellClicked = get_reservation_details;

    gridOptions.onCellDoubleClicked = function(params) {
      if (params.colDef.colId == "room_status") {
        set_room_status(params);
      } else {
        open_reservation(params);
      }
    };

    gridOptions.components = {
      // customTooltip: CustomTooltip
    };

    // gridOptions.getContextMenuItems = get_context_menu;
  }
};

//
const defaultColDef = {
  sortable: true,
  resizable: true
  // tooltipComponent: "customTooltip"
};

//
function set_column_defs(gridOptions) {
  for (let c of gridOptions.columnDefs) {
    if (c.colId == "room_status") {
      c.cellRenderer = function(params) {
        let icon =
          {
            occupied: "suitcase",
            dirty: "paint-brush",
            available: "check",
            unavailable: "minus-circle"
          }[frappe.scrub(params.value || "")] || "genderless";
        return `<i class="fa fa-${icon}"></i>`;
      };
    }

    c.headerClass = function(params) {
      console.log(params.colDef.day_type);
      return `ag-header-${params.colDef.day_type}`;
    };
    // c.tooltip = function(params) { return `<p>305</p>`; };
    c.cellClass = function(params) {
      return (
        (moment().diff(c.colId, "days") > 0 ? "hms-disabled " : "") +
        (params.data[`${c.field}_css`] || "")
      );
    };
  }
}

//
function open_reservation(params) {
  let data = params.data,
    date = params.colDef.colId;

  console.log(data);

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
    cur_frm.set_value(
      "customer",
      frappe.defaults.get_user_default("default_ngtd_customer")
    );
    cur_frm.set_value("check_in_cf", date);
    cur_frm.set_value("room_no_cf", data["name"]);
  });
}

function set_room_status(params) {
  frappe.prompt(
    [
      {
        label: __("Status"),
        fieldname: "status_action",
        fieldtype: "Select",
        options: [
          { label: __("Dirty"), value: "set_dirty" },
          { label: __("Clean"), value: "cleaned" }
        ]
      }
    ],
    data => {
      console.log(data);

      return frappe.call({
        method: "hms.hms.report.frontdesk_hms.frontdesk_hms.set_room_status",
        args: {
          room_no: params.data.name,
          status_action: data.status_action
        },
        callback: function(r) {
          frappe.ag_report.refresh();
        }
      });
    }
  );
}

function get_reservation_details(params) {
  if (params.colDef.day_type == undefined) {
    return;
  }

  return frappe.call({
    method: "hms.hms.controllers.reservation.get_reservation_details",
    args: {
      date: params.colDef.colId,
      room_no: params.data.name
    },
    callback: function(r) {
      console.log(r.message);
      if ($.isEmptyObject(r.message)) {
        return;
      }
      let info = frappe.render(info_template, r.message);
      console.log(info);
      frappe.msgprint(info, (title = r.message.customer));
    }
  });
}

const info_template = `
<div>
   {% include "hms/templates/includes/frontdesk_hms_reservation_info.html" %}
</div>
`;
