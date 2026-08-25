import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import add_days, today


class DisputeCase(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		if not self.raised_by:
			self.raised_by = frappe.session.user
		if self.is_new():
			days = frappe.db.get_single_value("Worcent Settings", "dispute_response_days") or 14
			self.arbitration_deadline = add_days(today(), days)

	def on_update(self):
		if self.is_new():
			return
		if not self.has_value_changed("status"):
			return
		if self.status == "Open":
			self.mark_contract_disputed()
		elif self.status in ("Resolved-Freelancer", "Resolved-Employer", "Resolved-Split"):
			self.resolve()

	def mark_contract_disputed(self):
		frappe.db.set_value("Contract", self.contract, "status", "Disputed")
		if self.milestone:
			frappe.db.set_value("Milestone", self.milestone, "status", "Disputed")

	def resolve(self):
		if not self.milestone:
			frappe.db.set_value("Contract", self.contract, "status", "Active")
			return

		from worcent.worcent_finance.escrow_engine import release_milestone, refund_milestone, split_milestone

		escrow_status = frappe.db.get_value(
			"Escrow Transaction", {"milestone": self.milestone, "status": "Held"}, "name"
		)
		if escrow_status:
			if self.status == "Resolved-Freelancer":
				release_milestone(self.milestone)
			elif self.status == "Resolved-Employer":
				refund_milestone(self.milestone)
			elif self.status == "Resolved-Split":
				if not self.split_freelancer_percent:
					frappe.throw(_("Set the Freelancer Share % before resolving as split"))
				split_milestone(self.milestone, self.split_freelancer_percent, remarks=self.resolution_notes)

		frappe.db.set_value("Contract", self.contract, "status", "Active")
