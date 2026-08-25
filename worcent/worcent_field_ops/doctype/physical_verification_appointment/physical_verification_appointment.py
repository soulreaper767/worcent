import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series

LEVEL_ORDER = ["Unverified", "Email Verified", "Phone Verified", "ID Verified", "Business Verified"]
LEVEL_BY_TYPE = {
	"ID": "ID Verified",
	"Address": "ID Verified",
	"Business": "Business Verified",
}
BONUS_ELIGIBLE_LEVELS = {"ID Verified", "Business Verified"}
COMPLETION_ROLES = {"Worcent Admin", "System Manager", "Office Manager", "Field Rep"}


class PhysicalVerificationAppointment(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def on_update(self):
		if self.status == "Completed" and self.has_value_changed("status"):
			self.bump_verification_level()

	def bump_verification_level(self):
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
	def mark_completed(self, result_notes=None):
		if not COMPLETION_ROLES.intersection(frappe.get_roles()):
			frappe.throw(_("Only the assigned Rep, Office Manager or Admin can complete a verification appointment."))
		if self.status == "Completed":
			return
		self.status = "Completed"
		if result_notes:
			self.result_notes = result_notes
		self.save(ignore_permissions=True)
