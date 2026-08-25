import frappe
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series


class SupportTicket(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		if not self.raised_by:
			self.raised_by = frappe.session.user
