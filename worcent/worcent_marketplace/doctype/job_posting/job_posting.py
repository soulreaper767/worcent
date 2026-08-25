import frappe
from frappe import _
from frappe.model.naming import set_name_by_naming_series
from frappe.website.website_generator import WebsiteGenerator

from worcent.worcent_core.utils import unique_route


class JobPosting(WebsiteGenerator):
	website = frappe._dict(
		condition_field="published",
		page_title_field="title",
		template="templates/generators/job_posting/job_posting.html",
	)

	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		if not self.route:
			self.route = unique_route("Job Posting", "jobs", self.title)

	def get_context(self, context):
		context.no_cache = 1
		context.title = self.title
		context.parents = [{"name": _("Jobs"), "route": "jobs"}]
		context.employer_doc = frappe.get_cached_doc("Employer Profile", self.employer)
		context.proposal_count = frappe.db.count("Proposal", {"job_posting": self.name})


def has_website_permission(doc, ptype, user, verbose=False):
	if user == "Administrator":
		return True
	if doc.published and doc.status == "Open":
		return True
	employer_user = frappe.db.get_value("Employer Profile", doc.employer, "user")
	return employer_user == user
