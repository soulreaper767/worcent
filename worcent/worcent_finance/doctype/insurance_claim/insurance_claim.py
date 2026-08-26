import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import flt

PROCESSING_ROLES = {"Finance Manager", "Accounts Manager", "Worcent Admin", "System Manager"}


class InsuranceClaim(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def _require_processing_role(self):
		if not PROCESSING_ROLES.intersection(frappe.get_roles()):
			frappe.throw(_("Only Finance can process an insurance claim."))

	@frappe.whitelist()
	def mark_under_review(self):
		if self.status != "Submitted":
			frappe.throw(_("Only a Submitted claim can be marked Under Review."))
		self._require_processing_role()
		self.status = "Under Review"
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def reject(self, reason=None):
		if self.status not in ("Submitted", "Under Review"):
			frappe.throw(_("Only a Submitted or Under Review claim can be rejected."))
		self._require_processing_role()
		self.status = "Rejected"
		if reason:
			self.reason = (self.reason or "") + f"\n\nRejected: {reason}"
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def approve_and_pay(self):
		if self.status not in ("Submitted", "Under Review"):
			frappe.throw(_("Only a Submitted or Under Review claim can be approved."))
		self._require_processing_role()

		freelancer = frappe.db.get_value("Insurance Policy", self.policy, "freelancer")
		if not freelancer:
			frappe.throw(_("This claim's policy has no freelancer on record."))

		from worcent.worcent_core.wallet_utils import ensure_wallet

		wallet = frappe.get_doc("Wallet", ensure_wallet("Freelancer Profile", freelancer))
		wallet.balance = flt(wallet.balance) + flt(self.amount_claimed)
		wallet.save(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "Wallet Transaction",
				"wallet": wallet.name,
				"transaction_type": "Insurance Payout",
				"direction": "Credit",
				"amount": self.amount_claimed,
				"balance_after": wallet.balance,
				"reference_doctype": "Insurance Claim",
				"reference_name": self.name,
			}
		).insert(ignore_permissions=True)

		from worcent.worcent_finance.accounting_engine import record_bonus

		record_bonus(
			"Freelancer Profile", freelancer, self.amount_claimed, self.name, label="Insurance claim payout"
		)

		self.status = "Paid"
		self.save(ignore_permissions=True)
		frappe.db.set_value("Insurance Policy", self.policy, "status", "Claimed")
