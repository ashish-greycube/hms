frappe.pages["pos"].refresh = function (wrapper) {


  setTimeout(() => {
    // 
    // Customization to handle 0 payment amount when charging POS to room folio.
    // 
    let payment = cur_pos.payment;
    payment.$component.off('click').on('click', '.submit-order-btn', () => {
      const doc = payment.events.get_frm().doc;
      const paid_amount = doc.paid_amount;
      const items = doc.items;

      if (!doc.room_folio_cf) {
        if (paid_amount == 0 || !items.length) {
          const message = items.length ? __("You can submit the order without payment.") : __("You cannot submit empty order.");
          frappe.show_alert({ message, indicator: "orange" });
          frappe.utils.play_sound("error");
          return;
        }
      } else {
        if (paid_amount == 0) {
          const message = `This order will be charged to Folio: ${doc.room_folio_cf}`;
          frappe.show_alert({ message, indicator: "orange" });
        } else {
          const message = `Set amount to 0 to be charge order to Room Folio.`;
          frappe.show_alert({ message, indicator: "orange" });
          frappe.utils.play_sound("error");
          return;
        }
      }

      payment.events.submit_invoice();
    });

  }, 600);


  if (this.page.wrapper.find(".list-folio-btn").length === 0) {
    $(`<button class="btn btn-default list-folio-btn" style="margin-left: 12px">
        <i class="octicon octicon-key"></i>
    </button>`).prependTo(wrapper.page.page_actions);

    $(wrapper).on("click", ".list-folio-btn", function () {
      if (!wrapper.pos.folio_dialog) make_folio_dialog(wrapper.pos);
      wrapper.pos.folio_dialog.show();
      get_folios(wrapper.pos);

      // if (!wrapper.pos.is_monkey_patched) {
      //   wrapper.pos.is_monkey_patched = true;
      //   var original = wrapper.pos.submit_sales_invoice;
      //   wrapper.pos.submit_sales_invoice = function () {
      //     if (
      //       wrapper.pos.frm.doc.room_folio_cf &&
      //       wrapper.pos.frm.doc.paid_amount > 0
      //     ) {
      //       let mop = wrapper.pos.frm.doc.payments[0].mode_of_payment;
      //       wrapper.pos.payment.update_payment_value(mop, 0);
      //     }
      //     original.apply(this, arguments);
      //   };
      // }
    });
  }

  window.onbeforeunload = function () {
    return wrapper.pos.beforeunload();
  };

  if (frappe.flags.is_online) {
    frappe.set_route("point-of-sale");
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
  pos.folio_dialog = new frappe.ui.Dialog({
    title: __("Select Folio & Customer"),
    size: "large",
    fields: [
      {
        fieldtype: "Button",
        fieldname: "grid_btn",
        label: __("Clear Filter"),
        click: function () {
          pos.gridOptions.api.setFilterModel({});
          pos.folio_dialog.hide();
        },
      },
      {
        fieldtype: "HTML",
        fieldname: "grid_html",
      },
    ],
  });

  let body = pos.folio_dialog.fields_dict["grid_html"].$wrapper;
  body.html(
    `
    <p>Double click on an item to select.</p>
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
        field: "folio",
        headerName: "Folio",
        type: "Link/Room Folio HMS",
        width: 180,
      },
    ],
    onGridReady: function () {
      get_folios(pos);
    },

    defaultColDef: {
      sortable: true,
      resizable: true,
    },
  };

  pos.gridOptions.rowSelection = "single";
  pos.gridOptions.floatingFilter = true;

  pos.gridOptions.onCellDoubleClicked = function (params) {
    pos.folio_dialog.hide();

    let folio = params.api.getSelectedRows()[0],
      customer = folio["customer"];

    pos.frm.doc.customer = customer;
    pos.frm.doc.room_folio_cf = folio["folio"];
    pos.set_customer_value_in_party_field();
    pos.party_field.awesomeplete.evaluate();
    pos.party_field.awesomeplete.select();
    debugger;
    pos.frm.doc.debit_to = frappe.defaults.get_user_default(
      "default_folio_receivable_account"
    );
  };

  pos.gridDiv = body.find("#ag-items");
  new agGrid.Grid(pos.gridDiv.get(0), pos.gridOptions);
}
