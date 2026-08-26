import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import add_days, today

ADMIN_ROLES = {"Worcent Admin", "System Manager"}
OPEN_STATUSES = ("Submitted", "Shortlisted")


class Proposal(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		if not self.job_posting and not self.gig:
			frappe.throw(frappe._("Proposal must reference either a Job Posting or a Gig"))
		if (
			self.is_new()
			and not self.flags.ignore_owner_check
			and frappe.session.user not in ("Administrator",)
			and not ADMIN_ROLES.intersection(frappe.get_roles())
		):
			owner = frappe.db.get_value("Freelancer Profile", self.freelancer, "user")
			if owner != frappe.session.user:
				frappe.throw(_("You can only submit proposals as yourself."))

	def on_update(self):
		if self.job_posting:
			count = frappe.db.count("Proposal", {"job_posting": self.job_posting})
			frappe.db.set_value("Job Posting", self.job_posting, "proposals_count", count)

	def on_trash(self):
		if self.job_posting:
			count = frappe.db.count("Proposal", {"job_posting": self.job_posting, "name": ["!=", self.name]})
			frappe.db.set_value("Job Posting", self.job_posting, "proposals_count", count)

	def _require_employer_or_admin(self):
		user = frappe.session.user
		if ADMIN_ROLES.intersection(frappe.get_roles(user)):
			return
		if not self.job_posting:
			frappe.throw(_("Only Job Posting proposals can be managed this way yet."))
		employer_user = frappe.db.get_value(
			"Employer Profile", frappe.db.get_value("Job Posting", self.job_posting, "employer"), "user"
		)
		if employer_user != user:
			frappe.throw(_("Only the employer who posted this job can do that."))

	@frappe.whitelist()
	def accept_proposal(self):
		if self.status not in OPEN_STATUSES:
			frappe.throw(_("Only a Submitted or Shortlisted proposal can be accepted."))
		if not self.job_posting:
			frappe.throw(_("Only Job Posting proposals can be accepted into a contract yet."))
		self._require_employer_or_admin()

		job_posting = frappe.get_doc("Job Posting", self.job_posting)

		contract = frappe.get_doc(
			{
				"doctype": "Contract",
				"job_posting": job_posting.name,
				"proposal": self.name,
				"freelancer": self.freelancer,
				"employer": job_posting.employer,
				"contract_type": "Hourly" if job_posting.budget_type == "Hourly" else "Fixed",
				"rate": self.bid_amount,
				"status": "Active",
			}
		)
		contract.insert(ignore_permissions=True)

		milestone = frappe.get_doc(
			{
				"doctype": "Milestone",
				"contract": contract.name,
				"title": job_posting.title,
				"amount": self.bid_amount,
				"due_date": add_days(today(), self.delivery_days or 14),
				"status": "Pending",
			}
		)
		milestone.insert(ignore_permissions=True)

		self.status = "Accepted"
		self.save(ignore_permissions=True)

		frappe.db.set_value("Job Posting", job_posting.name, "status", "In Progress")

		for other in frappe.get_all(
			"Proposal",
			filters={"job_posting": job_posting.name, "status": ["in", OPEN_STATUSES], "name": ["!=", self.name]},
			pluck="name",
		):
			frappe.db.set_value("Proposal", other, "status", "Rejected")

		return contract.name

	@frappe.whitelist()
	def reject_proposal(self):
		if self.status not in OPEN_STATUSES:
			frappe.throw(_("Only a Submitted or Shortlisted proposal can be rejected."))
		self._require_employer_or_admin()
		self.status = "Rejected"
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def shortlist_proposal(self):
		if self.status != "Submitted":
			frappe.throw(_("Only a Submitted proposal can be shortlisted."))
		self._require_employer_or_admin()
		self.status = "Shortlisted"
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def withdraw_proposal(self):
		if self.status not in OPEN_STATUSES:
			frappe.throw(_("Only a Submitted or Shortlisted proposal can be withdrawn."))
		user = frappe.session.user
		if user != "Administrator" and not ADMIN_ROLES.intersection(frappe.get_roles(user)):
			owner = frappe.db.get_value("Freelancer Profile", self.freelancer, "user")
			if owner != user:
				frappe.throw(_("Only the freelancer who submitted this proposal can withdraw it."))
		self.status = "Withdrawn"
		self.save(ignore_permissions=True)
