import frappe

sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.body_class = "worcent-tools"
