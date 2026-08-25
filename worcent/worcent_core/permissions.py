import frappe


def _is_admin(user):
	return user == "Administrator" or "Worcent Admin" in frappe.get_roles(user)


def get_freelancer_profile(user):
	return frappe.db.get_value("Freelancer Profile", {"user": user}, "name")


def get_employer_profile(user):
	return frappe.db.get_value("Employer Profile", {"user": user}, "name")


def get_rep(user):
	return frappe.db.get_value("Rep", {"user": user}, "name")


def contract_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or "Finance Manager" in frappe.get_roles(user) or "Dispute Arbitrator" in frappe.get_roles(user):
		return ""
	freelancer = get_freelancer_profile(user)
	employer = get_employer_profile(user)
	parts = []
	if freelancer:
		parts.append(f"`tabContract`.freelancer = {frappe.db.escape(freelancer)}")
	if employer:
		parts.append(f"`tabContract`.employer = {frappe.db.escape(employer)}")
	if not parts:
		return "1=0"
	return "(" + " or ".join(parts) + ")"


def contract_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or "Finance Manager" in frappe.get_roles(user) or "Dispute Arbitrator" in frappe.get_roles(user):
		return True
	freelancer = get_freelancer_profile(user)
	employer = get_employer_profile(user)
	return doc.freelancer == freelancer or doc.employer == employer


def milestone_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or "Finance Manager" in frappe.get_roles(user):
		return ""
	freelancer = get_freelancer_profile(user)
	employer = get_employer_profile(user)
	parts = []
	if freelancer:
		parts.append(
			f"`tabMilestone`.contract in (select name from `tabContract` where freelancer = {frappe.db.escape(freelancer)})"
		)
	if employer:
		parts.append(
			f"`tabMilestone`.contract in (select name from `tabContract` where employer = {frappe.db.escape(employer)})"
		)
	if not parts:
		return "1=0"
	return "(" + " or ".join(parts) + ")"


def milestone_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or "Finance Manager" in frappe.get_roles(user):
		return True
	contract = frappe.db.get_value("Contract", doc.contract, ["freelancer", "employer"], as_dict=True)
	if not contract:
		return False
	freelancer = get_freelancer_profile(user)
	employer = get_employer_profile(user)
	return contract.freelancer == freelancer or contract.employer == employer


def wallet_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or "Finance Manager" in frappe.get_roles(user):
		return ""
	freelancer = get_freelancer_profile(user)
	employer = get_employer_profile(user)
	parts = []
	if freelancer:
		parts.append(f"`tabWallet`.party = {frappe.db.escape(freelancer)}")
	if employer:
		parts.append(f"`tabWallet`.party = {frappe.db.escape(employer)}")
	if not parts:
		return "1=0"
	return "(" + " or ".join(parts) + ")"


def wallet_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or "Finance Manager" in frappe.get_roles(user):
		return True
	freelancer = get_freelancer_profile(user)
	employer = get_employer_profile(user)
	return doc.party == freelancer or doc.party == employer


def support_ticket_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or "Support Agent" in frappe.get_roles(user):
		return ""
	return f"`tabSupport Ticket`.raised_by = {frappe.db.escape(user)}"


def support_ticket_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or "Support Agent" in frappe.get_roles(user):
		return True
	return doc.raised_by == user


def assisted_request_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or "Office Manager" in frappe.get_roles(user):
		return ""
	rep = get_rep(user)
	if not rep:
		return "1=0"
	return f"`tabAssisted Request`.rep = {frappe.db.escape(rep)}"


def assisted_request_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or "Office Manager" in frappe.get_roles(user):
		return True
	return doc.rep == get_rep(user)
