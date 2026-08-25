import frappe

sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.title = "Browse Jobs"

	category = frappe.form_dict.get("category")
	budget_type = frappe.form_dict.get("budget_type")
	search = frappe.form_dict.get("search")

	context.categories = frappe.get_all(
		"Skill Category", fields=["name", "category_name"], order_by="category_name asc"
	)
	context.selected_category = category
	context.selected_budget_type = budget_type
	context.search = search

	filters = {"published": 1, "status": "Open"}
	if category:
		filters["category"] = category
	if budget_type:
		filters["budget_type"] = budget_type
	if search:
		filters["title"] = ["like", f"%{search}%"]

	context.jobs = frappe.get_all(
		"Job Posting",
		filters=filters,
		fields=["name", "title", "route", "employer", "budget_type", "budget_min", "budget_max", "description", "proposals_count"],
		order_by="creation desc",
		limit_page_length=48,
	)
	for job in context.jobs:
		job["employer_name"] = frappe.db.get_value("Employer Profile", job.employer, "company_name")
