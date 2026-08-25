import frappe

sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.body_class = "worcent-tools"
	context.countries = frappe.get_all("Country", pluck="name", order_by="name asc")
