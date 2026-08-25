import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series

ADMIN_ROLES = {"Worcent Admin", "System Manager", "Finance Manager"}


class Milestone(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def _contract(self):
		return frappe.get_cached_doc("Contract", self.contract)

	def _require_employer_or_admin(self):
		user = frappe.session.user
		if ADMIN_ROLES.intersection(frappe.get_roles(user)):
			return
		employer_user = frappe.db.get_value("Employer Profile", self._contract().employer, "user")
		if employer_user != user:
			frappe.throw(_("Only the employer on this contract can do that."))

	def _require_dispute_authority(self):
		user = frappe.session.user
		if (ADMIN_ROLES | {"Dispute Arbitrator"}).intersection(frappe.get_roles(user)):
			return
		frappe.throw(_("Only Finance/Admin or a Dispute Arbitrator can refund a funded milestone."))

	@frappe.whitelist()
	def fund(self):
		if self.status != "Pending":
			frappe.throw(_("Only a Pending milestone can be funded."))
		self._require_employer_or_admin()
		from worcent.worcent_finance.escrow_engine import fund_milestone

		fund_milestone(self.name)
		self.reload()

	@frappe.whitelist()
	def approve_and_release(self):
		if self.status not in ("Funded", "Submitted"):
			frappe.throw(_("Only a Funded or Submitted milestone can be released."))
		self._require_employer_or_admin()
		from worcent.worcent_finance.escrow_engine import release_milestone

		result = release_milestone(self.name)
		self.reload()
		return result

	@frappe.whitelist()
	def refund(self):
		if self.status not in ("Funded", "Submitted", "Disputed"):
			frappe.throw(_("Only a Funded, Submitted or Disputed milestone can be refunded."))
		self._require_dispute_authority()
		from worcent.worcent_finance.escrow_engine import refund_milestone

		refund_milestone(self.name)
		self.reload()
