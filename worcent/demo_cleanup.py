"""Wipes every demo record this app ever seeds, and nothing else. Reachable
only from the Worcent Admin Tools desk page (System Manager/Worcent Admin),
with a client-side confirmation first since this is a real, irreversible
delete of real rows.

Never touches master/reference data: Skill Category, Commission Slab,
Employer Plan, Insurance Plan, Premium Subscription Plan, Ticket Category,
Badge, Skill Challenge, Letter Head, Currency Exchange Rate, Fiscal Year,
Company, Customer/Supplier Groups, Referral Program -- none of that is
demo *data*, it's the platform's own configuration, and deleting it would
break the site rather than just clear test content.
"""

import frappe

DEMO_EMAIL_PATTERN = "%.demo@worcent.test"

ADMIN_ROLES = {"Worcent Admin", "System Manager"}


def _require_admin():
	if frappe.session.user != "Administrator" and not ADMIN_ROLES.intersection(frappe.get_roles()):
		frappe.throw(frappe._("Only a System Manager or Worcent Admin can remove demo data."))


@frappe.whitelist()
def remove_demo_data():
	_require_admin()

	demo_users = frappe.get_all("User", filters={"email": ["like", DEMO_EMAIL_PATTERN]}, pluck="name")
	if not demo_users:
		return {"deleted": 0, "message": "No demo users found -- nothing to remove."}

	try:
		counts = _delete_everything_for(demo_users)
		frappe.db.commit()
		return {"deleted": sum(counts.values()), "breakdown": counts}
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="Worcent demo data removal failed", message=frappe.get_traceback())
		frappe.throw(frappe._("Removing demo data failed partway through -- nothing was changed (rolled back). See Error Log for details."))


def _delete_where(doctype, filters, counts):
	names = frappe.get_all(doctype, filters=filters, pluck="name")
	for name in names:
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True, ignore_missing=True)
	if names:
		counts[doctype] = counts.get(doctype, 0) + len(names)


def _cancel_and_delete_journal_entries(parties, counts):
	"""Journal Entries are submitted documents -- delete_doc() refuses to
	remove a submitted doc even with force=True, so these have to be
	cancelled first. Found via GL Entry (auto-created on submit), which
	carries the party directly, rather than digging through each JE's
	child table.

	ERPNext keeps GL Entry rows around as an audit trail even after the
	source Journal Entry is cancelled and deleted (cancelling posts
	reversal GL Entries rather than removing the originals) -- fine for
	real accounting, not what we want for demo data, so both the original
	and reversal GL Entry rows for these vouchers are purged directly
	after the Journal Entry itself is gone."""
	if not parties:
		return
	voucher_names = set(frappe.get_all(
		"GL Entry", filters={"party": ["in", parties], "voucher_type": "Journal Entry"},
		pluck="voucher_no", distinct=True,
	))
	for name in voucher_names:
		if not frappe.db.exists("Journal Entry", name):
			continue
		je = frappe.get_doc("Journal Entry", name)
		if je.docstatus == 1:
			je.cancel()
		frappe.delete_doc("Journal Entry", name, force=True, ignore_permissions=True, ignore_missing=True)
	if voucher_names:
		counts["Journal Entry"] = counts.get("Journal Entry", 0) + len(voucher_names)
		deleted_gl = frappe.db.count("GL Entry", {"voucher_no": ["in", list(voucher_names)]})
		frappe.db.delete("GL Entry", {"voucher_no": ["in", list(voucher_names)]})
		if deleted_gl:
			counts["GL Entry"] = counts.get("GL Entry", 0) + deleted_gl


