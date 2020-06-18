frappe.pages["point-of-sale"].refresh = function (wrapper) {
  if (this.page.wrapper.find(".list-folio-btn").length === 0) {
    $(`<button class="btn btn-default list-folio-btn" style="margin-left: 12px">
          <i class="octicon octicon-key"></i>
      </button>`).prependTo(wrapper.page.page_actions);

    $(wrapper).on("click", ".list-folio-btn", function () {
      if (!wrapper.pos.dialog) make_folio_dialog(wrapper.pos);
      wrapper.pos.dialog.show();
      get_folios(wrapper.pos);
    });
  }

  if (wrapper.pos) {
    wrapper.pos.make_new_invoice();
  }

  if (frappe.flags.is_offline) {
    frappe.set_route("pos");
  }
};

function get_folios(pos) {
  frappe.call({
    method: "hms.hms.controllers.reservation.get_checked_in_folios",
    args: {},
    callback: function (r) {
      pos.gridOptions.api.setRowData(r.message);
    },
  });
}

function make_folio_dialog(pos) {
  pos.dialog = new frappe.ui.Dialog({
    title: __("Select Folio & Customer"),
    size: "large",
    fields: [
      {
        fieldtype: "Button",
        fieldname: "grid_btn",
        label: __("Clear Filter"),
        click: function () {
          pos.gridOptions.api.setFilterModel({});
          pos.dialog.hide();
        },
      },
      {
        fieldtype: "HTML",
        fieldname: "grid_html",
      },
    ],
  });

  let body = pos.dialog.fields_dict["grid_html"].$wrapper;
  body.html(
    `
      <p>Double click on item to select.</p>
      <div id="ag-items" class="ag-theme-balham" style="width:100%;height:350px;;"></div>
      `
  );

  pos.gridOptions = {
    columnDefs: [
      {
        field: "customer",
        headerName: "Customer",
        width: 150,
      },
      {
        field: "room_type",
        headerName: "Room Type",
        width: 90,
      },
      {
        field: "room_no",
        headerName: "Room No",
        width: 90,
      },
      {
        field: "check_in",
        headerName: "Check In",
        width: 90,
      },
      {
        field: "check_out",
        headerName: "Check Out",
        width: 90,
      },
      {
        field: "balance",
        headerName: "Balance",
        type: "numericColumn",
        width: 90,
      },
      {
        field: "folio",
        headerName: "Folio",
        type: "Link/Room Folio HMS",
        width: 120,
      },
    ],
    onGridReady: function () {
      get_folios(pos);
    },
  };

  pos.gridOptions.rowSelection = "single";
  pos.gridOptions.floatingFilter = true;

  pos.gridOptions.onCellDoubleClicked = function (params) {
    pos.dialog.hide();

    let folio = params.api.getSelectedRows()[0],
      customer = folio["customer"];

    pos.frm.doc.room_folio_cf = folio["folio"];
    pos.cart.customer_field.set_value(customer);
  };

  pos.gridDiv = body.find("#ag-items");
  new agGrid.Grid(pos.gridDiv.get(0), pos.gridOptions);
}
