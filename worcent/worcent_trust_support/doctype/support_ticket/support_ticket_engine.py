import frappe
from frappe.utils import add_to_date, now_datetime

from worcent.worcent_trust_support.doctype.support_ticket.support_ticket import _least_loaded_support_agent


def escalate_unanswered_tickets():
	"""Hourly: any Open/In Progress ticket that's had no agent response
	within an hour of being assigned gets reassigned to a different,
	less-loaded Support Agent."""
	cutoff = add_to_date(now_datetime(), hours=-1)

	stale = frappe.get_all(
		"Support Ticket",
		filters={
			"status": ["in", ["Open", "In Progress"]],
			"first_response_on": ["is", "not set"],
			"assigned_on": ["<=", cutoff],
		},
		fields=["name", "assigned_to"],
	)

	for ticket in stale:
		next_agent = _least_loaded_support_agent(exclude=ticket.assigned_to)
		if not next_agent or next_agent == ticket.assigned_to:
			continue
		doc = frappe.get_doc("Support Ticket", ticket.name)
		doc.db_set("assigned_to", next_agent)
		doc.db_set("assigned_on", now_datetime())
		doc.db_set("escalation_count", (doc.escalation_count or 0) + 1)
		doc.add_comment(
			"Info",
			f"Auto-escalated: no response within 1 hour, reassigned from {ticket.assigned_to or 'nobody'} to {next_agent}",
		)
	frappe.db.commit()
