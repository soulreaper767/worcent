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
	if ptype == "create":
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
	if ptype == "create":
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
	if ptype == "create":
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
	if ptype == "create":
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
	if ptype == "create":
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
	if ptype == "create":
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
	if ptype == "create":
		return True
	if doc.is_internal_note:
		return False
	return frappe.db.get_value("Support Ticket", doc.ticket, "raised_by") == user


def get_office_for_manager(user):
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return None
	return frappe.db.get_value("Office", {"manager": employee}, "name")


# --- Freelancer Profile / Employer Profile: read stays open (public marketplace
# directory, matches the public /freelancer //employer website pages), only
# writing/deleting is restricted to the profile's own owner. ---


def freelancer_profile_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	if ptype in ("write", "delete", "cancel"):
		return doc.user == user
	return True


def employer_profile_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	if ptype in ("write", "delete", "cancel"):
		return doc.user == user
	return True


# --- Gig / Job Posting: read stays open (public marketplace listings), only
# the owning freelancer/employer (or, for a Job Posting raised on someone's
# behalf, the Rep who posted it) can write. ---


def gig_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	if ptype in ("write", "delete", "cancel"):
		return doc.freelancer == get_freelancer_profile(user)
	return True


def job_posting_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	if ptype in ("write", "delete", "cancel"):
		if doc.employer == get_employer_profile(user):
			return True
		if doc.posted_via_rep and doc.posted_via_rep == get_rep(user):
			return True
		return False
	return True


# --- Proposal: a Freelancer only sees/edits their own proposals; an Employer
# only sees/edits proposals submitted against their own Job Postings. ---


def proposal_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user):
		return ""
	freelancer = get_freelancer_profile(user)
	employer = get_employer_profile(user)
	parts = []
	if freelancer:
		parts.append(f"`tabProposal`.freelancer = {frappe.db.escape(freelancer)}")
	if employer:
		parts.append(
			f"`tabProposal`.job_posting in (select name from `tabJob Posting` where employer = {frappe.db.escape(employer)})"
		)
	if not parts:
		return "1=0"
	return "(" + " or ".join(parts) + ")"


def proposal_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	if ptype == "create":
		return True
	freelancer = get_freelancer_profile(user)
	if doc.freelancer == freelancer:
		return True
	employer = get_employer_profile(user)
	if employer and doc.job_posting:
		return frappe.db.get_value("Job Posting", doc.job_posting, "employer") == employer
	return False


# --- Time Log: scoped to the contract's own freelancer/employer, same shape
# as milestone_query_conditions above. ---


def time_log_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user):
		return ""
	freelancer = get_freelancer_profile(user)
	employer = get_employer_profile(user)
	parts = []
	if freelancer:
		parts.append(
			f"`tabTime Log`.contract in (select name from `tabContract` where freelancer = {frappe.db.escape(freelancer)})"
		)
	if employer:
		parts.append(
			f"`tabTime Log`.contract in (select name from `tabContract` where employer = {frappe.db.escape(employer)})"
		)
	if not parts:
		return "1=0"
	return "(" + " or ".join(parts) + ")"


def time_log_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	if ptype == "create":
		return True
	contract = frappe.db.get_value("Contract", doc.contract, ["freelancer", "employer"], as_dict=True)
	if not contract:
		return False
	return contract.freelancer == get_freelancer_profile(user) or contract.employer == get_employer_profile(user)


# --- Physical Verification Appointment: the freelancer/employer being
# verified only sees their own appointment; a Field Rep only their own
# assigned appointments; an Office Manager only their own office's. ---


def physical_verification_appointment_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user):
		return ""
	rep = get_rep(user)
	office = get_office_for_manager(user)
	parties = _own_party_names(user)
	parts = []
	if rep:
		parts.append(f"`tabPhysical Verification Appointment`.rep = {frappe.db.escape(rep)}")
	if office:
		parts.append(f"`tabPhysical Verification Appointment`.office = {frappe.db.escape(office)}")
	if parties:
		quoted = ", ".join(frappe.db.escape(p) for p in parties)
		parts.append(f"`tabPhysical Verification Appointment`.party in ({quoted})")
	if not parts:
		return "1=0"
	return "(" + " or ".join(parts) + ")"


def physical_verification_appointment_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	if ptype == "create":
		return True
	if doc.rep and doc.rep == get_rep(user):
		return True
	if doc.office and doc.office == get_office_for_manager(user):
		return True
	return doc.party in _own_party_names(user)


# --- Rep: a Field Rep only sees their own record; an Office Manager only
# their own office's reps. ---


def rep_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user):
		return ""
	office = get_office_for_manager(user)
	parts = [f"`tabRep`.user = {frappe.db.escape(user)}"]
	if office:
		parts.append(f"`tabRep`.office = {frappe.db.escape(office)}")
	return "(" + " or ".join(parts) + ")"


