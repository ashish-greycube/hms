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
                    "route": "#ag-report/Frontdesk HMS",
                },
                {
                    "type": "doctype",
                    "name": "Sales Order",
                    "label": "Reservation",
                    "description": "Reservation",
                },
                {
                    "type": "doctype",
                    "name": "Room Folio HMS",
                    "label": "Room Folio",
                    "description": "Room Folio",
                },
                {
                    "type": "doctype",
                    "name": "Sign In Sheet HMS",
                    "label": "Sign In Sheet",
                    "description": "Sign In Sheet",
                },
                {
                    "type": "doctype",
                    "name": "Laundry HMS",
                    "label": "Laundry",
                    "description": "Laundry Entries",
                },
                {
                    "type": "doctype",
                    "name": "Online Booking HMS",
                    "label": "Online Booking",
                    "description": "Website Online Booking",
                },
                {
                    "type": "page",
                    "name": "pos",  # have to use pos, because of moduleview.filter_by_restrict_to_domain
                    "label": _("Point Of Sale"),
                },
                {
                    "name": "Night-Audit",
                    "type": "report",
                    "module_name": "hms",
                    "label": _("Night Audit"),
                    "route": "#ag-report/Night-Audit",
                },
            ],
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
                    "description": "Room Type",
                },
                {
                    "type": "doctype",
                    "name": "Date Lookup HMS",
                    "label": "Date Lookup",
                    "description": "Date Lookup",
                },
            ],
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
                    "route": "#ag-report/Room Occupancy and Revenue HMS",
                },
                # {
                #     "name": "Room Folio Statement",
                #     "type": "report",
                #     "module_name": "hms",
                #     "label": _("Room Folio Statement"),
                #     "route": "#ag-report/Room Folio Statement",
                # },
                {
                    "name": "Rooms To Checkout",
                    "type": "report",
                    "module_name": "hms",
                    "label": _("Rooms To Checkout"),
                    "route": "#ag-report/Rooms To Checkout",
                },
                {
                    "name": "Shift Report",
                    "type": "report",
                    "module_name": "hms",
                    "label": _("Shift Report"),
                    "route": "#query-report/Shift Report",
                },
                {
                    "name": "Complimentary Item Sales",
                    "type": "report",
                    "module_name": "hms",
                    "label": _("Complimentary Item Sales"),
                    "route": "#ag-report/Complimentary Item Sales",
                },
                {
                    "name": "Restaurant Chef Report",
                    "type": "report",
                    "module_name": "hms",
                    "label": _("Restaurant Chef Report"),
                    "route": "#ag-report/Restaurant Chef Report",
                },
            ],
        },
    ]
    return config
