from __future__ import unicode_literals
from frappe import _
import frappe


def get_data():
    roles = frappe.get_roles()
    config = [
        {
            "label": _("Documents"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Sales Order",
                    "label": "Reservation",
                    "description": "Reservation"
                },
                {
                    # "type": "link",
                    # "doctype": "Energy Point Log",
                    # "label": _("Energy Point Leaderboard"),
                    # "route": "#social/users"

                    "type": "link",
                    "module_name": "hms",
                    "label": _("Frontdesk"),
                    # "route": "#social/users"
                    "route": "#ag-report/Frontdesk HMS"
                },
                # {
                #     "type": "report",
                #     "is_query_report": True,
                #     # "name": "Frontdesk HMS",
                #     "label": "New Frontdesk HMS",
                #     "doctype": "Room Folio HMS"
                # },

            ]
        },
        {
            "label": _("Setup"),
            "items": [{
                "type": "doctype",
                "name": "Room Folio HMS",
                "label": "Room Folio",
                "description": "Room Folio"
            },
                {
                "type": "doctype",
                "name": "Room HMS",
                "label": "Rooms",
                "description": "Rooms"
                # "condition": frappe.utils.has_common(["EDMS_Admin", "System Manager"], frappe.get_roles())
            },
            ]
        },
        {
            "label": _("Standard Reports"),
            "items": [
                # {
                #     "type": "report",
                #     "name": "Entity Summary",
                #     "label": "Entity Master Report",
                #     "is_query_report": True
                # }, {
                #     "type": "report",
                #     "name": "File Sync",
                #     "label": "File Sync Report",
                #     "is_query_report": True,
                #     "condition": frappe.utils.has_common(["EDMS_Admin", "System Manager"], frappe.get_roles())
                # }, {
                #     "type": "report",
                #     "name": "Folder Sync",
                #     "label": "Folder Sync Report",
                #     "is_query_report": True,
                #     "condition": frappe.utils.has_common(["EDMS_Admin", "System Manager"], frappe.get_roles())
                # }, {
                #     "type": "report",
                #     "name": "Master Search",
                #     "label": "Master Search Report",
                #     "is_query_report": True
                # }
            ]
        }
    ]
    return config
