// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
frappe.listview_settings["Room Folio HMS"] = {
  hide_name_column: true,
  get_indicator: function (doc) {
    var status_color = {
      "Pre-Check In": "orange",
      "Checked In": "blue",
      "Checked Out": "green",
    };
    return [__(doc.status), status_color[doc.status], "status,=," + doc.status];
  },
  right_column: "status",
};
