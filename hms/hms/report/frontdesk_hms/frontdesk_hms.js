// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

function CustomTooltip() {}

CustomTooltip.prototype.init = function(params) {
  var eGui = (this.eGui = document.createElement("div"));
  var color = params.color || "white";
  var data = params.api.getDisplayedRowAtIndex(params.rowIndex).data;
  eGui.classList.add("custom-tooltip");
  // eGui.style["background-color"] = color;
  eGui.innerHTML = "hello there";
  // '<p><span class"name">' +
  // data.athlete +
  // "</span></p>" +
  // "<p><span>Country: </span>" +
  // data.country +
  // "</p>" +
  // "<p><span>Total: </span>" +
  // data.total +
  // "</p>";
};

CustomTooltip.prototype.getGui = function() {
  return this.eGui;
};

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
      customTooltip: CustomTooltip
    };

    // gridOptions.getContextMenuItems = get_context_menu;
  }
};

//
const defaultColDef = {
  sortable: true,
  resizable: true,
  tooltipComponent: "customTooltip"
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
    cur_frm.set_value("customer", "Dummy Customer");
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

      let info = frappe.render_template(info_template, r.message);
      frappe.msgprint(info, (title = r.message.customer));
    }
  });
}

const info_template = `
<table class="table table-bordered">
  <tbody>
    <tr><td>Customer</td><td>{{customer}}</td></tr>
    <tr><td>Guest</td><td>guest</td></tr>
    <tr><td>Contact No:</td><td>mobile</td></tr>
    <tr><td>Room #</td><td>room_no</td></tr>
    <tr><td>R</td><td>rate</td></tr>
    <tr><td>WNR</td><td>weekend_rate</td></tr>
    <tr><td>Total Nights</td><td>total_nights</td></tr>
    <tr><td>Total Stay Cost</td><td>total_stay_cost</td></tr>
    <tr><td>Advance</td><td>advance</td></tr>
	</tbody>
</table>
`;
