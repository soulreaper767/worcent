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
		if not self.route:
			self.route = unique_route("Gig", "gigs", self.title)

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
