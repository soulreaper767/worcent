import frappe
from frappe import _
from frappe.model.document import Document


class WorkSubmission(Document):
	def validate(self):
		if self.is_new():
			self._require_freelancer_on_contract()
			self._require_milestone_funded()
			self.status = "Submitted"
		if self.status == "Submitted" and self.has_value_changed("status"):
			frappe.db.set_value("Milestone", self.milestone, "status", "Submitted")

	def _require_milestone_funded(self):
		milestone_status = frappe.db.get_value("Milestone", self.milestone, "status")
		if milestone_status != "Funded":
			frappe.throw(
				_(
					"The employer hasn't funded this milestone yet (status: {0}). Don't start work until it "
					"shows Funded -- that's what confirms payment is secured in escrow."
				).format(milestone_status)
			)

	def _contract(self):
		return frappe.get_cached_doc("Contract", frappe.db.get_value("Milestone", self.milestone, "contract"))

	def _require_freelancer_on_contract(self):
		if frappe.session.user == "Administrator" or "Worcent Admin" in frappe.get_roles():
			return
		freelancer_user = frappe.db.get_value("Freelancer Profile", self._contract().freelancer, "user")
		if freelancer_user != frappe.session.user:
			frappe.throw(_("Only the freelancer on this contract can submit work for it."))

	def _require_employer_on_contract(self):
		if frappe.session.user == "Administrator" or "Worcent Admin" in frappe.get_roles():
			return
		employer_user = frappe.db.get_value("Employer Profile", self._contract().employer, "user")
		if employer_user != frappe.session.user:
			frappe.throw(_("Only the employer on this contract can review this submission."))

	@frappe.whitelist()
	def approve(self):
		if self.status != "Submitted":
			frappe.throw(_("Only a Submitted work submission can be approved."))
		self._require_employer_on_contract()
		self.status = "Approved"
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def reject(self, reason=None):
		if self.status != "Submitted":
			frappe.throw(_("Only a Submitted work submission can be rejected."))
		self._require_employer_on_contract()
		self.status = "Rejected"
		if reason:
			self.notes = (self.notes or "") + f"\n\nRejected: {reason}"
		self.save(ignore_permissions=True)
		# Back to Funded (not Pending -- the money's still in escrow) so the
		# freelancer can submit revised work without the employer re-paying.
		frappe.db.set_value("Milestone", self.milestone, "status", "Funded")
