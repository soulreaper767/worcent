import frappe
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import flt


class AdvanceRequest(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def on_update(self):
		if self.status == "Disbursed" and self.has_value_changed("status"):
			self.disburse()

	def disburse(self):
		from worcent.worcent_core.wallet_utils import ensure_wallet

		wallet_name = ensure_wallet("Freelancer Profile", self.freelancer)
		wallet = frappe.get_doc("Wallet", wallet_name)
		wallet.balance = flt(wallet.balance) + flt(self.amount_requested)
		wallet.save(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "Wallet Transaction",
				"wallet": wallet.name,
				"transaction_type": "Advance",
				"direction": "Credit",
				"amount": self.amount_requested,
				"balance_after": wallet.balance,
				"reference_doctype": "Advance Request",
				"reference_name": self.name,
			}
		).insert(ignore_permissions=True)
