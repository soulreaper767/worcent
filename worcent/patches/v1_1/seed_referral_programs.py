import frappe


def execute():
	frappe.reload_doc("worcent_finance", "doctype", "referral_program")
	frappe.reload_doc("worcent_finance", "doctype", "referral_code")
	frappe.reload_doc("worcent_finance", "doctype", "referral")

	if not frappe.db.exists("Referral Program", "Standard Referral Program"):
		frappe.get_doc(
			{
				"doctype": "Referral Program",
				"program_name": "Standard Referral Program",
				"is_active": 1,
				"is_default": 1,
				"applies_to": "Both",
				"reward_type": "Percent of First Platform Earning",
				"reward_value": 1,
				"referred_signup_bonus": 5,
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Referral Program", "Launch Promo"):
		frappe.get_doc(
			{
				"doctype": "Referral Program",
				"program_name": "Launch Promo",
				"is_active": 1,
				"is_default": 0,
				"applies_to": "Both",
				"reward_type": "Flat Bonus on First Milestone",
				"reward_value": 15,
				"referred_signup_bonus": 5,
				"validity_days": 60,
			}
		).insert(ignore_permissions=True)

	default_program = frappe.db.get_value("Referral Program", {"is_default": 1}, "name")
	for code_name in frappe.get_all("Referral Code", filters={"program": ["in", ["", None]]}, pluck="name"):
		code = frappe.get_doc("Referral Code", code_name)
		code.program = default_program
		code.save(ignore_permissions=True)
