import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import flt, now_datetime

REVIEW_ROLES = {"Payment Officer", "Finance Manager", "Worcent Admin", "System Manager"}
PAYMENT_ROLES = {"Accounts Manager", "Finance Manager", "Worcent Admin", "System Manager"}
OPEN_STATUSES = ("Requested", "In Review")


class WithdrawalRequest(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		if self.is_new():
			self.validate_requester_owns_wallet()
			self.validate_payout_account()
			self.validate_amount()
			self.snapshot_payout_destination()
			self.available_balance = frappe.db.get_value("Wallet", self.wallet, "balance")

	def validate_requester_owns_wallet(self):
		if frappe.session.user == "Administrator" or REVIEW_ROLES.intersection(frappe.get_roles()) or PAYMENT_ROLES.intersection(frappe.get_roles()):
			return
		party = frappe.db.get_value("Wallet", self.wallet, "party")
		freelancer = frappe.db.get_value("Freelancer Profile", {"user": frappe.session.user}, "name")
		employer = frappe.db.get_value("Employer Profile", {"user": frappe.session.user}, "name")
		if party not in (freelancer, employer):
			frappe.throw(_("You can only withdraw from your own wallet."))

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
		if flt(wallet.balance) < min_amount:
			frappe.throw(
				_("Your available balance ({0}) is below the minimum withdrawal amount ({1}).").format(
					frappe.utils.fmt_money(wallet.balance, currency="USD"),
					frappe.utils.fmt_money(min_amount, currency="USD"),
				)
			)
		if flt(self.amount) < min_amount:
			frappe.throw(_("Minimum withdrawal amount is {0}").format(frappe.utils.fmt_money(min_amount, currency="USD")))

		already_committed = flt(
			frappe.db.sql(
				"""select coalesce(sum(amount), 0) from `tabWithdrawal Request`
				where wallet = %s and status in ('Requested', 'In Review', 'Approved')""",
				self.wallet,
			)[0][0]
		)
		if already_committed + flt(self.amount) > flt(wallet.balance):
			frappe.throw(
				_("Withdrawal amount exceeds available wallet balance (accounting for {0} already committed to other pending withdrawal requests).").format(
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
	def start_review(self):
		if self.status != "Requested":
			frappe.throw(_("Only a Requested withdrawal can be picked up for review."))
		self._require_review_role()
		self.db_set("status", "In Review")
		self.db_set("reviewed_by", self._current_employee())
		self.db_set("reviewed_on", now_datetime())

	@frappe.whitelist()
	def approve_request(self):
		if self.status not in OPEN_STATUSES:
			frappe.throw(_("Only a Requested or In Review request can be approved."))
		self._require_review_role()
		if not self.reviewed_by:
			self.db_set("reviewed_by", self._current_employee())
			self.db_set("reviewed_on", now_datetime())
		self.db_set("status", "Approved")

	@frappe.whitelist()
	def reject_request(self, reason=None):
		if self.status not in OPEN_STATUSES:
			frappe.throw(_("Only a Requested or In Review request can be rejected."))
		self._require_review_role()
		self.db_set("status", "Rejected")
		self.db_set("rejection_reason", reason or "")
		if not self.reviewed_by:
			self.db_set("reviewed_by", self._current_employee())
			self.db_set("reviewed_on", now_datetime())

	@frappe.whitelist()
	def mark_paid(self):
		if self.status != "Approved":
			frappe.throw(_("Only an Approved request can be marked Paid."))
		self._require_payment_role()
		if not self.approved_by:
			self.db_set("approved_by", self._current_employee())
		self.status = "Paid"
		self.save(ignore_permissions=True)

	def _require_review_role(self):
		if not REVIEW_ROLES.intersection(frappe.get_roles()):
			frappe.throw(_("Only a Payment Officer or Finance team member can review withdrawal requests."))

	def _require_payment_role(self):
		if not PAYMENT_ROLES.intersection(frappe.get_roles()):
			frappe.throw(_("Only an Accounts Manager or Finance team member can initiate payment."))

	def _current_employee(self):
		return frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")


@frappe.whitelist()
def get_my_withdrawal_context():
	"""Powers the "your available balance" panel on the New Withdrawal
	Request form -- looks up the current user's own wallet rather than
	trusting a client-supplied wallet name."""
	from worcent.worcent_core.wallet_utils import get_wallet
	from worcent.worcent_finance.currency_utils import BASE_CURRENCY, convert, get_currency_for_country

	freelancer = frappe.db.get_value("Freelancer Profile", {"user": frappe.session.user}, ["name", "country"], as_dict=True)
	employer = frappe.db.get_value("Employer Profile", {"user": frappe.session.user}, ["name", "country"], as_dict=True)
	party_type, party_name, country = (
		("Freelancer Profile", freelancer.name, freelancer.country) if freelancer
		else ("Employer Profile", employer.name, employer.country) if employer
		else (None, None, None)
	)
	if not party_name:
		frappe.throw(_("No Freelancer or Employer profile found for your account."))

	wallet = get_wallet(party_type, party_name)
	balance = flt(wallet.balance) if wallet else 0
	min_amount = flt(frappe.db.get_single_value("Worcent Settings", "min_withdrawal_amount")) or 100
	display_currency = get_currency_for_country(country)

	return {
		"wallet": wallet.name if wallet else None,
		"party_type": party_type,
		"party": party_name,
		"balance": balance,
		"min_withdrawal": min_amount,
		"base_currency": BASE_CURRENCY,
		"display_currency": display_currency,
		"balance_in_display_currency": convert(balance, BASE_CURRENCY, display_currency),
		"min_withdrawal_in_display_currency": convert(min_amount, BASE_CURRENCY, display_currency),
		"eligible": balance >= min_amount,
	}
