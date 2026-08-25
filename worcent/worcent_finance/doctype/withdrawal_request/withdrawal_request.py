import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import flt, now_datetime


class WithdrawalRequest(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		if self.is_new():
			wallet = frappe.get_doc("Wallet", self.wallet)
			if flt(self.amount) > flt(wallet.balance):
				frappe.throw(_("Withdrawal amount exceeds available wallet balance"))
			min_amount = frappe.db.get_single_value("Worcent Settings", "min_withdrawal_amount")
			if min_amount and flt(self.amount) < flt(min_amount):
				frappe.throw(_("Minimum withdrawal amount is {0}").format(min_amount))

	def on_update(self):
		if self.status == "Paid" and self.has_value_changed("status"):
			self.debit_wallet()

	def debit_wallet(self):
		wallet = frappe.get_doc("Wallet", self.wallet)
		wallet.balance = flt(wallet.balance) - flt(self.amount)
		wallet.total_withdrawn = flt(wallet.total_withdrawn) + flt(self.amount)
		wallet.save(ignore_permissions=True)

		self.db_set("paid_on", now_datetime())

		frappe.get_doc(
			{
				"doctype": "Wallet Transaction",
				"wallet": self.wallet,
				"transaction_type": "Withdrawal",
				"direction": "Debit",
				"amount": self.amount,
				"balance_after": wallet.balance,
				"reference_doctype": "Withdrawal Request",
				"reference_name": self.name,
			}
		).insert(ignore_permissions=True)
