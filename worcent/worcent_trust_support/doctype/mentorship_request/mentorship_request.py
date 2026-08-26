import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class MentorshipRequest(Document):
	def validate(self):
		if self.is_new():
			if frappe.session.user != "Administrator" and "Worcent Admin" not in frappe.get_roles():
				owner = frappe.db.get_value("Freelancer Profile", self.mentee, "user")
				if owner != frappe.session.user:
					frappe.throw(_("You can only request mentorship as yourself."))
			fee = flt(frappe.db.get_value("Mentor Program", self.mentor_program, "session_fee"))
			self.fee_charged = fee
			self.payment_status = "Pending" if fee else "Not Applicable"
			self.status = "Requested"

	def on_update(self):
		if self.status == "Accepted" and self.has_value_changed("status") and self.payment_status == "Pending":
			if frappe.session.user != "Administrator" and not self._is_the_mentor():
				frappe.throw(_("Only the mentor can accept a mentorship request."))
			self.charge_mentee_and_pay_mentor()

	def _is_the_mentor(self):
		mentor = frappe.db.get_value("Mentor Program", self.mentor_program, "mentor")
		mentor_user = frappe.db.get_value("Freelancer Profile", mentor, "user")
		return mentor_user == frappe.session.user

	def _require_mentor(self):
		if frappe.session.user != "Administrator" and "Worcent Admin" not in frappe.get_roles() and not self._is_the_mentor():
			frappe.throw(_("Only the mentor can do that."))

	def _require_mentee(self):
		if frappe.session.user != "Administrator" and "Worcent Admin" not in frappe.get_roles():
			owner = frappe.db.get_value("Freelancer Profile", self.mentee, "user")
			if owner != frappe.session.user:
				frappe.throw(_("Only the mentee can do that."))

	@frappe.whitelist()
	def accept(self):
		if self.status != "Requested":
			frappe.throw(_("Only a Requested mentorship can be accepted."))
		self._require_mentor()
		self.status = "Accepted"
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def reject(self):
		if self.status != "Requested":
			frappe.throw(_("Only a Requested mentorship can be rejected."))
		self._require_mentor()
		self.status = "Rejected"
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def complete(self):
		if self.status != "Accepted":
			frappe.throw(_("Only an Accepted mentorship can be marked Completed."))
		if frappe.session.user != "Administrator" and "Worcent Admin" not in frappe.get_roles() and not (
			self._is_the_mentor() or frappe.db.get_value("Freelancer Profile", self.mentee, "user") == frappe.session.user
		):
			frappe.throw(_("Only the mentor or mentee can mark this session Completed."))
		self.status = "Completed"
		self.save(ignore_permissions=True)

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

		from worcent.worcent_finance.accounting_engine import record_mentorship_fee

		record_mentorship_fee(self.mentee, mentor, self.fee_charged, commission, net, self.name)
