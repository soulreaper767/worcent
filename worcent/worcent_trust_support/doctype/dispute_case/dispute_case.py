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

		return self.appeal_status

	@frappe.whitelist()
	def compute_appeal_reversal(self):
		"""Read-only preview of exactly what reversing this dispute's original
		resolution would move -- shown to the admin as a confirm dialog before
		apply_appeal_reversal() actually commits it."""
		if self.appeal_status != "Appeal Upheld":
			frappe.throw(_("This appeal hasn't been upheld."))
		if self.reversal_applied:
			frappe.throw(_("The reversal has already been applied."))

		from worcent.worcent_finance.escrow_engine import compute_resolution_reversal

		plan = compute_resolution_reversal(self.name)
		if not plan:
			frappe.throw(_("There's nothing to reverse -- the milestone was never released/refunded, or there's no milestone on this dispute."))
		for line in plan["lines"]:
			line["party_title"] = frappe.db.get_value(
				line["party_type"], line["party"], "display_name" if line["party_type"] == "Freelancer Profile" else "company_name"
			)
		return plan

	@frappe.whitelist()
	def apply_appeal_reversal(self):
		if self.appeal_status != "Appeal Upheld":
			frappe.throw(_("This appeal hasn't been upheld."))
		if self.reversal_applied:
			frappe.throw(_("The reversal has already been applied."))
		if not ARBITRATION_ROLES.intersection(frappe.get_roles()):
			frappe.throw(_("Only a Dispute Arbitrator or Admin/Finance can apply a reversal."))

		from worcent.worcent_finance.escrow_engine import apply_resolution_reversal

		plan = apply_resolution_reversal(self.name)
		self.db_set("reversal_applied", 1)

		from worcent.worcent_core.notify import notify

		contract = frappe.db.get_value("Contract", self.contract, ["freelancer", "employer"], as_dict=True)
		for profile_type, profile in (("Freelancer Profile", contract.freelancer), ("Employer Profile", contract.employer)):
			user = frappe.db.get_value(profile_type, profile, "user")
			if user:
				notify(
					user, _("Dispute appeal upheld"),
					_("The resolution on your dispute was reversed after a successful appeal. Funds are back in escrow pending a new decision."),
					reference_doctype="Dispute Case", reference_name=self.name,
				)
		return plan

	def mark_contract_disputed(self):
		frappe.db.set_value("Contract", self.contract, "status", "Disputed")
		if self.milestone:
			frappe.db.set_value("Milestone", self.milestone, "status", "Disputed")
		self.notify_other_party()

	def notify_other_party(self):
		from worcent.worcent_core.notify import notify

		contract = frappe.db.get_value("Contract", self.contract, ["freelancer", "employer"], as_dict=True)
		freelancer_user = frappe.db.get_value("Freelancer Profile", contract.freelancer, "user")
		employer_user = frappe.db.get_value("Employer Profile", contract.employer, "user")
		other_user = employer_user if self.raised_by == freelancer_user else freelancer_user
		if other_user:
			notify(
				other_user, _("Dispute opened"),
				_("A dispute was opened on your contract: {0}").format(self.reason or ""),
				reference_doctype="Dispute Case", reference_name=self.name,
			)

	def notify_resolution(self):
		from worcent.worcent_core.notify import notify

		contract = frappe.db.get_value("Contract", self.contract, ["freelancer", "employer"], as_dict=True)
		for profile_type, profile in (("Freelancer Profile", contract.freelancer), ("Employer Profile", contract.employer)):
			user = frappe.db.get_value(profile_type, profile, "user")
			if user:
				notify(
					user, _("Dispute resolved"),
					_("Your dispute was resolved: {0}").format(self.status),
					reference_doctype="Dispute Case", reference_name=self.name,
				)

	def resolve(self):
		if not self.milestone:
			frappe.db.set_value("Contract", self.contract, "status", "Active")
			self.notify_resolution()
			return

		from worcent.worcent_finance.escrow_engine import release_milestone, refund_milestone, split_milestone

		escrow_status = frappe.db.get_value(
			"Escrow Transaction", {"milestone": self.milestone, "status": "Held"}, "name"
		)
		if not escrow_status:
			frappe.throw(
				_(
					"This milestone has no funds currently held in escrow, so resolving this dispute as "
					"{0} would move no money. Nothing was ever funded (or it was already resolved) — "
					"double-check the milestone before resolving."
				).format(self.status)
			)

		if self.status == "Resolved-Freelancer":
			release_milestone(self.milestone)
		elif self.status == "Resolved-Employer":
			refund_milestone(self.milestone)
		elif self.status == "Resolved-Split":
			if not self.split_freelancer_percent:
				frappe.throw(_("Set the Freelancer Share % before resolving as split"))
			split_milestone(self.milestone, self.split_freelancer_percent, remarks=self.resolution_notes)

		frappe.db.set_value("Contract", self.contract, "status", "Active")
		self.notify_resolution()
