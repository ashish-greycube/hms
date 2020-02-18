// Copyright (c) 2020, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Room Folio HMS", {
  refresh: function(frm) {
    make_grid(frm);
    load_charge_and_purchase(frm);
  }
});

function make_grid(frm) {
  let $wrapper = frm.fields_dict["sales_invoice_reference"].$wrapper;
  $wrapper
    .empty()
    .html(
      `<div id="charge-purchase" class="ag-theme-balham" style="width:100%;height:150px;;"></div>`
    );
  frm.gridOptions = {
    columnDefs: [
      { headerName: "Invoice", field: "name", width: 120 },
      { headerName: "Date", field: "posting_date", width: 90 },
      { headerName: "Time", field: "posting_time", width: 90 },
      { headerName: "Total", field: "rounded_total" },
      { headerName: "Outstanding", field: "outstanding_amount" }
    ],
    rowData: []
  };
  var gridDiv = document.querySelector("#charge-purchase");
  new agGrid.Grid(gridDiv, frm.gridOptions);
}

function load_charge_and_purchase(frm) {
  return frappe.call({
    method:
      "hms.hms.doctype.room_folio_hms.room_folio_hms.get_charge_and_purchase",
    args: { docname: frm.doc.name },
    callback: function(r) {
      if (r.message) {
        console.log(r.message);

        frm.gridOptions.api.setRowData(r.message);
      }
    }
  });
}
