import frappe
from frappe import _
from frappe.model.document import Document


class SavedItem(Document):
	def validate(self):
		if not self.user:
			self.user = frappe.session.user
		if frappe.session.user not in (self.user, "Administrator") and "Worcent Admin" not in frappe.get_roles():
			frappe.throw(_("You can only save items to your own list."))
		if self.is_new() and frappe.db.exists(
			"Saved Item", {"user": self.user, "item_doctype": self.item_doctype, "item_name": self.item_name}
		):
			frappe.throw(_("Already saved."))
