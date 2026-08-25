import frappe

sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.body_class = "worcent-join"
	if frappe.session.user != "Guest":
		frappe.local.flags.redirect_location = "/app"
		raise frappe.Redirect

	context.countries = frappe.get_all("Country", pluck="name", order_by="name asc")
	requested_type = (frappe.form_dict.get("type") or "freelancer").strip().lower()
	context.account_type = "Employer" if requested_type == "employer" else "Freelancer"
	context.referral_code = frappe.form_dict.get("ref") or ""
