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
		self.apply_default_currency()
		self.lock_referral_code()

	def lock_referral_code(self):
		if self.is_new():
			return
		previous = frappe.db.get_value("Freelancer Profile", self.name, "referred_by_code")
		if previous and self.referred_by_code != previous:
			self.referred_by_code = previous

	def apply_default_currency(self):
		if self.country and not self.preferred_currency:
			from worcent.worcent_finance.currency_utils import get_currency_for_country

			self.preferred_currency = get_currency_for_country(self.country)

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
		from worcent.worcent_finance.referral_engine import apply_referral_signup, apply_signup_bonus

		ensure_wallet("Freelancer Profile", self.name)
		apply_signup_bonus("Freelancer Profile", self.name)
		if self.referred_by_code:
			apply_referral_signup("Freelancer Profile", self.name, self.referred_by_code)

	def sync_freelancer_role(self):
		if not self.user or self.user == "Administrator":
			return
		user = frappe.get_doc("User", self.user)
		if "Freelancer" not in [r.role for r in user.roles]:
			user.append("roles", {"role": "Freelancer"})
			user.save(ignore_permissions=True)

	def compute_worcent_score(self):
		from worcent.worcent_growth.tools_engine import calculate_worcent_score

		years_experience = max([s.years_experience or 0 for s in self.skills], default=0)
		return calculate_worcent_score(
			{
				"skills": [s.skill for s in self.skills],
				"years_experience": years_experience,
				"certifications": 0,
				"portfolio_items": len(self.portfolio or []),
				"completed_jobs": self.jobs_completed or 0,
				"rating_avg": self.rating_avg or 0,
			}
		)

	def get_context(self, context):
		context.no_cache = 1
		context.title = self.display_name
		context.worcent_score = self.compute_worcent_score()
		context.parents = [{"name": _("Freelancers"), "route": "freelancers"}]
		context.reviews = frappe.get_all(
			"Review",
			filters={"reviewee_profile": self.name},
			fields=["rating", "comment", "creation", "reviewer_type"],
			order_by="creation desc",
			limit_page_length=20,
		)
		context.career_history = frappe.get_all(
			"Agency Membership",
			filters={"freelancer": self.name},
			fields=[
				"agency", "status", "joined_on", "separated_on",
				"jobs_completed_during_membership", "earnings_during_membership", "rating_at_separation",
			],
			order_by="joined_on desc",
		)
		for row in context.career_history:
			row["agency_name"] = frappe.db.get_value("Agency", row.agency, "agency_name")
			row["agency_route"] = frappe.db.get_value("Agency", row.agency, "route")


def has_website_permission(doc, ptype, user, verbose=False):
	if user == "Administrator":
		return True
	if doc.published and doc.status == "Active":
		return True
	return doc.user == user
