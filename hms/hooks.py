# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "hms"
app_title = "HMS"
app_publisher = "GreyCube Technologies"
app_description = "Manage hotel operations: Booking, Pricing, Inventory, Customer Relations, Financials, Point of Sale"
app_icon = "octicon octicon-octoface"
app_color = "red"
app_email = "admin@greycube.in"
app_license = "proprietary"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/hms/css/hms.css"
app_include_js = ["/assets/hms/js/hms.js",
                  "/assets/hms/js/ag_report.js",
                  "/assets/hms/js/lib/ag-grid-community.min.js"
                  ]
app_include_css = "/assets/hms/css/hms.css"

# include js, css files in header of web template
# web_include_css = "/assets/hms/css/hms.css"
# web_include_js = "/assets/hms/js/hms.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_js = {"Sales Order": "public/js/sales_order.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "hms.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "hms.install.before_install"
# after_install = "hms.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "hms.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

on_session_creation = [
    "hms.set_session_defaults"
]
# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

doc_events = {
    "Sales Order": {
        "validate": "hms.hms.controllers.reservation.on_submit_sales_order",
        "on_update_after_submit": "hms.hms.controllers.reservation.on_update_after_submit_sales_order"
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"hms.tasks.all"
# 	],
# 	"daily": [
# 		"hms.tasks.daily"
# 	],
# 	"hourly": [
# 		"hms.tasks.hourly"
# 	],
# 	"weekly": [
# 		"hms.tasks.weekly"
# 	]
# 	"monthly": [
# 		"hms.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "hms.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "hms.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "hms.task.get_dashboard_data"
# }
