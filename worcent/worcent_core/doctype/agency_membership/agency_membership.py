import frappe
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import flt, today


class AgencyMembership(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def before_insert(self):
		# Capture the freelancer's totals as they stand right now, so that
		# separation can later compute exactly what was earned *during* this
		# membership rather than the freelancer's whole lifetime total.
		freelancer = frappe.db.get_value(
			"Freelancer Profile", self.freelancer, ["jobs_completed", "total_earned"], as_dict=True
		)
		self.jobs_completed_at_join = freelancer.jobs_completed or 0
		self.earnings_at_join = flt(freelancer.total_earned)

	def validate(self):
		self.enforce_single_active_membership()
		if self.status == "Separated" and not self.separated_on:
			self.separated_on = today()

	def enforce_single_active_membership(self):
		if self.status != "Active":
			return
		existing = frappe.db.get_value(
			"Agency Membership",
			{"freelancer": self.freelancer, "status": "Active", "name": ["!=", self.name or ""]},
			"name",
		)
		if existing:
			frappe.throw(
				frappe._("Freelancer {0} already has an active agency membership ({1})").format(
					self.freelancer, existing
				)
			)

	def on_update(self):
		if self.status == "Separated" and self.has_value_changed("status"):
			self.snapshot_career_history()
		self.sync_current_agency()
		frappe.get_doc("Agency", self.agency).save(ignore_permissions=True)

	def snapshot_career_history(self):
		"""This is the 'his ratings/experience are fetched there too' bit:
		the freelancer's own profile already accumulates ratings/earnings
		regardless of agency affiliation (Review/Milestone always point at
		the individual), so nothing needs to move. What separation adds is a
		permanent, dated record of what was achieved *during* this specific
		membership, visible on the freelancer's public career history."""
		freelancer = frappe.db.get_value(
			"Freelancer Profile", self.freelancer, ["jobs_completed", "total_earned", "rating_avg"], as_dict=True
		)
		self.db_set("jobs_completed_during_membership", (freelancer.jobs_completed or 0) - (self.jobs_completed_at_join or 0))
		self.db_set("earnings_during_membership", flt(freelancer.total_earned) - flt(self.earnings_at_join))
		self.db_set("rating_at_separation", freelancer.rating_avg)

	def sync_current_agency(self):
		current = frappe.db.get_value(
			"Agency Membership", {"freelancer": self.freelancer, "status": "Active"}, "agency"
		)
		frappe.db.set_value("Freelancer Profile", self.freelancer, "current_agency", current)

	def on_trash(self):
		self.sync_current_agency()
