import frappe
from frappe.model.document import Document


class Rep(Document):
	def on_update(self):
		self.sync_field_rep_role()

	def sync_field_rep_role(self):
		if not self.user or self.user == "Administrator":
			return
		user = frappe.get_doc("User", self.user)
		if "Field Rep" not in [r.role for r in user.roles]:
			user.append("roles", {"role": "Field Rep"})
			user.save(ignore_permissions=True)
