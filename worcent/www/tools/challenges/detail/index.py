import json

import frappe

sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.body_class = "worcent-tools"
	slug = frappe.form_dict.get("slug")
	if not slug or not frappe.db.exists("Skill Challenge", slug):
		frappe.throw("Challenge not found", frappe.DoesNotExistError)

	challenge = frappe.get_doc("Skill Challenge", slug)
	context.challenge = challenge
	context.tasks = sorted(challenge.daily_tasks, key=lambda d: d.day_number)

	context.enrollment = None
	context.completed_days = []
	if frappe.session.user != "Guest":
		existing = frappe.db.get_value(
			"Skill Challenge Enrollment", {"user": frappe.session.user, "challenge": challenge.name}, "name"
		)
		if existing:
			context.enrollment = frappe.get_doc("Skill Challenge Enrollment", existing)
			context.completed_days = json.loads(context.enrollment.completed_days_json or "[]")
