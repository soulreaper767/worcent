import frappe
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series

LEVEL_ORDER = ["Unverified", "Email Verified", "Phone Verified", "ID Verified", "Business Verified"]
LEVEL_BY_TYPE = {
	"Email": "Email Verified",
	"Phone": "Phone Verified",
	"ID": "ID Verified",
	"Business": "Business Verified",
}


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
