import frappe
from frappe import _
from frappe.model.naming import set_name_by_naming_series
from frappe.website.website_generator import WebsiteGenerator

from worcent.worcent_core.utils import unique_route


class Agency(WebsiteGenerator):
	website = frappe._dict(
		condition_field="published",
		page_title_field="agency_name",
		template="templates/generators/agency/agency.html",
	)

	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		if not self.route:
			self.route = unique_route("Agency", "agency", self.agency_name)
		self.refresh_stats()

	def refresh_stats(self):
		self.total_freelancers = frappe.db.count("Agency Membership", {"agency": self.name, "status": "Active"})

	def get_context(self, context):
		context.no_cache = 1
		context.title = self.agency_name
		context.members = frappe.get_all(
			"Agency Membership",
			filters={"agency": self.name, "status": "Active"},
			fields=["freelancer"],
		)
		for m in context.members:
			profile = frappe.db.get_value(
				"Freelancer Profile",
				m.freelancer,
				["display_name", "route", "profile_photo", "headline", "rating_avg"],
				as_dict=True,
			)
			m.update(profile or {})


def has_website_permission(doc, ptype, user, verbose=False):
	if user == "Administrator":
		return True
	if doc.published and doc.status == "Active":
		return True
	return doc.owner_user == user
