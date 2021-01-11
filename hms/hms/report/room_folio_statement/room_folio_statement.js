// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Room Folio Statement"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("From"),
      fieldtype: "Date",
      default: frappe.defaults.get_default("year_start_date"),
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
      default: frappe.defaults.get_user_default("company"),
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
      options: ["", "Checked In", "Checked Out", "Cancelled"],
      default: "Checked In",
    },
    {
      fieldname: "room_folio",
      label: __("Room Folio"),
      fieldtype: "Link",
      options: "Room Folio HMS",
    },
  ],

  onload(report) {
    frappe.set_redirect_to_ag_report();
    set_print_folio_statement(report);
  },

  after_refresh(report) {
    let totals = report.data.slice(-1);
    let balance = totals.length
      ? (totals[0].credit || 0) - (totals[0].debit || 0)
      : 0;
    let html = `<span style="font-weight:bold;font-size:14px;color:${
      balance < 0 ? "red" : "green"
    }">Account Balance: ${format_currency(balance)}</span>`;
    $(".ag-header-message").html(html);
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
    gridOptions.getRowStyle = function (params) {
      return params.data.voucher_type == "Payment Entry"
        ? {
            "background-color": "#def8de",
          }
        : null;
    };

    for (let col of gridOptions.columnDefs) {
      if (col.colId == "voucher_no")
        col.cellRenderer = function (params) {
          return params.data.voucher_type
            ? `<a href='#Form/${params.data.voucher_type}/${params.value}' target="_blank">${params.value}</a>`
            : "";
        };
    }

    //
  },
};

function set_print_folio_statement(report) {
  report.page.page_actions
    .find("li > a.grey-link span[data-label='Print']")
    .parent()
    .remove();
  report.page.add_menu_item(
    "Print",
    () => {
      let docname = report.get_filter_value("room_folio");
      if (!docname) {
        let selection = report.get_selected_rows_after_filter(
          "Please select a folio to Print.",
          true
        );
        docname = selection[0].folio;
      }
      if (!docname) {
        frappe.throw("Please select a folio to Print.");
      }
      var w = window.open(
        frappe.urllib.get_full_url(
          `/api/method/frappe.utils.print_format.download_pdf?doctype=Room Folio HMS&name=${docname}&format=Folio Summary&no_letterhead=0`
        )
      );
      if (!w) {
        frappe.msgprint(__("Please enable pop-ups"));
        return;
      }
    },
    false
  );
}
