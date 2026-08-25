import frappe

sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.body_class = "worcent-home"

	context.categories = frappe.get_all(
		"Skill Category", fields=["name", "category_name"], order_by="category_name asc", limit_page_length=8
	)

	context.featured_freelancers = frappe.get_all(
		"Freelancer Profile",
		filters={"published": 1, "status": "Active"},
		fields=["name", "display_name", "route", "headline", "profile_photo", "hourly_rate", "rating_avg", "verification_level"],
		order_by="is_guru desc, rating_avg desc",
		limit_page_length=6,
	)

	context.gurus = frappe.get_all(
		"Industry Guru",
		filters={"is_featured": 1},
		fields=["freelancer", "industry"],
		limit_page_length=4,
	)
	for guru in context.gurus:
		profile = frappe.db.get_value(
			"Freelancer Profile", guru.freelancer, ["display_name", "route", "profile_photo", "headline"], as_dict=True
		)
		guru.update(profile or {})

	context.open_jobs = frappe.get_all(
		"Job Posting",
		filters={"published": 1, "status": "Open"},
		fields=["title", "route", "budget_type", "budget_min", "budget_max", "employer"],
		order_by="creation desc",
		limit_page_length=6,
	)
	for job in context.open_jobs:
		job["employer_name"] = frappe.db.get_value("Employer Profile", job.employer, "company_name")

	context.stats = {
		"freelancers": frappe.db.count("Freelancer Profile", {"status": "Active"}),
		"employers": frappe.db.count("Employer Profile", {"status": "Active"}),
		"jobs_posted": frappe.db.count("Job Posting"),
		"countries": len(frappe.db.sql(
			"select distinct country from `tabFreelancer Profile` where country is not null and country != ''"
		)),
	}
