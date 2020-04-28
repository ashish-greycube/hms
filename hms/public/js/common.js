frappe.provide("hms");

hms.make_grid_room_folio_advance = function (frm) {
  let $wrapper = frm.fields_dict["room_folio_advance"].$wrapper;
  $wrapper
    .empty()
    .html(
      `<div id="ag-room-folio-advance" class="ag-theme-balham" style="width:100%;height:150px;;"></div>`
    );
  frm.room_folio_advance_gridOptions = {
    columnDefs: [
      { headerName: "Reference Type", field: "reference_type", width: 160 },
      {
        headerName: "Reference Name",
        field: "reference_name",
        width: 160,
        cellRenderer: function (params) {
          return `<a href='#Form/${params.data.reference_type}/${params.value}' target="_blank">${params.value}</a>`;
        },
      },
      { headerName: "Posting Date", field: "posting_date", width: 100 },
      { headerName: "Amount", field: "amount", width: 100 },
      { headerName: "Allocated Amount", field: "allocated_amount", width: 100 },
    ],
    rowData: [],
    components: {
      customNoRowsOverlay: CustomNoRowsOverlay,
    },
    noRowsOverlayComponent: "customNoRowsOverlay",
    noRowsOverlayComponentParams: {
      noRowsMessageFunc: function () {
        return !frm.doc.master_folio
          ? "No advance payments made"
          : "Please check master folio for advances";
      },
    },
  };

  var gridDiv = document.querySelector("#ag-room-folio-advance");
  new agGrid.Grid(gridDiv, frm.room_folio_advance_gridOptions);
};

hms.make_grid_charge_and_purchase = function (frm) {
  let $wrapper = frm.fields_dict["sales_invoice_reference"].$wrapper;
  $wrapper
    .empty()
    .html(
      `<div id="charge-purchase" class="ag-theme-balham" style="width:100%;height:150px;;"></div>`
    );
  frm.gridOptions = {
    columnDefs: [
      {
        headerName: "Invoice",
        field: "name",
        width: 160,
        cellRenderer: function (params) {
          return `<a href='#Form/Sales Invoice/${params.value}' target="_blank">${params.value}</a>`;
        },
      },
      {
        headerName: "Folio",
        field: "room_folio",
        width: 160,
        cellRenderer: function (params) {
          return `<a href='#Form/Room Folio HMS/${params.value}' target="_blank">${params.value}</a>`;
        },
      },
      { headerName: "Room", field: "room_no", width: 90 },
      { headerName: "Date", field: "room_date_cf", width: 90 },
      { headerName: "Time", field: "posting_time", width: 90 },
      { headerName: "Total", field: "rounded_total", width: 90 },
      { headerName: "Outstanding", field: "outstanding_amount" },
    ],
    rowData: [],
  };
  var gridDiv = document.querySelector("#charge-purchase");
  new agGrid.Grid(gridDiv, frm.gridOptions);
};

frappe.provide("hms.utils");
hms.utils.toggle_selection = function (report) {
  const rows = report.gridOptions.api.getSelectedRows();
  if (rows.length > 0) report.gridOptions.api.deselectAll();
  else report.gridOptions.api.selectAll();
};

hms.utils.pick = function (o, ...props) {
  return Object.assign({}, ...props.map((prop) => ({ [prop]: o[prop] })));
};

function CustomNoRowsOverlay() {}

CustomNoRowsOverlay.prototype.init = function (params) {
  this.eGui = document.createElement("div");
  this.eGui.innerHTML =
    '<div class="ag-overlay-loading-center" style="background-color: lightcoral;">' +
    '   <i class="far fa-frown"> ' +
    params.noRowsMessageFunc() +
    " </i>" +
    "</div>";
};

CustomNoRowsOverlay.prototype.getGui = function () {
  return this.eGui;
};
