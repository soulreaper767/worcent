import frappe
from frappe.model.document import Document


class MentorProgram(Document):
	def on_update(self):
		frappe.db.set_value("Freelancer Profile", self.mentor, "is_mentor", 1 if self.status == "Active" else 0)
