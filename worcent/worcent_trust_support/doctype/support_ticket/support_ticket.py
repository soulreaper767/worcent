import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import now_datetime

OWNERSHIP_CHECKS = {
	"Job Posting": lambda name, user: frappe.db.get_value("Job Posting", name, "employer") in _own_parties(user),
	"Gig": lambda name, user: frappe.db.get_value("Gig", name, "freelancer") in _own_parties(user),
	"Proposal": lambda name, user: frappe.db.get_value("Proposal", name, "freelancer") in _own_parties(user),
	"Contract": lambda name, user: bool(
		set(frappe.db.get_value("Contract", name, ["freelancer", "employer"]) or []) & set(_own_parties(user))
	),
	"Milestone": lambda name, user: bool(
		set(
			frappe.db.get_value(
				"Contract", frappe.db.get_value("Milestone", name, "contract"), ["freelancer", "employer"]
			)
			or []
		)
		& set(_own_parties(user))
	),
	"Withdrawal Request": lambda name, user: frappe.db.get_value(
		"Wallet", frappe.db.get_value("Withdrawal Request", name, "wallet"), "party"
	)
	in _own_parties(user),
	"Wallet Transaction": lambda name, user: frappe.db.get_value(
		"Wallet", frappe.db.get_value("Wallet Transaction", name, "wallet"), "party"
	)
	in _own_parties(user),
	"Dispute Case": lambda name, user: frappe.db.get_value("Dispute Case", name, "raised_by") == user,
}


def _own_parties(user):
	return [
		frappe.db.get_value("Freelancer Profile", {"user": user}, "name"),
		frappe.db.get_value("Employer Profile", {"user": user}, "name"),
	]


class SupportTicket(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		if not self.raised_by:
			self.raised_by = frappe.session.user
		self.validate_related_record_ownership()

	def validate_related_record_ownership(self):
		if not self.related_record or self.related_doctype in ("General Query", "Other"):
			return
		if frappe.session.user == "Administrator" or "Worcent Admin" in frappe.get_roles():
			return
		check = OWNERSHIP_CHECKS.get(self.related_doctype)
		if check and not check(self.related_record, self.raised_by):
			frappe.throw(_("That {0} doesn't belong to you.").format(self.related_doctype))

	def after_insert(self):
		self.auto_assign()

	def auto_assign(self):
		agent = _least_loaded_support_agent()
		if not agent:
			return
		self.db_set("assigned_to", agent)
		self.db_set("assigned_on", now_datetime())

	@frappe.whitelist()
	def reassign(self, to_user=None):
		if not {"Worcent Admin", "System Manager", "Support Agent"}.intersection(frappe.get_roles()):
			frappe.throw(_("Only Support Agents or Admin can reassign a ticket."))
		agent = to_user or _least_loaded_support_agent(exclude=self.assigned_to)
		if not agent:
			frappe.throw(_("No other Support Agent is available."))
		self.db_set("assigned_to", agent)
		self.db_set("assigned_on", now_datetime())
		self.db_set("escalation_count", (self.escalation_count or 0) + 1)
		self.add_comment("Info", _("Reassigned to {0}").format(agent))


def _least_loaded_support_agent(exclude=None):
	agents = frappe.get_all("Has Role", filters={"role": "Support Agent", "parenttype": "User"}, pluck="parent")
	agents = [a for a in agents if frappe.db.get_value("User", a, "enabled") and a != exclude]
	if not agents:
		return None
	load = {
		a: frappe.db.count("Support Ticket", {"assigned_to": a, "status": ["in", ["Open", "In Progress"]]})
		for a in agents
	}
	return min(load, key=load.get)


def on_comment_after_insert(doc, method=None):
	"""Stamps first_response_on the first time the assigned agent (or any
	Support Agent/Admin) comments on a ticket — used as the 'did anyone
	actually respond' signal for the 1-hour escalation job."""
	if doc.reference_doctype != "Support Ticket" or not doc.reference_name:
		return
	ticket = frappe.db.get_value("Support Ticket", doc.reference_name, "first_response_on")
	if ticket:
		return
	commenter_roles = frappe.get_roles(doc.owner)
	if {"Support Agent", "Worcent Admin", "System Manager"}.intersection(commenter_roles):
		frappe.db.set_value("Support Ticket", doc.reference_name, "first_response_on", now_datetime())
