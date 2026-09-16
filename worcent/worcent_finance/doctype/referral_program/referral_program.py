import frappe
from frappe.model.document import Document


class ReferralProgram(Document):
	def validate(self):
		if self.is_default:
			frappe.db.set_value(
				"Referral Program", {"is_default": 1, "name": ["!=", self.name or ""]}, "is_default", 0
			)
