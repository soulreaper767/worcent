import frappe
from frappe.model.document import Document


class WorkSubmission(Document):
	def validate(self):
		if self.status == "Submitted":
			frappe.db.set_value("Milestone", self.milestone, "status", "Submitted")

	def on_update(self):
		if self.status == "Approved" and self.has_value_changed("status"):
			from worcent.worcent_finance.escrow_engine import release_milestone

			release_milestone(self.milestone)
