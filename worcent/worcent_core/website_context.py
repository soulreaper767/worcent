import frappe


def update_context(context):
	context["worcent_brand"] = {"brand_name": "Worcent"}
	if frappe.session.user != "Guest":
		context["worcent_freelancer_profile"] = frappe.db.get_value(
			"Freelancer Profile", {"user": frappe.session.user}, "name"
		)
		context["worcent_employer_profile"] = frappe.db.get_value(
			"Employer Profile", {"user": frappe.session.user}, "name"
		)
