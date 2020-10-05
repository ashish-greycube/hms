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
                    "name": "Frontdesk HMS",
                    "type": "report",
                    "module_name": "hms",
                    "label": _("Frontdesk"),
                    "route": "#ag-report/Frontdesk HMS"
                },
                {
                    "type": "doctype",
                    "name": "Sales Order",
                    "label": "Reservation",
                    "description": "Reservation"
                },
                {
                    "type": "doctype",
                    "name": "Room Folio HMS",
                    "label": "Room Folio",
                    "description": "Room Folio"
                },
                {
                    "name": "Night-Audit",
                    "type": "report",
                    "module_name": "hms",
                    "label": _("Night Audit"),
                    "route": "#ag-report/Night-Audit"
                },
            ]
        },
        {
            "label": _("Setup"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Customer",
                    "label": "Customer",
                    "description": "Customer"
                    # "condition": frappe.utils.has_common(["", "System Manager"], frappe.get_roles())
                },
                {
                    "type": "doctype",
                    "name": "Contact",
                    "label": "Guest",
                    "description": "Guest"
                    # "condition": frappe.utils.has_common(["", "System Manager"], frappe.get_roles())
                },
                {
                    "type": "doctype",
                    "name": "Room HMS",
                    "label": "Rooms",
                    "description": "Rooms"
                    # "condition": frappe.utils.has_common(["", "System Manager"], frappe.get_roles())
                },
                {
                    "type": "doctype",
                    "name": "Room Type HMS",
                    "label": "Room Type",
                    "description": "Room Type"

                },
                {
                    "type": "doctype",
                    "name": "Date Lookup HMS",
                    "label": "Date Lookup",
                    "description": "Date Lookup"
                }
            ]
        },
        {
            "label": _("Standard Reports"),
            "items": [
                {
                    "type": "report",
                    "name": "Guest History HMS",
                    "label": "Guest History",
                    "is_query_report": True,
                },
                {
                    "name": "Room Occupancy and Revenue HMS",
                    "type": "report",
                    "module_name": "hms",
                    "label": _("Room Occupancy and Revenue"),
                    "route": "#ag-report/Room Occupancy and Revenue HMS"
                },
            ]
        }
    ]
    return config
