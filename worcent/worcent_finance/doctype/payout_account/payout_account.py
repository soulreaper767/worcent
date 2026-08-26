import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series


class PayoutAccount(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		self.enforce_ownership()
		if self.account_type == "Bank Transfer" and not (self.account_number or self.iban):
			frappe.throw(_("Enter an Account Number or IBAN for a Bank Transfer payout account."))
		if self.account_type == "PayPal" and not self.paypal_email:
			frappe.throw(_("Enter a PayPal email for a PayPal payout account."))
		if self.is_default:
			self.unset_other_defaults()
		self.set_default_currency()
		self.set_title()

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

	def set_default_currency(self):
		if self.currency:
			return
		preferred = frappe.db.get_value(self.party_type, self.party, "preferred_currency")
		if preferred:
			self.currency = preferred
			return
		from worcent.worcent_finance.currency_utils import get_currency_for_country

		country = frappe.db.get_value(self.party_type, self.party, "country")
		self.currency = get_currency_for_country(country)

	def set_title(self):
		name_field = "display_name" if self.party_type == "Freelancer Profile" else "company_name"
		party_label = frappe.db.get_value(self.party_type, self.party, name_field)
		if self.account_type == "Bank Transfer":
			tail_source = self.account_number or self.iban or ""
			masked = f"****{tail_source[-4:]}" if len(tail_source) >= 4 else tail_source
			detail = " - ".join(part for part in [self.bank_name, masked] if part)
		elif self.account_type == "PayPal":
			detail = self.paypal_email or ""
		else:
			detail = self.other_method_label or ""

		self.title = " - ".join(part for part in [self.account_type, detail, party_label] if part)
