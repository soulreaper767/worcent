import json

import frappe

from worcent.worcent_growth.tools_engine import TOOL_REGISTRY, run_tool


@frappe.whitelist(allow_guest=True)
def use_tool(tool_name, inputs):
	if tool_name not in TOOL_REGISTRY:
		frappe.throw(frappe._("Unknown tool: {0}").format(tool_name))
	if isinstance(inputs, str):
		inputs = json.loads(inputs)

	output, metric = run_tool(tool_name, inputs)

	result = {"output": output, "saved": False, "comparison": None, "history_count": 0}

	if frappe.session.user != "Guest":
		doc = frappe.get_doc(
			{
				"doctype": "Growth Tool Result",
				"tool_name": tool_name,
				"headline": output.get("headline"),
				"metric": metric,
				"input_data": frappe.as_json(inputs),
				"output_data": frappe.as_json(output),
			}
		)
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
		result["saved"] = True
		result["comparison"] = doc.comparison
		result["result_name"] = doc.name
		result["history_count"] = frappe.db.count(
			"Growth Tool Result", {"user": frappe.session.user, "tool_name": tool_name}
		)

	return result


@frappe.whitelist(allow_guest=True)
def list_challenges():
	return frappe.get_all(
		"Skill Challenge",
		fields=["name", "title", "slug", "description", "total_days", "enrolled_count"],
		order_by="title asc",
	)


@frappe.whitelist(allow_guest=True)
def get_challenge(slug):
	challenge = frappe.get_doc("Skill Challenge", {"slug": slug})
	tasks = [
		{"day_number": d.day_number, "task_title": d.task_title, "task_description": d.task_description}
		for d in sorted(challenge.daily_tasks, key=lambda d: d.day_number)
	]

	enrollment = None
	if frappe.session.user != "Guest":
		existing = frappe.db.get_value(
			"Skill Challenge Enrollment", {"user": frappe.session.user, "challenge": challenge.name}, "name"
		)
		if existing:
			enrollment = frappe.get_doc("Skill Challenge Enrollment", existing).as_dict()

	return {
		"title": challenge.title,
		"description": challenge.description,
		"total_days": challenge.total_days,
		"tasks": tasks,
		"enrollment": enrollment,
	}


@frappe.whitelist()
def enroll_in_challenge(challenge):
	existing = frappe.db.get_value(
		"Skill Challenge Enrollment", {"user": frappe.session.user, "challenge": challenge}, "name"
	)
	if existing:
		return existing
	doc = frappe.get_doc({"doctype": "Skill Challenge Enrollment", "challenge": challenge})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


@frappe.whitelist()
def mark_challenge_day_complete(enrollment, day_number):
	doc = frappe.get_doc("Skill Challenge Enrollment", enrollment)
	return doc.mark_day_complete(day_number)


@frappe.whitelist()
def get_history(tool_name):
	if tool_name not in TOOL_REGISTRY:
		frappe.throw(frappe._("Unknown tool: {0}").format(tool_name))
	return frappe.get_all(
		"Growth Tool Result",
		filters={"user": frappe.session.user, "tool_name": tool_name},
		fields=["name", "headline", "metric", "comparison", "creation"],
		order_by="creation desc",
		limit_page_length=50,
	)
