import frappe


def execute():
	frappe.reload_doc("worcent_core", "doctype", "skill_category")

	from worcent.worcent_core.service_categories import seed_service_categories

	seed_service_categories()