def rep_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	if doc.user == user:
		return True
	return doc.office == get_office_for_manager(user)


# --- Insurance Policy / Insurance Claim: a Freelancer only sees/edits their
# own policy, and only their own claims (via the claim's policy). ---


def insurance_policy_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user):
		return ""
	freelancer = get_freelancer_profile(user)
	if not freelancer:
		return "1=0"
	return f"`tabInsurance Policy`.freelancer = {frappe.db.escape(freelancer)}"


def insurance_policy_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	if ptype == "create":
		return True
	return doc.freelancer == get_freelancer_profile(user)


def insurance_claim_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return ""
	freelancer = get_freelancer_profile(user)
	if not freelancer:
		return "1=0"
	return (
		f"`tabInsurance Claim`.policy in (select name from `tabInsurance Policy` where freelancer = "
		f"{frappe.db.escape(freelancer)})"
	)


def insurance_claim_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return True
	if ptype == "create":
		return True
	policy_freelancer = frappe.db.get_value("Insurance Policy", doc.policy, "freelancer")
	owns_it = policy_freelancer == get_freelancer_profile(user)
	if ptype in ("write", "delete", "cancel"):
		# Only Submitted status/amount/reason are self-service; anything under
		# review or decided is staff-only from here, same as an Insurance
		# Claim's status options moving straight to Approved/Rejected/Paid
		# with no wallet-crediting side effect coded in yet — a freelancer
		# must not be able to self-mark their own claim decided.
		return owns_it and doc.status == "Submitted"
	return owns_it


# --- Premium Subscription: a user only sees/edits their own. ---


def premium_subscription_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user):
		return ""
	return f"`tabPremium Subscription`.user = {frappe.db.escape(user)}"


def premium_subscription_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	return doc.user == user


# --- Dispute Case: visible to whoever raised it, either party on the
# underlying contract, or a Dispute Arbitrator/Admin. ---


def dispute_case_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or "Dispute Arbitrator" in frappe.get_roles(user):
		return ""
	freelancer = get_freelancer_profile(user)
	employer = get_employer_profile(user)
	parts = [f"`tabDispute Case`.raised_by = {frappe.db.escape(user)}"]
	if freelancer:
		parts.append(
			f"`tabDispute Case`.contract in (select name from `tabContract` where freelancer = {frappe.db.escape(freelancer)})"
		)
	if employer:
		parts.append(
			f"`tabDispute Case`.contract in (select name from `tabContract` where employer = {frappe.db.escape(employer)})"
		)
	return "(" + " or ".join(parts) + ")"


def dispute_case_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or "Dispute Arbitrator" in frappe.get_roles(user):
		return True
	if doc.raised_by == user:
		return True
	contract = frappe.db.get_value("Contract", doc.contract, ["freelancer", "employer"], as_dict=True)
	if not contract:
		return False
	return contract.freelancer == get_freelancer_profile(user) or contract.employer == get_employer_profile(user)


# --- Agency Membership: a Freelancer only sees their own membership history. ---


def agency_membership_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or "Agency Manager" in frappe.get_roles(user):
		return ""
	freelancer = get_freelancer_profile(user)
	if not freelancer:
		return "1=0"
	return f"`tabAgency Membership`.freelancer = {frappe.db.escape(freelancer)}"


def agency_membership_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or "Agency Manager" in frappe.get_roles(user):
		return True
	return doc.freelancer == get_freelancer_profile(user)


# --- Verification Request: a Freelancer/Employer only sees/edits their own
# verification requests, and only while still Pending. ---


def verification_request_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user):
		return ""
	parties = _own_party_names(user)
	if not parties:
		return "1=0"
	quoted = ", ".join(frappe.db.escape(p) for p in parties)
	return f"`tabVerification Request`.party in ({quoted})"


def verification_request_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	if ptype == "create":
		return True
	owns_it = doc.party in _own_party_names(user)
	if ptype in ("write", "delete", "cancel"):
		return owns_it and doc.status == "Pending"
	return owns_it


# --- Office / Franchise Settlement: an Office Manager or Field Rep only sees
# their own office; a Franchise Owner only their own franchised office(s) —
# this matters most for Franchise Settlement, which carries real revenue
# figures that shouldn't leak between competing franchisees. ---


def _offices_for_user(user):
	offices = set()
	office = get_office_for_manager(user)
	if office:
		offices.add(office)
	rep_office = get_rep_office(user)
	if rep_office:
		offices.add(rep_office)
	for o in frappe.get_all("Office", filters={"franchisee_user": user}, pluck="name"):
		offices.add(o)
	return offices


