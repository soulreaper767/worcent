import frappe

sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.body_class = "worcent-tools"
	context.prefill = {}
	if frappe.session.user != "Guest":
		freelancer = frappe.db.get_value(
			"Freelancer Profile", {"user": frappe.session.user},
			["jobs_completed", "rating_avg"], as_dict=True,
		)
		if freelancer:
			context.prefill = {
				"completed_jobs": freelancer.jobs_completed or 0,
				"rating_avg": freelancer.rating_avg or 0,
			}
