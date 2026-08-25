import frappe
from frappe import _
from frappe.model.naming import set_name_by_naming_series
from frappe.website.website_generator import WebsiteGenerator

from worcent.worcent_core.utils import unique_route


class FreelancerProfile(WebsiteGenerator):
	website = frappe._dict(
		condition_field="published",
		page_title_field="display_name",
		template="templates/generators/freelancer/freelancer.html",
	)

	def autoname(self):
		set_name_by_naming_series(self)

	def before_insert(self):
		if not self.user:
			self.user = frappe.session.user

	def validate(self):
		self.set_route()
		self.enforce_single_profile_per_user()
		self.sync_employer_link()

	def set_route(self):
		if not self.route:
			self.route = unique_route("Freelancer Profile", "freelancer", self.display_name or self.user)

	def enforce_single_profile_per_user(self):
		existing = frappe.db.get_value(
			"Freelancer Profile", {"user": self.user, "name": ["!=", self.name or ""]}, "name"
		)
		if existing:
			frappe.throw(_("User {0} already has a Freelancer Profile ({1})").format(self.user, existing))

	def sync_employer_link(self):
		self.employer_profile = frappe.db.get_value("Employer Profile", {"user": self.user}, "name")

	def on_update(self):
		self.sync_freelancer_role()
		from worcent.worcent_core.wallet_utils import ensure_wallet

		ensure_wallet("Freelancer Profile", self.name)

	def sync_freelancer_role(self):
		if not self.user or self.user == "Administrator":
			return
		user = frappe.get_doc("User", self.user)
		if "Freelancer" not in [r.role for r in user.roles]:
			user.append("roles", {"role": "Freelancer"})
			user.save(ignore_permissions=True)

	def get_context(self, context):
		context.no_cache = 1
		context.title = self.display_name
		context.parents = [{"name": _("Freelancers"), "route": "freelancers"}]
		context.reviews = frappe.get_all(
			"Review",
			filters={"reviewee_profile": self.name},
			fields=["rating", "comment", "creation", "reviewer_type"],
			order_by="creation desc",
			limit_page_length=20,
		)


def has_website_permission(doc, ptype, user, verbose=False):
	if user == "Administrator":
		return True
	if doc.published and doc.status == "Active":
		return True
	return doc.user == user
