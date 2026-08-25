import frappe
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series

LEVEL_BY_TYPE = {
	"ID": "ID Verified",
	"Address": "ID Verified",
	"Business": "Business Verified",
}


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
		frappe.db.set_value(self.party_type, self.party, "verification_level", new_level)
