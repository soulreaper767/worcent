import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import add_days, today

ARBITRATION_ROLES = {"Dispute Arbitrator", "Worcent Admin", "System Manager", "Finance Manager"}
RESOLUTION_STATUSES = ("Resolved-Freelancer", "Resolved-Employer", "Resolved-Split")


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
		elif self.status in RESOLUTION_STATUSES:
			self.resolve()

	@frappe.whitelist()
	def resolve_case(self, resolution, split_freelancer_percent=None, resolution_notes=None):
		if resolution not in RESOLUTION_STATUSES:
			frappe.throw(_("Invalid resolution."))
		if not ARBITRATION_ROLES.intersection(frappe.get_roles()):
			frappe.throw(_("Only a Dispute Arbitrator or Admin/Finance can resolve a dispute."))
		if self.status in RESOLUTION_STATUSES:
			frappe.throw(_("This dispute is already resolved."))

		self.status = resolution
		if resolution_notes:
			self.resolution_notes = resolution_notes
		if resolution == "Resolved-Split":
			self.split_freelancer_percent = split_freelancer_percent
		self.save(ignore_permissions=True)
		return self.status

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
