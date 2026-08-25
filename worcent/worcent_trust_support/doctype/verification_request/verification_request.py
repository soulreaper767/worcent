import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series

LEVEL_ORDER = ["Unverified", "Email Verified", "Phone Verified", "ID Verified", "Business Verified"]
LEVEL_BY_TYPE = {
	"Email": "Email Verified",
	"Phone": "Phone Verified",
	"ID": "ID Verified",
	"Business": "Business Verified",
}
BONUS_ELIGIBLE_LEVELS = {"ID Verified", "Business Verified"}
REVIEW_ROLES = {"Worcent Admin", "System Manager", "Office Manager", "Field Rep"}


class VerificationRequest(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def on_update(self):
		if self.status == "Approved" and self.has_value_changed("status"):
			self.approve()

	def approve(self):
		if not self.reviewed_by:
			self.db_set("reviewed_by", frappe.session.user)

		new_level = LEVEL_BY_TYPE.get(self.verification_type)
		if not new_level:
			return
		current_level = frappe.db.get_value(self.party_type, self.party, "verification_level")
		if LEVEL_ORDER.index(new_level) > LEVEL_ORDER.index(current_level or "Unverified"):
			frappe.db.set_value(self.party_type, self.party, "verification_level", new_level)
			if new_level in BONUS_ELIGIBLE_LEVELS:
				from worcent.worcent_finance.referral_engine import apply_verification_bonus

				apply_verification_bonus(self.party_type, self.party)

	@frappe.whitelist()
	def approve_request(self):
		self._require_review_role()
		if self.status == "Approved":
			return
		self.status = "Approved"
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def reject_request(self, reason=None):
		self._require_review_role()
		self.status = "Rejected"
		if reason:
			self.review_notes = reason
		self.save(ignore_permissions=True)

	def _require_review_role(self):
		if not REVIEW_ROLES.intersection(frappe.get_roles()):
			frappe.throw(_("Only an Office Manager, Field Rep or Admin can review verification requests."))