def get_rep_office(user):
	return frappe.db.get_value("Rep", {"user": user}, "office")


def office_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or "Office Managing Partner" in frappe.get_roles(user):
		return ""
	offices = _offices_for_user(user)
	if not offices:
		return "1=0"
	quoted = ", ".join(frappe.db.escape(o) for o in offices)
	return f"`tabOffice`.name in ({quoted})"


def office_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or "Office Managing Partner" in frappe.get_roles(user):
		return True
	return doc.name in _offices_for_user(user)


def franchise_settlement_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or {"Office Managing Partner", "Finance Manager", "Accounts Manager"}.intersection(frappe.get_roles(user)):
		return ""
	offices = _offices_for_user(user)
	if not offices:
		return "1=0"
	quoted = ", ".join(frappe.db.escape(o) for o in offices)
	return f"`tabFranchise Settlement`.office in ({quoted})"


def franchise_settlement_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or {"Office Managing Partner", "Finance Manager", "Accounts Manager"}.intersection(frappe.get_roles(user)):
		return True
	return doc.office in _offices_for_user(user)


# --- Mentor Program: read stays open (mentees need to browse mentors), only
# the mentor themselves can write. ---


def mentor_program_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	if ptype in ("write", "delete", "cancel"):
		return doc.mentor == get_freelancer_profile(user)
	return True


# --- Mentorship Request: visible/writable only to the mentee who requested
# it or the mentor it was requested from -- this is what actually gates the
# wallet-charging accept() action, since a mentee's funds move on accept. ---


def mentorship_request_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user):
		return ""
	freelancer = get_freelancer_profile(user)
	if not freelancer:
		return "1=0"
	return (
		f"(`tabMentorship Request`.mentee = {frappe.db.escape(freelancer)} or "
		f"`tabMentorship Request`.mentor_program in (select name from `tabMentor Program` where mentor = {frappe.db.escape(freelancer)}))"
	)


def mentorship_request_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	if ptype == "create":
		return True
	freelancer = get_freelancer_profile(user)
	if doc.mentee == freelancer:
		return True
	return frappe.db.get_value("Mentor Program", doc.mentor_program, "mentor") == freelancer


# --- Work Submission: only the freelancer/employer on the underlying
# contract can see or act on it (approving one is a money-adjacent review
# step even though the actual release only happens via Milestone). ---


def work_submission_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user):
		return ""
	freelancer = get_freelancer_profile(user)
	employer = get_employer_profile(user)
	parts = []
	if freelancer:
		parts.append(
			f"`tabWork Submission`.milestone in (select name from `tabMilestone` where contract in "
			f"(select name from `tabContract` where freelancer = {frappe.db.escape(freelancer)}))"
		)
	if employer:
		parts.append(
			f"`tabWork Submission`.milestone in (select name from `tabMilestone` where contract in "
			f"(select name from `tabContract` where employer = {frappe.db.escape(employer)}))"
		)
	if not parts:
		return "1=0"
	return "(" + " or ".join(parts) + ")"


def work_submission_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user):
		return True
	if ptype == "create":
		return True
	contract_name = frappe.db.get_value("Milestone", doc.milestone, "contract")
	contract = frappe.db.get_value("Contract", contract_name, ["freelancer", "employer"], as_dict=True)
	if not contract:
		return False
	return contract.freelancer == get_freelancer_profile(user) or contract.employer == get_employer_profile(user)


# --- Advance Request: a Freelancer only sees their own (loan amounts,
# interest rate and repayment schedule are private financial data). ---


def advance_request_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return ""
	freelancer = get_freelancer_profile(user)
	if not freelancer:
		return "1=0"
	return f"`tabAdvance Request`.freelancer = {frappe.db.escape(freelancer)}"


def advance_request_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return True
	if ptype == "create":
		return True
	return doc.freelancer == get_freelancer_profile(user)


# --- Wallet Top Up: a Freelancer/Employer only sees their own top-up
# requests (bank reference notes and amounts are private). ---


def wallet_top_up_query_conditions(user):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return ""
	parties = _own_party_names(user)
	if not parties:
		return "1=0"
	quoted = ", ".join(frappe.db.escape(p) for p in parties)
	return f"`tabWallet Top Up`.wallet in (select name from `tabWallet` where party in ({quoted}))"


def wallet_top_up_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_admin(user) or _finance_staff(user):
		return True
	if not doc.wallet:
		# A brand-new Wallet Top Up may not have its wallet resolved yet --
		# that happens in validate() (auto-creating one if needed), which
		# runs after this create-permission check. Ownership is enforced
		# there instead once doc.wallet actually exists.
		return True
	party = frappe.db.get_value("Wallet", doc.wallet, "party")
	return party in _own_party_names(user)
