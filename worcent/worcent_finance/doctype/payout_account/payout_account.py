import frappe
from frappe import _
from frappe.model.document import Document


class PayoutAccount(Document):
	def validate(self):
		self.enforce_ownership()
		if self.account_type == "Bank Transfer" and not (self.account_number or self.iban):
			frappe.throw(_("Enter an Account Number or IBAN for a Bank Transfer payout account."))
		if self.account_type == "PayPal" and not self.paypal_email:
			frappe.throw(_("Enter a PayPal email for a PayPal payout account."))
		if self.is_default:
			self.unset_other_defaults()

	def enforce_ownership(self):
		if frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles():
			return
		owner_user = frappe.db.get_value(self.party_type, self.party, "user")
		if owner_user != frappe.session.user:
			frappe.throw(_("You can only manage your own payout accounts."))

	def unset_other_defaults(self):
		frappe.db.set_value(
			"Payout Account",
			{"party_type": self.party_type, "party": self.party, "name": ["!=", self.name]},
			"is_default",
			0,
		)
