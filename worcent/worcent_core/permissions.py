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
	if _is_admin(user) or {"Finance Manager", "Dispute Arbitrator"}.intersection(frappe.get_roles(user)):
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
	if _is_admin(user) or {"Finance Manager", "Dispute Arbitrator"}.intersection(frappe.get_roles(user)):
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


FINANCE_STAFF_ROLES = {"Finance Manager", "Accounts Manager"}


def _finance_staff(user):
	return bool(FINANCE_STAFF_ROLES.intersection(frappe.get_roles(user)))


def _own_party_names(user):
	names = []
	freelancer = get_freelancer_profile(user)
	employer = get_employer_profile(user)
	if freelancer:
		names.append(freelancer)
	if employer:
		names.append(employer)
	return names


def wallet_transaction_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return ""
	parties = _own_party_names(user)
	if not parties:
		return "1=0"
	quoted = ", ".join(frappe.db.escape(p) for p in parties)
	return f"`tabWallet Transaction`.wallet in (select name from `tabWallet` where party in ({quoted}))"


def wallet_transaction_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return True
	party = frappe.db.get_value("Wallet", doc.wallet, "party")
	return party in _own_party_names(user)


def platform_earning_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return ""
	parties = _own_party_names(user)
	if not parties:
		return "1=0"
	quoted = ", ".join(frappe.db.escape(p) for p in parties)
	return f"`tabPlatform Earning`.party in ({quoted})"


def platform_earning_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return True
	return doc.party in _own_party_names(user)


def payout_account_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return ""
	parties = _own_party_names(user)
	if not parties:
		return "1=0"
	quoted = ", ".join(frappe.db.escape(p) for p in parties)
	return f"`tabPayout Account`.party in ({quoted})"


def payout_account_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return True
	return doc.party in _own_party_names(user)


def withdrawal_request_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return ""
	parties = _own_party_names(user)
	if not parties:
		return "1=0"
	quoted = ", ".join(frappe.db.escape(p) for p in parties)
	return f"`tabWithdrawal Request`.wallet in (select name from `tabWallet` where party in ({quoted}))"


def withdrawal_request_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return True
	party = frappe.db.get_value("Wallet", doc.wallet, "party")
	return party in _own_party_names(user)


def referral_code_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return ""
	return f"`tabReferral Code`.owner_user = {frappe.db.escape(user)}"


def referral_code_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return True
	return doc.owner_user == user


def referral_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return ""
	parties = _own_party_names(user)
	referred_clause = ""
	if parties:
		quoted = ", ".join(frappe.db.escape(p) for p in parties)
		referred_clause = f" or `tabReferral`.referred_profile in ({quoted})"
	return (
		f"(`tabReferral`.referral_code in (select name from `tabReferral Code` where owner_user = {frappe.db.escape(user)})"
		f"{referred_clause})"
	)


def referral_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return True
	owner_user = frappe.db.get_value("Referral Code", doc.referral_code, "owner_user")
	return owner_user == user or doc.referred_profile in _own_party_names(user)


def growth_tool_result_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user):
		return ""
	return f"`tabGrowth Tool Result`.user = {frappe.db.escape(user)}"


def growth_tool_result_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	return doc.user == user


def skill_challenge_enrollment_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user):
		return ""
	return f"`tabSkill Challenge Enrollment`.user = {frappe.db.escape(user)}"


def skill_challenge_enrollment_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	return doc.user == user


def _is_rank_reviewer(user):
	return "Rank Reviewer" in frappe.get_roles(user)


def rank_application_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or _is_rank_reviewer(user):
		return ""
	freelancer = get_freelancer_profile(user)
	if not freelancer:
		return "1=0"
	return f"`tabRank Application`.freelancer = {frappe.db.escape(freelancer)}"


def rank_application_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or _is_rank_reviewer(user):
		return True
	return doc.freelancer == get_freelancer_profile(user)


SUPPORT_STAFF_ROLES = {"Support Agent", "Worcent Admin"}


def _is_support_staff(user):
	return bool(SUPPORT_STAFF_ROLES.intersection(frappe.get_roles(user)))


def support_ticket_reply_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or _is_support_staff(user):
		return ""
	return (
		f"`tabSupport Ticket Reply`.ticket in "
		f"(select name from `tabSupport Ticket` where raised_by = {frappe.db.escape(user)}) "
		f"and `tabSupport Ticket Reply`.is_internal_note = 0"
	)


def support_ticket_reply_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or _is_support_staff(user):
		return True
	if doc.is_internal_note:
		return False
	return frappe.db.get_value("Support Ticket", doc.ticket, "raised_by") == user
