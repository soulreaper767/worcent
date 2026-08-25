import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class SkillChallengeEnrollment(Document):
	def before_insert(self):
		self.user = frappe.session.user
		self.started_on = today()
		if not self.completed_days_json:
			self.completed_days_json = "[]"

	def after_insert(self):
		frappe.db.set_value(
			"Skill Challenge", self.challenge, "enrolled_count",
			(frappe.db.get_value("Skill Challenge", self.challenge, "enrolled_count") or 0) + 1,
		)

	@frappe.whitelist()
	def mark_day_complete(self, day_number):
		if self.user != frappe.session.user:
			frappe.throw(_("Not your enrollment."))
		day_number = int(day_number)
		days = json.loads(self.completed_days_json or "[]")
		if day_number not in days:
			days.append(day_number)
		self.completed_days_json = json.dumps(sorted(days))
		self.completed_count = len(days)

		total_days = frappe.db.get_value("Skill Challenge", self.challenge, "total_days") or 30
		if self.completed_count >= total_days:
			self.status = "Completed"
		self.save(ignore_permissions=True)
		return {"completed_count": self.completed_count, "status": self.status}
