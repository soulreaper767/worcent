import frappe

sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.title = "Browse Gigs"

	category = frappe.form_dict.get("category")
	search = frappe.form_dict.get("search")

	context.categories = frappe.get_all(
		"Skill Category", fields=["name", "category_name"], order_by="category_name asc"
	)
	context.selected_category = category
	context.search = search

	active_freelancers = frappe.get_all("Freelancer Profile", filters={"status": ["!=", "Suspended"]}, pluck="name")

	filters = {"published": 1, "status": "Active", "freelancer": ["in", active_freelancers]}
	if category:
		filters["category"] = category
	if search:
		filters["title"] = ["like", f"%{search}%"]

	gigs = frappe.get_all(
		"Gig",
		filters=filters,
		fields=["name", "title", "route", "freelancer", "description"],
		order_by="creation desc",
		limit_page_length=48,
	)
	for gig in gigs:
		gig["freelancer_name"] = frappe.db.get_value("Freelancer Profile", gig.freelancer, "display_name")
		prices = frappe.get_all("Gig Package", filters={"parent": gig.name}, pluck="price")
		gig["starting_price"] = min(prices) if prices else None
	context.gigs = gigs
