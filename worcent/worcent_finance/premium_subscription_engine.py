import frappe
from frappe.utils import add_days, today

from worcent.worcent_finance.premium_subscription_api import CYCLE_DAYS, TIER_FIELDS, _charge_and_extend


def process_renewals():
	"""Scheduled daily: any Active Premium Subscription due for renewal gets
	auto-charged for another cycle, or -- if the wallet can't cover it --
	expires (and, for a Freelancer plan, drops their premium_tier back to
	None) with a notification either way."""
	due = frappe.get_all(
		"Premium Subscription",
		filters={"status": "Active", "renews_on": ["<=", today()]},
		fields=["name", "user", "plan"],
	)
	for sub in due:
		plan_doc = frappe.get_cached_doc("Premium Subscription Plan", sub.plan)
		party_type = TIER_FIELDS[plan_doc.tier_for]
		party = frappe.db.get_value(party_type, {"user": sub.user}, "name")
		if not party:
			continue

		from worcent.worcent_core.notify import notify

		if _charge_and_extend(sub.name, plan_doc, party_type, party):
			frappe.db.set_value(
				"Premium Subscription", sub.name, "renews_on", add_days(today(), CYCLE_DAYS.get(plan_doc.billing_cycle, 30))
			)
			notify(sub.user, "Subscription renewed", f"Your {plan_doc.plan_name} subscription was renewed.",
				reference_doctype="Premium Subscription", reference_name=sub.name)
		else:
			frappe.db.set_value("Premium Subscription", sub.name, "status", "Expired")
			if plan_doc.tier_for == "Freelancer":
				frappe.db.set_value("Freelancer Profile", party, "premium_tier", "None")
			notify(sub.user, "Subscription expired", f"Your {plan_doc.plan_name} subscription expired (insufficient wallet balance).",
				reference_doctype="Premium Subscription", reference_name=sub.name)
