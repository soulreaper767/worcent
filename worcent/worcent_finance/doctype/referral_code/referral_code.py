import frappe
from frappe.model.document import Document


class ReferralCode(Document):
	def validate(self):
		if not self.program:
			self.program = frappe.db.get_value("Referral Program", {"is_default": 1}, "name")
		if self.program:
			program = frappe.get_cached_doc("Referral Program", self.program)
			self.signup_bonus_referred = program.referred_signup_bonus
			self.commission_percent_referrer = (
				program.reward_value if program.reward_type == "Percent of First Platform Earning" else 0
			)
