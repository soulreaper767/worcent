import frappe

sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.body_class = "worcent-tools"
	context.challenges = frappe.get_all(
		"Skill Challenge",
		fields=["title", "slug", "description", "total_days", "enrolled_count"],
		order_by="title asc",
	)
