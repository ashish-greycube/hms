// Copyright (c) 2020, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sign In Sheet HMS", {
  refresh: function (frm) {
    frm.page.add_inner_button(__("Room Folio"), function (params) {
      // let docname = frm.doc.content
      //   .match(/<small>(.*?)<\/small>/g)[0]
      //   .replace(/(<([^>]+)>)/gi, "");
      frappe.set_route("Form", "Room Folio HMS", frm.doc.folio);
    });
  },
});
