import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import flt


class WalletTopUp(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		if self.is_new() and frappe.session.user != "Administrator" and "Worcent Admin" not in frappe.get_roles():
			self._resolve_own_wallet()

	def _resolve_own_wallet(self):
		"""A Freelancer/Employer topping up their own wallet shouldn't need to
		already know their Wallet doc's name -- it may not even exist yet for
		a brand new account (Wallets are created lazily on first use). Force
		self.wallet to their own, creating it if needed, rather than trusting
		whatever they picked."""
		from worcent.worcent_core.wallet_utils import ensure_wallet

		freelancer = frappe.db.get_value("Freelancer Profile", {"user": frappe.session.user}, "name")
		employer = frappe.db.get_value("Employer Profile", {"user": frappe.session.user}, "name")

		if self.wallet:
			owner = frappe.db.get_value("Wallet", self.wallet, "party")
			if owner not in (freelancer, employer):
				frappe.throw(_("You can only top up your own wallet."))
			return

		if freelancer:
			self.wallet = ensure_wallet("Freelancer Profile", freelancer)
		elif employer:
			self.wallet = ensure_wallet("Employer Profile", employer)
		else:
			frappe.throw(_("No Freelancer or Employer profile found for your account."))

	def on_update(self):
		if self.status == "Approved" and self.has_value_changed("status"):
			self.credit_wallet()

	def credit_wallet(self):
		if not self.approved_by:
			self.db_set("approved_by", frappe.session.user)

		wallet = frappe.get_doc("Wallet", self.wallet)
		wallet.balance = flt(wallet.balance) + flt(self.amount)
		wallet.save(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "Wallet Transaction",
				"wallet": self.wallet,
				"transaction_type": "Top Up",
				"direction": "Credit",
				"amount": self.amount,
				"balance_after": wallet.balance,
				"reference_doctype": "Wallet Top Up",
				"reference_name": self.name,
				"remarks": self.reference_note,
			}
		).insert(ignore_permissions=True)

		from worcent.worcent_finance.accounting_engine import record_topup

		record_topup(wallet.party_type, wallet.party, self.amount, "Wallet Top Up", self.name)
