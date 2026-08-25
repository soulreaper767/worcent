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
		self.resolved_by = frappe.session.user
		self.save(ignore_permissions=True)
		return self.status

	@frappe.whitelist()
	def appeal(self, appeal_notes):
		if self.status not in RESOLUTION_STATUSES:
			frappe.throw(_("Only a resolved dispute can be appealed."))
		if self.appeal_status != "Not Appealed":
			frappe.throw(_("This dispute has already been appealed once — only one appeal is allowed."))

		contract = frappe.db.get_value("Contract", self.contract, ["freelancer", "employer"], as_dict=True)
		freelancer_user = frappe.db.get_value("Freelancer Profile", contract.freelancer, "user")
		employer_user = frappe.db.get_value("Employer Profile", contract.employer, "user")
		if frappe.session.user not in (freelancer_user, employer_user) and not ARBITRATION_ROLES.intersection(
			frappe.get_roles()
		):
			frappe.throw(_("Only a party to this contract can appeal."))

		if not appeal_notes:
			frappe.throw(_("Explain why you're appealing this resolution."))

		self.appeal_status = "Appeal Pending"
		self.appeal_notes = appeal_notes
		self.save(ignore_permissions=True)
		return self.appeal_status

	@frappe.whitelist()
	def resolve_appeal(self, upheld, notes=None):
		if self.appeal_status != "Appeal Pending":
			frappe.throw(_("No pending appeal on this dispute."))
		if not ARBITRATION_ROLES.intersection(frappe.get_roles()):
			frappe.throw(_("Only a Dispute Arbitrator or Admin/Finance can resolve an appeal."))
		if self.resolved_by == frappe.session.user:
			frappe.throw(_("The original resolver cannot also decide the appeal — needs a second reviewer."))

		upheld = frappe.utils.cint(upheld)
		self.appeal_status = "Appeal Upheld" if upheld else "Appeal Rejected"
		self.appeal_resolved_by = frappe.session.user
		if notes:
			self.appeal_notes = (self.appeal_notes or "") + f"\n\nAppeal decision: {notes}"
		self.save(ignore_permissions=True)

		if upheld:
			frappe.msgprint(
				_(
					"Appeal upheld. The original resolution stands on record for audit purposes — if funds "
					"need correcting, post a Wallet Transaction of type 'Adjustment' for the affected wallet(s)."
				)
			)
		return self.appeal_status

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