def _delete_everything_for(demo_users):
	counts = {}

	freelancers = frappe.get_all("Freelancer Profile", filters={"user": ["in", demo_users]}, pluck="name")
	employers = frappe.get_all("Employer Profile", filters={"user": ["in", demo_users]}, pluck="name")
	employees = frappe.get_all("Employee", filters={"user_id": ["in", demo_users]}, pluck="name")
	offices = frappe.get_all("Office", filters={"manager": ["in", employees or [""]]}, pluck="name") if employees else []
	reps = frappe.get_all("Rep", filters={"employee": ["in", employees or [""]]}, pluck="name") if employees else []
	all_offices = list(set(offices) | set(frappe.get_all("Office", filters={"franchisee_user": ["in", demo_users]}, pluck="name")))
	if reps:
		all_offices = list(set(all_offices) | set(frappe.get_all("Rep", filters={"name": ["in", reps]}, pluck="office")))
	agencies = frappe.get_all("Agency", filters={"owner_user": ["in", demo_users]}, pluck="name")

	contracts = list(set(
		frappe.get_all("Contract", filters={"freelancer": ["in", freelancers or [""]]}, pluck="name")
		+ frappe.get_all("Contract", filters={"employer": ["in", employers or [""]]}, pluck="name")
	))
	milestones = frappe.get_all("Milestone", filters={"contract": ["in", contracts or [""]]}, pluck="name") if contracts else []

	# --- children before parents ---
	_delete_where("Wallet Transaction", {"wallet": ["in", frappe.get_all(
		"Wallet", filters={"party": ["in", freelancers + employers or [""]]}, pluck="name") or [""]]}, counts)
	_delete_where("Platform Earning", {"party": ["in", freelancers + employers or [""]]}, counts)
	_delete_where("Escrow Transaction", {"milestone": ["in", milestones or [""]]}, counts)
	_delete_where("Work Submission", {"milestone": ["in", milestones or [""]]}, counts)
	_delete_where("Time Log", {"contract": ["in", contracts or [""]]}, counts)
	_delete_where("Review", {"contract": ["in", contracts or [""]]}, counts)
	_delete_where("Dispute Evidence", {"parent": ["in", frappe.get_all(
		"Dispute Case", filters={"contract": ["in", contracts or [""]]}, pluck="name") or [""]]}, counts)
	_delete_where("Dispute Case", {"contract": ["in", contracts or [""]]}, counts)
	_delete_where("Milestone", {"name": ["in", milestones or [""]]}, counts)
	_delete_where("Message", {"conversation": ["in", frappe.get_all(
		"Conversation", filters={"freelancer_profile": ["in", freelancers or [""]]}, pluck="name")
		+ frappe.get_all("Conversation", filters={"employer_profile": ["in", employers or [""]]}, pluck="name") or [""]]}, counts)
	_delete_where("Conversation", {"freelancer_profile": ["in", freelancers or [""]]}, counts)
	_delete_where("Conversation", {"employer_profile": ["in", employers or [""]]}, counts)
	_delete_where("Saved Item", {"user": ["in", demo_users]}, counts)
	_delete_where("Growth Tool Result", {"user": ["in", demo_users]}, counts)
	_delete_where("Skill Challenge Enrollment", {"user": ["in", demo_users]}, counts)
	_delete_where("Support Ticket Reply", {"ticket": ["in", frappe.get_all(
		"Support Ticket", filters={"raised_by": ["in", demo_users]}, pluck="name") or [""]]}, counts)
	_delete_where("Support Ticket", {"raised_by": ["in", demo_users]}, counts)
	_delete_where("Contract", {"name": ["in", contracts or [""]]}, counts)
	_delete_where("Proposal", {"freelancer": ["in", freelancers or [""]]}, counts)
	_delete_where("Gig", {"freelancer": ["in", freelancers or [""]]}, counts)
	_delete_where("Job Posting", {"employer": ["in", employers or [""]]}, counts)
	_delete_where("Referral", {"referred_profile": ["in", freelancers + employers or [""]]}, counts)
	_delete_where("Referral Code", {"owner_user": ["in", demo_users]}, counts)
	_delete_where("Rank Application", {"freelancer": ["in", freelancers or [""]]}, counts)
	_delete_where("Mentorship Request", {"mentee": ["in", freelancers or [""]]}, counts)
	_delete_where("Mentor Program", {"mentor": ["in", freelancers or [""]]}, counts)
	_delete_where("Industry Guru", {"freelancer": ["in", freelancers or [""]]}, counts)
	_delete_where("Freelancer Badge", {"parent": ["in", freelancers or [""]]}, counts)
	_delete_where("Agency Membership", {"freelancer": ["in", freelancers or [""]]}, counts)
	_delete_where("Agency", {"name": ["in", agencies or [""]]}, counts)
	_delete_where("Physical Verification Appointment", {"party": ["in", freelancers + employers or [""]]}, counts)
	_delete_where("Verification Request", {"party": ["in", freelancers + employers or [""]]}, counts)
	_delete_where("Assisted Request", {"rep": ["in", reps or [""]]}, counts)
	_delete_where("Franchise Settlement", {"office": ["in", all_offices or [""]]}, counts)
	_delete_where("Withdrawal Request", {"wallet": ["in", frappe.get_all(
		"Wallet", filters={"party": ["in", freelancers + employers or [""]]}, pluck="name") or [""]]}, counts)
	_delete_where("Advance Request", {"freelancer": ["in", freelancers or [""]]}, counts)
	_delete_where("Insurance Claim", {"policy": ["in", frappe.get_all(
		"Insurance Policy", filters={"freelancer": ["in", freelancers or [""]]}, pluck="name") or [""]]}, counts)
	_delete_where("Insurance Policy", {"freelancer": ["in", freelancers or [""]]}, counts)
	_delete_where("Premium Subscription", {"user": ["in", demo_users]}, counts)
	_delete_where("Wallet Top Up", {"wallet": ["in", frappe.get_all(
		"Wallet", filters={"party": ["in", freelancers + employers or [""]]}, pluck="name") or [""]]}, counts)
	_delete_where("Payout Account", {"party": ["in", freelancers + employers or [""]]}, counts)
	_delete_where("Wallet", {"party": ["in", freelancers + employers or [""]]}, counts)
	_delete_where("Rep", {"name": ["in", reps or [""]]}, counts)
	_delete_where("Office", {"name": ["in", all_offices or [""]]}, counts)
	_delete_where("Employee", {"name": ["in", employees or [""]]}, counts)

	# Auto-created ERPNext Customer/Supplier parties + the Journal Entries
	# posted against them (accounting_engine.py's GL mirror)
	suppliers = [s for s in frappe.get_all("Freelancer Profile", filters={"user": ["in", demo_users]}, pluck="erp_supplier") if s]
	customers = [c for c in frappe.get_all("Employer Profile", filters={"user": ["in", demo_users]}, pluck="erp_customer") if c]
	_cancel_and_delete_journal_entries(suppliers + customers, counts)
	_delete_where("Supplier", {"name": ["in", suppliers or [""]]}, counts)
	_delete_where("Customer", {"name": ["in", customers or [""]]}, counts)

	_delete_where("Freelancer Profile", {"user": ["in", demo_users]}, counts)
	_delete_where("Employer Profile", {"user": ["in", demo_users]}, counts)
	_delete_where("User", {"name": ["in", demo_users]}, counts)

	return counts
