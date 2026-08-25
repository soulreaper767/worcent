import frappe
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series


class Contract(Document):
	def autoname(self):
		set_name_by_naming_series(self)
