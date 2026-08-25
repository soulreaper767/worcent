import frappe
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series


class Proposal(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		if not self.job_posting and not self.gig:
			frappe.throw(frappe._("Proposal must reference either a Job Posting or a Gig"))

	def on_update(self):
		if self.job_posting:
			count = frappe.db.count("Proposal", {"job_posting": self.job_posting})
			frappe.db.set_value("Job Posting", self.job_posting, "proposals_count", count)

	def on_trash(self):
		if self.job_posting:
			count = frappe.db.count("Proposal", {"job_posting": self.job_posting, "name": ["!=", self.name]})
			frappe.db.set_value("Job Posting", self.job_posting, "proposals_count", count)
