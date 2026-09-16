import frappe
from frappe import _
from frappe.utils import now_datetime

from worcent.worcent_core.permissions import get_employer_profile, get_freelancer_profile

RELATED_OWNER_FIELD = {
	"Gig": "freelancer",
	"Job Posting": "employer",
	"Contract": None,
}


def _resolve_other_party(related_doctype, related_name, my_freelancer, my_employer):
	"""Given the record a conversation is about, work out who the *other*
	party is: if I'm the employer messaging in about a Gig, the other party
	is that Gig's freelancer; if I'm the freelancer messaging in about a Job
	Posting, the other party is that job's employer; for a Contract either
	side may be starting the conversation, so resolve whichever profile on
	it isn't me."""
	if related_doctype == "Contract":
		contract = frappe.db.get_value("Contract", related_name, ["freelancer", "employer"], as_dict=True)
		if not contract:
			frappe.throw(_("Contract not found."))
		if my_freelancer and contract.freelancer == my_freelancer:
			return contract.employer, "Employer Profile"
		if my_employer and contract.employer == my_employer:
			return contract.freelancer, "Freelancer Profile"
		frappe.throw(_("You aren't a party to this contract."))

	owner_field = RELATED_OWNER_FIELD.get(related_doctype)
	if not owner_field:
		frappe.throw(_("Unsupported conversation subject."))
	owner_profile_type = "Freelancer Profile" if owner_field == "freelancer" else "Employer Profile"
	owner = frappe.db.get_value(related_doctype, related_name, owner_field)
	if not owner:
		frappe.throw(_("{0} not found.").format(related_doctype))
	return owner, owner_profile_type


@frappe.whitelist()
def start_conversation(related_doctype, related_name):
	user = frappe.session.user
	my_freelancer = get_freelancer_profile(user)
	my_employer = get_employer_profile(user)
	if not my_freelancer and not my_employer:
		frappe.throw(_("Complete your profile before messaging anyone."))

	other_profile, other_profile_type = _resolve_other_party(related_doctype, related_name, my_freelancer, my_employer)

	if other_profile_type == "Freelancer Profile":
		if other_profile == my_freelancer:
			frappe.throw(_("You can't message yourself."))
		employer_profile, freelancer_profile = my_employer, other_profile
	else:
		if other_profile == my_employer:
			frappe.throw(_("You can't message yourself."))
		employer_profile, freelancer_profile = other_profile, my_freelancer

	if not employer_profile or not freelancer_profile:
		frappe.throw(_("Both an employer and a freelancer profile are needed to start a conversation."))

	existing = frappe.db.get_value(
		"Conversation",
		{
			"employer_profile": employer_profile,
			"freelancer_profile": freelancer_profile,
			"related_doctype": related_doctype,
			"related_name": related_name,
		},
		"name",
	)
	if existing:
		return existing

	conversation = frappe.get_doc(
		{
			"doctype": "Conversation",
			"employer_profile": employer_profile,
			"freelancer_profile": freelancer_profile,
			"related_doctype": related_doctype,
			"related_name": related_name,
		}
	)
	conversation.insert(ignore_permissions=True)
	return conversation.name


def _my_role_in(conversation):
	user = frappe.session.user
	if conversation.employer_profile == get_employer_profile(user):
		return "Employer"
	if conversation.freelancer_profile == get_freelancer_profile(user):
		return "Freelancer"
	frappe.throw(_("You aren't a party to this conversation."), frappe.PermissionError)


@frappe.whitelist()
def send_message(conversation, body):
	body = (body or "").strip()
	if not body:
		frappe.throw(_("Message can't be empty."))

	convo = frappe.get_doc("Conversation", conversation)
	role = _my_role_in(convo)

	message = frappe.get_doc(
		{
			"doctype": "Message",
			"conversation": convo.name,
			"sender_user": frappe.session.user,
			"sender_type": role,
			"body": body,
			"sent_at": now_datetime(),
		}
	)
	message.insert(ignore_permissions=True)

	from worcent.worcent_core.notify import notify

	recipient_user = frappe.db.get_value(
		"Freelancer Profile" if role == "Employer" else "Employer Profile",
		convo.freelancer_profile if role == "Employer" else convo.employer_profile,
		"user",
	)
	if recipient_user:
		notify(
			recipient_user,
			_("New message"),
			_("You have a new message: {0}").format(body[:120]),
			reference_doctype="Conversation",
			reference_name=convo.name,
		)

	return message.name


@frappe.whitelist()
def get_messages(conversation, after=None):
	convo = frappe.get_doc("Conversation", conversation)
	_my_role_in(convo)

	filters = {"conversation": convo.name}
	if after:
		filters["sent_at"] = [">", after]

	messages = frappe.get_all(
		"Message",
		filters=filters,
		fields=["name", "sender_user", "sender_type", "body", "sent_at"],
		order_by="sent_at asc",
		limit_page_length=200,
	)
	for m in messages:
		m["is_mine"] = m.sender_user == frappe.session.user
	return messages


@frappe.whitelist()
def mark_read(conversation):
	convo = frappe.get_doc("Conversation", conversation)
	role = _my_role_in(convo)

	other_role = "Freelancer" if role == "Employer" else "Employer"
	frappe.db.set_value("Message", {"conversation": convo.name, "sender_type": other_role}, "read_by_recipient", 1)
	frappe.db.set_value(
		"Conversation", convo.name,
		"employer_unread_count" if role == "Employer" else "freelancer_unread_count",
		0,
	)


@frappe.whitelist()
def list_my_conversations():
	user = frappe.session.user
	freelancer = get_freelancer_profile(user)
	employer = get_employer_profile(user)

	filters = []
	if freelancer:
		filters.append(["freelancer_profile", "=", freelancer])
	if employer:
		filters.append(["employer_profile", "=", employer])
	if not filters:
		return []

	or_filters = {}
	if freelancer:
		or_filters["freelancer_profile"] = freelancer
	if employer:
		or_filters["employer_profile"] = employer

	conversations = frappe.get_all(
		"Conversation",
		or_filters=or_filters,
		fields=[
			"name", "employer_profile", "freelancer_profile", "related_doctype", "related_name",
			"last_message_at", "employer_unread_count", "freelancer_unread_count",
		],
		order_by="last_message_at desc",
		limit_page_length=100,
	)
	for c in conversations:
		c["my_unread"] = c.employer_unread_count if employer and c.employer_profile == employer else c.freelancer_unread_count
		c["other_party_name"] = (
			frappe.db.get_value("Freelancer Profile", c.freelancer_profile, "display_name")
			if employer and c.employer_profile == employer
			else frappe.db.get_value("Employer Profile", c.employer_profile, "company_name")
		)
	return conversations
