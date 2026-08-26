import frappe
from frappe import _
from frappe.model.document import Document


class Review(Document):
	def validate(self):
		if not self.reviewer:
			self.reviewer = frappe.session.user
		if frappe.session.user != "Administrator" and "Worcent Admin" not in frappe.get_roles():
			self.validate_is_a_real_contract_party()

	def validate_is_a_real_contract_party(self):
		contract = frappe.db.get_value(
			"Contract", self.contract, ["freelancer", "employer", "status"], as_dict=True
		)
		if not contract:
			frappe.throw(_("That contract doesn't exist."))
		if contract.status not in ("Active", "Completed"):
			frappe.throw(_("You can only review a contract that's actually underway or completed."))

		freelancer_user = frappe.db.get_value("Freelancer Profile", contract.freelancer, "user")
		employer_user = frappe.db.get_value("Employer Profile", contract.employer, "user")

		if frappe.session.user == freelancer_user:
			if self.reviewer_type != "Freelancer" or self.reviewee_profile != contract.employer:
				frappe.throw(_("You can only review the employer on your own contract."))
		elif frappe.session.user == employer_user:
			if self.reviewer_type != "Employer" or self.reviewee_profile != contract.freelancer:
				frappe.throw(_("You can only review the freelancer on your own contract."))
		else:
			frappe.throw(_("You're not a party to this contract."))

		if self.is_new() and frappe.db.exists(
			"Review", {"contract": self.contract, "reviewer_type": self.reviewer_type, "name": ["!=", self.name or ""]}
		):
			frappe.throw(_("You've already reviewed this contract."))

	def after_insert(self):
		self.refresh_reviewee_stats()

	def on_trash(self):
		self.refresh_reviewee_stats()

	def refresh_reviewee_stats(self):
		stats = frappe.db.sql(
			"""
			select avg(rating) as avg_rating, count(*) as total
			from `tabReview`
			where reviewee_type = %s and reviewee_profile = %s
			""",
			(self.reviewee_type, self.reviewee_profile),
			as_dict=True,
		)
		if stats:
			frappe.db.set_value(
				self.reviewee_type,
				self.reviewee_profile,
				{
					"rating_avg": round((stats[0].avg_rating or 0) * 5, 2),
					"total_reviews": stats[0].total or 0,
				},
			)
