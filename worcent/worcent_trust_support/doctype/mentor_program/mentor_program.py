import frappe
from frappe import _
from frappe.model.document import Document


class MentorProgram(Document):
	def validate(self):
		if self.is_new() and frappe.session.user != "Administrator" and "Worcent Admin" not in frappe.get_roles():
			owner = frappe.db.get_value("Freelancer Profile", self.mentor, "user")
			if owner != frappe.session.user:
				frappe.throw(_("You can only set yourself up as a mentor."))

	def on_update(self):
		frappe.db.set_value("Freelancer Profile", self.mentor, "is_mentor", 1 if self.status == "Active" else 0)
