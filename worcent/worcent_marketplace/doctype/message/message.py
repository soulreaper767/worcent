import frappe
from frappe import _
from frappe.model.document import Document

ADMIN_ROLES = {"Worcent Admin", "System Manager"}


class Message(Document):
	def validate(self):
		if self.is_new() and frappe.session.user not in (self.sender_user, "Administrator") and not ADMIN_ROLES.intersection(
			frappe.get_roles()
		):
			frappe.throw(_("You can only send messages as yourself."))

	def on_update(self):
		if not self.flags.in_insert:
			return
		frappe.db.set_value("Conversation", self.conversation, "last_message_at", self.sent_at)
		recipient_field = "employer_unread_count" if self.sender_type == "Freelancer" else "freelancer_unread_count"
		frappe.db.set_value(
			"Conversation", self.conversation, recipient_field,
			frappe.utils.cint(frappe.db.get_value("Conversation", self.conversation, recipient_field)) + 1,
		)
