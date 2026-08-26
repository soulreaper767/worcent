import frappe
from frappe import _
from frappe.model.naming import set_name_by_naming_series
from frappe.website.website_generator import WebsiteGenerator

from worcent.worcent_core.utils import unique_route


class Gig(WebsiteGenerator):
	website = frappe._dict(
		condition_field="published",
		page_title_field="title",
		template="templates/generators/gig/gig.html",
	)

	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		self.set_freelancer()
		if not self.route:
			self.route = unique_route("Gig", "gigs", self.title)

	def set_freelancer(self):
		if frappe.session.user == "Administrator" or "Worcent Admin" in frappe.get_roles():
			if not self.freelancer:
				frappe.throw(_("Set a Freelancer for this Gig."))
			return
		own_freelancer = frappe.db.get_value("Freelancer Profile", {"user": frappe.session.user}, "name")
		if not own_freelancer:
			frappe.throw(_("Only a Freelancer Profile can create a Gig."))
		self.freelancer = own_freelancer

	def get_context(self, context):
		context.no_cache = 1
		context.title = self.title
		context.parents = [{"name": _("Gigs"), "route": "gigs"}]
		context.freelancer_doc = frappe.get_cached_doc("Freelancer Profile", self.freelancer)


def has_website_permission(doc, ptype, user, verbose=False):
	if user == "Administrator":
		return True
	if doc.published and doc.status == "Active":
		return True
	freelancer_user = frappe.db.get_value("Freelancer Profile", doc.freelancer, "user")
	return freelancer_user == user
