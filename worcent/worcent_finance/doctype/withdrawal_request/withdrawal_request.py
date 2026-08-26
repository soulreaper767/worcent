import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import flt, now_datetime

PROCESSING_ROLES = {"Accounts Manager", "Finance Manager", "Worcent Admin", "System Manager"}


class WithdrawalRequest(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		if self.is_new():
			self.validate_payout_account()
			self.validate_amount()
			self.snapshot_payout_destination()

	def validate_payout_account(self):
		account = frappe.get_doc("Payout Account", self.payout_account)
		wallet = frappe.get_doc("Wallet", self.wallet)
		if account.party_type != wallet.party_type or account.party != wallet.party:
			frappe.throw(_("The selected payout account does not belong to this wallet's owner."))
		if account.status != "Active":
			frappe.throw(_("The selected payout account is disabled."))

	def validate_amount(self):
		wallet = frappe.get_doc("Wallet", self.wallet)
		min_amount = flt(frappe.db.get_single_value("Worcent Settings", "min_withdrawal_amount")) or 100
		if flt(self.amount) < min_amount:
			frappe.throw(_("Minimum withdrawal amount is {0}").format(frappe.utils.fmt_money(min_amount, currency="USD")))

		already_committed = flt(
			frappe.db.sql(
				"""select coalesce(sum(amount), 0) from `tabWithdrawal Request`
				where wallet = %s and status in ('Pending', 'Approved')""",
				self.wallet,
			)[0][0]
		)
		if already_committed + flt(self.amount) > flt(wallet.balance):
			frappe.throw(
				_("Withdrawal amount exceeds available wallet balance (accounting for {0} already committed to other pending/approved withdrawal requests).").format(
					frappe.utils.fmt_money(already_committed, currency="USD")
				)
			)

	def snapshot_payout_destination(self):
		account = frappe.get_doc("Payout Account", self.payout_account)
		if account.account_type == "Bank Transfer":
			lines = [
				f"Bank: {account.bank_name or ''}",
				f"Account Holder: {account.account_holder_name or ''}",
				f"Account No: {account.account_number or ''}",
				f"IBAN: {account.iban or ''}",
				f"SWIFT/BIC: {account.swift_bic or ''}",
				f"Branch: {account.branch_name or ''}, {account.branch_address or ''}",
			]
		elif account.account_type == "PayPal":
			lines = [f"PayPal: {account.paypal_email or ''}"]
		else:
			lines = [f"{account.other_method_label or 'Other'}: {account.other_method_details or ''}"]
		self.payout_destination_snapshot = "\n".join(lines)

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

		from worcent.worcent_finance.accounting_engine import record_withdrawal

		record_withdrawal(wallet.party_type, wallet.party, self.amount, self.name)

	@frappe.whitelist()
	def approve_request(self):
		self._require_processing_role()
		if self.status != "Pending":
			frappe.throw(_("Only a Pending request can be approved."))
		self.db_set("status", "Approved")
		self.db_set("approved_by", self._current_employee())

	@frappe.whitelist()
	def reject_request(self, reason=None):
		self._require_processing_role()
		if self.status not in ("Pending", "Approved"):
			frappe.throw(_("Only a Pending or Approved request can be rejected."))
		self.db_set("status", "Rejected")
		self.db_set("rejection_reason", reason or "")
		self.db_set("approved_by", self._current_employee())

	@frappe.whitelist()
	def mark_paid(self):
		self._require_processing_role()
		if self.status != "Approved":
			frappe.throw(_("Only an Approved request can be marked Paid."))
		if not self.approved_by:
			self.db_set("approved_by", self._current_employee())
		self.status = "Paid"
		self.save(ignore_permissions=True)

	def _require_processing_role(self):
		if not PROCESSING_ROLES.intersection(frappe.get_roles()):
			frappe.throw(_("Only an Accounts Manager or Finance team member can process withdrawal requests."))

	def _current_employee(self):
		return frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
