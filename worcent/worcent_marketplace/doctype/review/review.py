import frappe
from frappe.model.document import Document


class Review(Document):
	def validate(self):
		if not self.reviewer:
			self.reviewer = frappe.session.user

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
