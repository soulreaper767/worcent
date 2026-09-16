import frappe

sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.title = "Messages"

	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/messages"
		raise frappe.Redirect

	from worcent.worcent_core.permissions import get_employer_profile, get_freelancer_profile

	if not get_freelancer_profile(frappe.session.user) and not get_employer_profile(frappe.session.user):
		frappe.local.flags.redirect_location = "/"
		raise frappe.Redirect
