import frappe
from frappe import _
from frappe.model.naming import set_name_by_naming_series
from frappe.website.website_generator import WebsiteGenerator

from worcent.worcent_core.utils import unique_route


class EmployerProfile(WebsiteGenerator):
	website = frappe._dict(
		condition_field="published",
		page_title_field="company_name",
		template="templates/generators/employer/employer.html",
	)

	def autoname(self):
		set_name_by_naming_series(self)

	def before_insert(self):
		if not self.user:
			self.user = frappe.session.user

	def validate(self):
		self.set_route()
		self.enforce_single_profile_per_user()
		self.apply_default_plan()
		self.sync_freelancer_link()

	def set_route(self):
		if not self.route:
			self.route = unique_route("Employer Profile", "employer", self.company_name or self.user)

	def enforce_single_profile_per_user(self):
		existing = frappe.db.get_value(
			"Employer Profile", {"user": self.user, "name": ["!=", self.name or ""]}, "name"
		)
		if existing:
			frappe.throw(_("User {0} already has an Employer Profile ({1})").format(self.user, existing))

	def apply_default_plan(self):
		if not self.plan:
			self.plan = frappe.db.get_single_value("Worcent Settings", "default_employer_plan")

	def sync_freelancer_link(self):
		self.freelancer_profile = frappe.db.get_value("Freelancer Profile", {"user": self.user}, "name")

	def on_update(self):
		self.sync_employer_role()
		from worcent.worcent_core.wallet_utils import ensure_wallet

		ensure_wallet("Employer Profile", self.name)

	def sync_employer_role(self):
		if not self.user or self.user == "Administrator":
			return
		user = frappe.get_doc("User", self.user)
		if "Employer" not in [r.role for r in user.roles]:
			user.append("roles", {"role": "Employer"})
			user.save(ignore_permissions=True)

	def get_context(self, context):
		context.no_cache = 1
		context.title = self.company_name
		context.parents = [{"name": _("Employers"), "route": "employers"}]
		context.job_postings = frappe.get_all(
			"Job Posting",
			filters={"employer": self.name, "status": "Open"},
			fields=["title", "route", "budget_type", "budget_min", "budget_max"],
			limit_page_length=10,
		)


def has_website_permission(doc, ptype, user, verbose=False):
	if user == "Administrator":
		return True
	if doc.published and doc.status == "Active":
		return True
	return doc.user == user
