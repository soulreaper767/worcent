import frappe
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series


class Contract(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def before_insert(self):
		if not self.agency and self.freelancer:
			self.agency = frappe.db.get_value("Freelancer Profile", self.freelancer, "current_agency")

	def on_update(self):
		if self.status == "Completed" and self.has_value_changed("status"):
			frappe.db.set_value(
				"Freelancer Profile", self.freelancer, "jobs_completed",
				(frappe.db.get_value("Freelancer Profile", self.freelancer, "jobs_completed") or 0) + 1,
			)
			if self.agency:
				frappe.db.set_value(
					"Agency", self.agency, "total_jobs_completed",
					(frappe.db.get_value("Agency", self.agency, "total_jobs_completed") or 0) + 1,
				)
