import frappe
from frappe import _
from frappe.utils import add_days, today

from worcent.worcent_core.permissions import assert_not_suspended, get_employer_profile, get_freelancer_profile


@frappe.whitelist()
def submit_job_proposal(job_posting, bid_amount, delivery_days, cover_letter=None):
	freelancer = get_freelancer_profile(frappe.session.user)
	if not freelancer:
		frappe.throw(_("Complete your Freelancer Profile before applying."))
	assert_not_suspended("Freelancer Profile", freelancer)

	job = frappe.get_doc("Job Posting", job_posting)
	if job.status != "Open" or not job.published:
		frappe.throw(_("This job is no longer open for proposals."))

	if frappe.db.exists(
		"Proposal", {"job_posting": job_posting, "freelancer": freelancer, "status": ["not in", ["Withdrawn", "Rejected"]]}
	):
		frappe.throw(_("You've already applied to this job."))

	proposal = frappe.get_doc(
		{
			"doctype": "Proposal",
			"job_posting": job_posting,
			"freelancer": freelancer,
			"bid_amount": bid_amount,
			"delivery_days": delivery_days,
			"cover_letter": cover_letter,
		}
	)
	proposal.insert(ignore_permissions=True)
	return proposal.name


@frappe.whitelist()
def order_gig(gig, package_type, requirements_answer=None, selected_extras=None):
	"""Fiverr-style checkout: ordering a fixed-price gig package needs no
	seller review -- it goes straight to a Contract + funded Milestone,
	reusing the existing, already-tested escrow engine to actually charge
	the buyer's wallet (its own insufficient-balance error already tells
	them to top up)."""
	employer = get_employer_profile(frappe.session.user)
	if not employer:
		frappe.throw(_("Complete your Employer Profile before ordering a gig."))
	assert_not_suspended("Employer Profile", employer)

	gig_doc = frappe.get_doc("Gig", gig)
	if gig_doc.status != "Active" or not gig_doc.published:
		frappe.throw(_("This gig isn't available for orders right now."))

	package = next((p for p in gig_doc.packages if p.package_type == package_type), None)
	if not package:
		frappe.throw(_("Choose a valid package."))

	if package.requirements and not (requirements_answer or "").strip():
		frappe.throw(_("Please answer the seller's requirements before ordering: {0}").format(package.requirements))

	amount = package.price
	delivery_days = package.delivery_days or 7

	if isinstance(selected_extras, str):
		import json

		selected_extras = json.loads(selected_extras) if selected_extras else []
	extra_titles = []
	for extra in gig_doc.extras:
		if selected_extras and extra.title in selected_extras:
			amount += extra.price
			delivery_days = max(1, delivery_days - (extra.delivery_days_reduction or 0))
			extra_titles.append(extra.title)

	proposal = frappe.get_doc(
		{
			"doctype": "Proposal",
			"gig": gig,
			"package_type": package_type,
			"freelancer": gig_doc.freelancer,
			"bid_amount": amount,
			"delivery_days": delivery_days,
			"buyer_requirements_answer": requirements_answer,
			"status": "Accepted",
		}
	)
	proposal.flags.ignore_owner_check = True
	proposal.insert(ignore_permissions=True)

	contract = frappe.get_doc(
		{
			"doctype": "Contract",
			"gig": gig,
			"proposal": proposal.name,
			"freelancer": gig_doc.freelancer,
			"employer": employer,
			"contract_type": "Gig",
			"rate": amount,
			"status": "Active",
		}
	)
	contract.insert(ignore_permissions=True)

	title = gig_doc.title if not extra_titles else f"{gig_doc.title} (+{', '.join(extra_titles)})"
	milestone = frappe.get_doc(
		{
			"doctype": "Milestone",
			"contract": contract.name,
			"title": title,
			"amount": amount,
			"due_date": add_days(today(), delivery_days),
			"status": "Pending",
		}
	)
	milestone.insert(ignore_permissions=True)

	from worcent.worcent_finance.escrow_engine import fund_milestone

	fund_milestone(milestone.name)

	from worcent.worcent_core.notify import notify

	freelancer_user = frappe.db.get_value("Freelancer Profile", gig_doc.freelancer, "user")
	if freelancer_user:
		notify(
			freelancer_user,
			_("New order"),
			_("You have a new order on {0} ({1} package)").format(gig_doc.title, package_type),
			reference_doctype="Contract",
			reference_name=contract.name,
		)

	return {"contract": contract.name, "milestone": milestone.name, "amount": amount}
