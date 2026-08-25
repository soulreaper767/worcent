import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class MentorshipRequest(Document):
	def validate(self):
		if self.is_new():
			fee = flt(frappe.db.get_value("Mentor Program", self.mentor_program, "session_fee"))
			self.fee_charged = fee
			self.payment_status = "Pending" if fee else "Not Applicable"

	def on_update(self):
		if self.status == "Accepted" and self.has_value_changed("status") and self.payment_status == "Pending":
			self.charge_mentee_and_pay_mentor()

	@frappe.whitelist()
	def charge_mentee_and_pay_mentor(self):
		if self.payment_status != "Pending" or not self.fee_charged:
			return
		from worcent.worcent_core.wallet_utils import ensure_wallet
		from worcent.worcent_finance.escrow_engine import _record_earning, _wallet_txn

		mentor = frappe.db.get_value("Mentor Program", self.mentor_program, "mentor")

		mentee_wallet = frappe.get_doc("Wallet", ensure_wallet("Freelancer Profile", self.mentee))
		if flt(mentee_wallet.balance) < flt(self.fee_charged):
			frappe.throw(_("Mentee's wallet balance is insufficient for this mentorship fee."))

		mentee_wallet.balance = flt(mentee_wallet.balance) - flt(self.fee_charged)
		mentee_wallet.save(ignore_permissions=True)
		_wallet_txn(
			mentee_wallet.name, "Mentorship Fee", "Debit", self.fee_charged, mentee_wallet.balance,
			"Mentorship Request", self.name, remarks="Paid mentorship session",
		)

		rate = flt(frappe.db.get_single_value("Worcent Settings", "default_platform_fee_percent")) or 5
		commission = flt(self.fee_charged) * flt(rate) / 100
		net = flt(self.fee_charged) - commission

		mentor_wallet = frappe.get_doc("Wallet", ensure_wallet("Freelancer Profile", mentor))
		mentor_wallet.balance = flt(mentor_wallet.balance) + net
		mentor_wallet.save(ignore_permissions=True)
		_wallet_txn(
			mentor_wallet.name, "Mentorship Fee", "Credit", net, mentor_wallet.balance,
			"Mentorship Request", self.name, remarks=f"Mentorship fee, {rate}% platform commission deducted",
		)
		_record_earning(
			"Mentor Fee", commission, "Freelancer Profile", mentor,
			"Mentorship Request", self.name, f"{rate}% commission on mentorship fee",
		)

		self.db_set("payment_status", "Paid")
