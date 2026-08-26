import frappe


def extend_bootinfo(bootinfo):
	if frappe.session.user == "Guest":
		return

	freelancer = frappe.db.get_value("Freelancer Profile", {"user": frappe.session.user}, "name")
	employer = frappe.db.get_value("Employer Profile", {"user": frappe.session.user}, "name")

	bootinfo.worcent_dual_role = {
		"is_freelancer": bool(freelancer),
		"is_employer": bool(employer),
	}
