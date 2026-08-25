import frappe
from frappe.model.document import Document


class Office(Document):
	def on_update(self):
		self.ensure_hr_branch()

	def ensure_hr_branch(self):
		if self.hr_branch:
			return
		if frappe.db.exists("Branch", self.office_name):
			self.db_set("hr_branch", self.office_name)
			return
		branch = frappe.get_doc({"doctype": "Branch", "branch": self.office_name})
		branch.insert(ignore_permissions=True)
		self.db_set("hr_branch", branch.name)
