import frappe
from frappe import _
from frappe.model.document import Document


class Conversation(Document):
	def validate(self):
		if self.employer_profile == self.freelancer_profile:
			frappe.throw(_("A conversation needs two different parties."))
