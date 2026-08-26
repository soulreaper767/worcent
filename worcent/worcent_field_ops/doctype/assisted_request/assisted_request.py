import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series


class AssistedRequest(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def _require_own_rep(self):
		rep_user = frappe.db.get_value("Rep", self.rep, "user")
		if frappe.session.user != "Administrator" and "Worcent Admin" not in frappe.get_roles() and frappe.session.user != rep_user:
			frappe.throw(_("Only the assigned Rep can do that."))

	@frappe.whitelist()
	def mark_in_progress(self):
		if self.status != "New":
			frappe.throw(_("Only a New request can be marked In Progress."))
		self._require_own_rep()
		self.status = "In Progress"
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def convert(self):
		from worcent.worcent_field_ops.assisted_engine import convert_assisted_request

		return convert_assisted_request(self.name)

	@frappe.whitelist()
	def close(self):
		if self.status == "Converted":
			frappe.throw(_("A Converted request is already resolved."))
		self._require_own_rep()
		self.status = "Closed"
		self.save(ignore_permissions=True)
