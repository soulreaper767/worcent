import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import flt

RANK_ORDER = ["Bronze", "Silver", "Gold", "Platinum"]
REVIEW_ROLES = {"Rank Reviewer", "Worcent Admin", "System Manager"}
APPEAL_FEE_USD = 5


class RankApplication(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		if self.is_new():
			if not self.freelancer:
				self.freelancer = frappe.db.get_value("Freelancer Profile", {"user": frappe.session.user}, "name")
			if not self.freelancer:
				frappe.throw(_("Only a Freelancer Profile can apply for a rank change."))
			if frappe.session.user != "Administrator" and "Worcent Admin" not in frappe.get_roles():
				owner = frappe.db.get_value("Freelancer Profile", self.freelancer, "user")
				if owner != frappe.session.user:
					frappe.throw(_("You can only apply for your own rank."))
			if frappe.db.exists(
				"Rank Application", {"freelancer": self.freelancer, "status": ["in", ["Pending", "Appeal Pending"]]}
			):
				frappe.throw(_("You already have a Rank Application in progress."))

			current_rank = frappe.db.get_value("Freelancer Profile", self.freelancer, "rank") or "Bronze"
			self.current_rank = current_rank
			current_idx = RANK_ORDER.index(current_rank)
			if current_idx >= len(RANK_ORDER) - 1:
				frappe.throw(_("You're already at the highest rank."))
			expected_next = RANK_ORDER[current_idx + 1]
			if self.requested_rank != expected_next:
				frappe.throw(_("You can only apply for the next rank up: {0}.").format(expected_next))
			if not self.justification:
				frappe.throw(_("Explain why your rank should be raised."))

	@frappe.whitelist()
	def approve(self, review_notes=None):
		self._require_reviewer()
		if self.status not in ("Pending", "Appeal Pending"):
			frappe.throw(_("This application isn't awaiting review."))

		frappe.db.set_value("Freelancer Profile", self.freelancer, "rank", self.requested_rank)
		if self.status == "Appeal Pending":
			self._finish_appeal("Appeal Approved", review_notes)
		else:
			self.status = "Approved"
			self.reviewed_by = frappe.session.user
			if review_notes:
				self.review_notes = review_notes
			self.save(ignore_permissions=True)
		return self.status

	@frappe.whitelist()
	def reject(self, review_notes=None):
		self._require_reviewer()
		if self.status not in ("Pending", "Appeal Pending"):
			frappe.throw(_("This application isn't awaiting review."))

		if self.status == "Appeal Pending":
			self._finish_appeal("Appeal Rejected", review_notes)
		else:
			self.status = "Rejected"
			self.reviewed_by = frappe.session.user
			if review_notes:
				self.review_notes = review_notes
			self.save(ignore_permissions=True)
		return self.status

	def _finish_appeal(self, outcome, notes):
		if self.reviewed_by == frappe.session.user:
			frappe.throw(_("The original reviewer cannot also decide the appeal — needs a second reviewer."))
		self.status = outcome
		if notes:
			self.appeal_notes = (self.appeal_notes or "") + f"\n\nAppeal decision: {notes}"
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def appeal(self):
		if self.status != "Rejected":
			frappe.throw(_("Only a rejected application can be appealed."))
		if self.appeal_used:
			frappe.throw(_("You've already used your one appeal on this application."))
		if frappe.session.user != "Administrator":
			owner = frappe.db.get_value("Freelancer Profile", self.freelancer, "user")
			if owner != frappe.session.user:
				frappe.throw(_("Only the applicant can appeal."))

		from worcent.worcent_core.wallet_utils import ensure_wallet

		wallet = frappe.get_doc("Wallet", ensure_wallet("Freelancer Profile", self.freelancer))
		if flt(wallet.balance) < APPEAL_FEE_USD:
			frappe.throw(_("Appealing costs ${0}. Top up your wallet first.").format(APPEAL_FEE_USD))

		wallet.balance = flt(wallet.balance) - APPEAL_FEE_USD
		wallet.save(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Wallet Transaction",
				"wallet": wallet.name,
				"transaction_type": "Rank Appeal Fee",
				"direction": "Debit",
				"amount": APPEAL_FEE_USD,
				"balance_after": wallet.balance,
				"reference_doctype": "Rank Application",
				"reference_name": self.name,
				"remarks": "Rank application appeal fee",
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Platform Earning",
				"earning_type": "Rank Appeal Fee",
				"amount": APPEAL_FEE_USD,
				"party_type": "Freelancer Profile",
				"party": self.freelancer,
				"reference_doctype": "Rank Application",
				"reference_name": self.name,
				"remarks": "Rank application appeal fee",
			}
		).insert(ignore_permissions=True)

		self.status = "Appeal Pending"
		self.appeal_used = 1
		self.appeal_fee_paid = APPEAL_FEE_USD
		self.save(ignore_permissions=True)
		return self.status

	def _require_reviewer(self):
		if not REVIEW_ROLES.intersection(frappe.get_roles()):
			frappe.throw(_("Only a Rank Reviewer or Admin can review rank applications."))
