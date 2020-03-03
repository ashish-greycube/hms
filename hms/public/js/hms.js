frappe.provide("hms");

hms.make_grid_charge_and_purchase = function(frm) {
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
};

frappe.provide("hms.utils");
hms.utils.toggle_selection = function(report) {
  const rows = report.gridOptions.api.getSelectedRows();
  if (rows.length > 0) report.gridOptions.api.deselectAll();
  else report.gridOptions.api.selectAll();
};

hms.utils.pick = function(o, ...props) {
  return Object.assign({}, ...props.map(prop => ({ [prop]: o[prop] })));
};
