import frappe
from frappe.utils import today

BADGE_CRITERIA = {
	"Verified Pro": lambda f: f.verification_level in ("ID Verified", "Business Verified"),
	"Top Rated": lambda f: (f.rating_avg or 0) >= 4.8 and (f.total_reviews or 0) >= 5,
	"Rising Talent": lambda f: 1 <= (f.jobs_completed or 0) <= 5 and (f.rating_avg or 0) >= 4.5,
}


def evaluate_badges():
	"""Scheduled daily: awards the auto-qualifying badges (Verified Pro, Top
	Rated, Rising Talent) the first time a Freelancer Profile meets their
	criteria. Idempotent -- never re-awards a badge a freelancer already
	has, and never revokes one that no longer strictly applies (once earned,
	kept, same as how real reputation badges usually work)."""
	freelancers = frappe.get_all(
		"Freelancer Profile",
		filters={"status": ["!=", "Suspended"]},
		fields=["name", "verification_level", "rating_avg", "total_reviews", "jobs_completed"],
	)
	for badge_name, criteria in BADGE_CRITERIA.items():
		if not frappe.db.exists("Badge", badge_name):
			continue
		already_have = set(
			frappe.get_all("Freelancer Badge", filters={"badge": badge_name}, pluck="parent")
		)
		for f in freelancers:
			if f.name in already_have:
				continue
			if criteria(f):
				_award(f.name, badge_name)


def _award(freelancer, badge_name):
	frappe.get_doc(
		{
			"doctype": "Freelancer Badge",
			"parenttype": "Freelancer Profile",
			"parentfield": "badges",
			"parent": freelancer,
			"badge": badge_name,
			"awarded_on": today(),
		}
	).insert(ignore_permissions=True)
