import frappe
from frappe.model.document import Document


class IndustryGuru(Document):
	def on_update(self):
		frappe.db.set_value("Freelancer Profile", self.freelancer, "is_guru", 1)

	def on_trash(self):
		frappe.db.set_value("Freelancer Profile", self.freelancer, "is_guru", 0)
