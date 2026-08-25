import frappe

sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.title = "Browse Freelancers"

	category = frappe.form_dict.get("category")
	verified_only = frappe.form_dict.get("verified")
	search = frappe.form_dict.get("search")

	context.categories = frappe.get_all(
		"Skill Category", fields=["name", "category_name"], order_by="category_name asc"
	)
	context.selected_category = category
	context.verified_only = verified_only
	context.search = search

	filters = {"published": 1, "status": "Active"}
	if verified_only:
		filters["verification_level"] = ["in", ["ID Verified", "Business Verified"]]
	if search:
		filters["headline"] = ["like", f"%{search}%"]

	freelancer_names = None
	if category:
		skill_names = frappe.get_all("Skill", filters={"category": category}, pluck="name")
		if skill_names:
			freelancer_names = frappe.get_all(
				"Freelancer Skill", filters={"skill": ["in", skill_names]}, pluck="parent"
			)
		else:
			freelancer_names = []
		filters["name"] = ["in", freelancer_names or [""]]

	context.freelancers = frappe.get_all(
		"Freelancer Profile",
		filters=filters,
		fields=[
			"name", "display_name", "route", "headline", "profile_photo", "hourly_rate",
			"rating_avg", "total_reviews", "verification_level", "availability",
		],
		order_by="is_guru desc, is_mentor desc, rating_avg desc",
		limit_page_length=48,
	)

	for f in context.freelancers:
		f["skills"] = frappe.get_all("Freelancer Skill", filters={"parent": f.name}, fields=["skill"], limit_page_length=5)
