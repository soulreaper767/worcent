import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import flt


class WalletTopUp(Document):
	def autoname(self):
		set_name_by_naming_series(self)

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
