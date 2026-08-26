import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import now_datetime

SUPPORT_ROLES = {"Support Agent", "Worcent Admin", "System Manager"}

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
		if not SUPPORT_ROLES.intersection(frappe.get_roles()):
			frappe.throw(_("Only Support Agents or Admin can reassign a ticket."))
		agent = to_user or _least_loaded_support_agent(exclude=self.assigned_to)
		if not agent:
			frappe.throw(_("No other Support Agent is available."))
		self.db_set("assigned_to", agent)
		self.db_set("assigned_on", now_datetime())
		self.db_set("escalation_count", (self.escalation_count or 0) + 1)
		self.add_comment("Info", _("Reassigned to {0}").format(agent))

	@frappe.whitelist()
	def get_replies(self):
		is_support = bool(SUPPORT_ROLES.intersection(frappe.get_roles()))
		filters = {"ticket": self.name}
		if not is_support:
			filters["is_internal_note"] = 0
		return frappe.get_all(
			"Support Ticket Reply",
			filters=filters,
			fields=["name", "sender", "sender_role", "is_internal_note", "message", "creation"],
			order_by="creation asc",
		)

	@frappe.whitelist()
	def add_reply(self, message, is_internal_note=0):
		if not SUPPORT_ROLES.intersection(frappe.get_roles()) and frappe.utils.cint(is_internal_note):
			frappe.throw(_("Only Support can add an internal note."))
		frappe.get_doc(
			{
				"doctype": "Support Ticket Reply",
				"ticket": self.name,
				"message": message,
				"is_internal_note": frappe.utils.cint(is_internal_note),
			}
		).insert()
		self.reload()
		return self.get_replies()

	@frappe.whitelist()
	def mark_resolved(self):
		self._require_support()
		self.status = "Resolved"
		self.save(ignore_permissions=True)
		self.add_comment("Info", _("Marked Resolved by {0}").format(frappe.session.user))

	@frappe.whitelist()
	def close_ticket(self):
		self._require_support()
		if self.status not in ("Resolved", "In Progress", "Open"):
			frappe.throw(_("Invalid status transition."))
		self.status = "Closed"
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def reopen_ticket(self):
		if frappe.session.user == "Administrator" or SUPPORT_ROLES.intersection(frappe.get_roles()):
			pass
		elif self.raised_by != frappe.session.user:
			frappe.throw(_("Only the requester or Support can reopen a ticket."))
		self.status = "Open"
		self.save(ignore_permissions=True)

	def _require_support(self):
		if not SUPPORT_ROLES.intersection(frappe.get_roles()):
			frappe.throw(_("Only Support Agents or Admin can do that."))


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
