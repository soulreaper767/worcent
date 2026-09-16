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
		if self.is_new() and frappe.session.user != "Administrator" and not ADMIN_ROLES.intersection(frappe.get_roles()):
			self._require_party_on_conversation()

	def _require_party_on_conversation(self):
		from worcent.worcent_core.permissions import get_employer_profile, get_freelancer_profile

		convo = frappe.db.get_value(
			"Conversation", self.conversation, ["freelancer_profile", "employer_profile"], as_dict=True
		)
		if not convo:
			frappe.throw(_("Conversation not found."))

		user = frappe.session.user
		is_the_freelancer = convo.freelancer_profile == get_freelancer_profile(user)
		is_the_employer = convo.employer_profile == get_employer_profile(user)
		if not is_the_freelancer and not is_the_employer:
			frappe.throw(_("You aren't a party to this conversation."), frappe.PermissionError)

		expected_type = "Freelancer" if is_the_freelancer else "Employer"
		if self.sender_type != expected_type:
			frappe.throw(_("Sender Type doesn't match which side of this conversation you're on."))

	def on_update(self):
		if not self.flags.in_insert:
			return
		frappe.db.set_value("Conversation", self.conversation, "last_message_at", self.sent_at)
		recipient_field = "employer_unread_count" if self.sender_type == "Freelancer" else "freelancer_unread_count"
		frappe.db.set_value(
			"Conversation", self.conversation, recipient_field,
			frappe.utils.cint(frappe.db.get_value("Conversation", self.conversation, recipient_field)) + 1,
		)
