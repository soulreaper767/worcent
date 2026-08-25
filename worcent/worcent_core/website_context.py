import frappe


def update_context(context):
	context["worcent_brand"] = {"brand_name": "Worcent"}
	context["worcent_whatsapp_number"] = frappe.db.get_single_value("Worcent Settings", "whatsapp_support_number") or "15550100"
	context["worcent_support_email"] = frappe.db.get_single_value("Worcent Settings", "support_email") or "support@worcent.test"

	if frappe.session.user != "Guest":
		context["worcent_freelancer_profile"] = frappe.db.get_value(
			"Freelancer Profile", {"user": frappe.session.user}, "name"
		)
		context["worcent_employer_profile"] = frappe.db.get_value(
			"Employer Profile", {"user": frappe.session.user}, "name"
		)
