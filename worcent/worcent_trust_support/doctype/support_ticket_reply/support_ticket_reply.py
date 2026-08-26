import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

SUPPORT_ROLES = {"Support Agent", "Worcent Admin", "System Manager"}


class SupportTicketReply(Document):
	def validate(self):
		if not self.message:
			frappe.throw(_("Write a message before sending."))

	def before_insert(self):
		self.sender = frappe.session.user
		is_support = bool(SUPPORT_ROLES.intersection(frappe.get_roles()))
		self.sender_role = "Support" if is_support else "Requester"
		if not is_support:
			self.is_internal_note = 0

		ticket = frappe.get_doc("Support Ticket", self.ticket)
		if frappe.session.user != "Administrator" and not is_support and ticket.raised_by != frappe.session.user:
			frappe.throw(_("You can only reply on your own ticket."))

	def after_insert(self):
		ticket = frappe.get_doc("Support Ticket", self.ticket)
		if self.sender_role == "Support" and not self.is_internal_note:
			if not ticket.first_response_on:
				ticket.db_set("first_response_on", now_datetime())
			if ticket.status == "Open":
				ticket.db_set("status", "In Progress")
		elif self.sender_role == "Requester" and ticket.status in ("Resolved", "Closed"):
			ticket.db_set("status", "Open")
