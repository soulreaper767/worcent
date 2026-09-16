import frappe
from frappe import _
from frappe.model.document import Document

ADMIN_ROLES = {"Worcent Admin", "System Manager"}


class Conversation(Document):
	def validate(self):
		if self.employer_profile == self.freelancer_profile:
			frappe.throw(_("A conversation needs two different parties."))
		if self.is_new() and frappe.session.user != "Administrator" and not ADMIN_ROLES.intersection(frappe.get_roles()):
			from worcent.worcent_core.permissions import get_employer_profile, get_freelancer_profile

			user = frappe.session.user
			is_the_freelancer = self.freelancer_profile == get_freelancer_profile(user)
			is_the_employer = self.employer_profile == get_employer_profile(user)
			if not is_the_freelancer and not is_the_employer:
				frappe.throw(_("You can only start a conversation you're actually a party to."))
