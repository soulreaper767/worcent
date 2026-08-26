import frappe
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series


class Wallet(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		self.set_title()

	def set_title(self):
		name_field = "display_name" if self.party_type == "Freelancer Profile" else "company_name"
		party_label = frappe.db.get_value(self.party_type, self.party, name_field)
		role = "Freelancer" if self.party_type == "Freelancer Profile" else "Employer"
		self.title = f"{party_label} ({role})" if party_label else f"{role} Wallet"
