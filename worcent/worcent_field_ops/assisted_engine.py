import re

import frappe
from frappe import _


def _synthetic_email(requester_phone, requester_name):
	digits = re.sub(r"\D", "", requester_phone or "") or "0000"
	base = f"assisted.{digits}@worcent.local"
	if not frappe.db.exists("User", base):
		return base
	n = 2
	while frappe.db.exists("User", f"assisted.{digits}.{n}@worcent.local"):
		n += 1
	return f"assisted.{digits}.{n}@worcent.local"


def _ensure_assisted_user(requester_name, requester_phone, role):
	"""A field rep is signing this person up on their behalf -- they may have
	no email at all (that's the whole point of the assisted-request flow), so
	we synthesize a placeholder login tied to their phone number rather than
	blocking on one."""
	existing = frappe.db.get_value("User", {"mobile_no": requester_phone, "enabled": 1}, "name")
	if existing:
		if role not in [r.role for r in frappe.get_doc("User", existing).roles]:
			user = frappe.get_doc("User", existing)
			user.append("roles", {"role": role})
			user.save(ignore_permissions=True)
		return existing

	email = _synthetic_email(requester_phone, requester_name)
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": requester_name,
			"mobile_no": requester_phone,
			"send_welcome_email": 0,
		}
	)
	user.append("roles", {"role": role})
	user.insert(ignore_permissions=True)
	return user.name


@frappe.whitelist()
def convert_assisted_request(assisted_request_name):
	req = frappe.get_doc("Assisted Request", assisted_request_name)
	if req.status == "Converted":
		frappe.throw(_("This request has already been converted."))

	rep_user = frappe.db.get_value("Rep", req.rep, "user")
	if frappe.session.user != "Administrator" and "Worcent Admin" not in frappe.get_roles() and frappe.session.user != rep_user:
		frappe.throw(_("Only the assigned Rep can convert this request."))

	if req.request_type == "Register as Freelancer":
		result = _convert_register_as_freelancer(req)
	elif req.request_type == "Post Job":
		result = _convert_post_job(req)
	elif req.request_type == "Apply to Job":
		result = _convert_apply_to_job(req)
	else:
		frappe.throw(_("Unknown request type: {0}").format(req.request_type))

	req.converted_to_doctype = result.doctype
	req.converted_to_name = result.name
	req.status = "Converted"
	req.save(ignore_permissions=True)
	return {"doctype": result.doctype, "name": result.name}


def _convert_register_as_freelancer(req):
	user_name = _ensure_assisted_user(req.requester_name, req.requester_phone, "Freelancer")
	existing = frappe.db.get_value("Freelancer Profile", {"user": user_name}, "name")
	if existing:
		return frappe.get_doc("Freelancer Profile", existing)

	profile = frappe.get_doc(
		{
			"doctype": "Freelancer Profile",
			"user": user_name,
			"headline": (req.details or "")[:140] or f"Freelancer registered via {req.rep}",
			"bio": req.details,
		}
	)
	profile.insert(ignore_permissions=True)
	return profile


def _convert_post_job(req):
	user_name = _ensure_assisted_user(req.requester_name, req.requester_phone, "Employer")
	employer = frappe.db.get_value("Employer Profile", {"user": user_name}, "name")
	if not employer:
		employer_doc = frappe.get_doc(
			{"doctype": "Employer Profile", "user": user_name, "company_name": req.requester_name}
		)
		employer_doc.insert(ignore_permissions=True)
		employer = employer_doc.name

	job = frappe.get_doc(
		{
			"doctype": "Job Posting",
			"title": ((req.details or "").splitlines()[0][:140] if req.details else None) or "Job posted via field rep",
			"employer": employer,
			"budget_type": "Fixed",
			"description": req.details,
			"status": "Open",
			"published": 0,
			"posted_via_rep": req.rep,
		}
	)
	job.insert(ignore_permissions=True)
	return job


def _convert_apply_to_job(req):
	if not req.related_job_posting:
		frappe.throw(_("Set the Related Job Posting before converting an \"Apply to Job\" request."))

	user_name = _ensure_assisted_user(req.requester_name, req.requester_phone, "Freelancer")
	freelancer = frappe.db.get_value("Freelancer Profile", {"user": user_name}, "name")
	if not freelancer:
		profile = frappe.get_doc(
			{"doctype": "Freelancer Profile", "user": user_name, "headline": f"Freelancer registered via {req.rep}"}
		)
		profile.insert(ignore_permissions=True)
		freelancer = profile.name

	job = frappe.get_doc("Job Posting", req.related_job_posting)
	proposal = frappe.get_doc(
		{
			"doctype": "Proposal",
			"job_posting": job.name,
			"freelancer": freelancer,
			"bid_amount": job.budget_min or job.budget_max or 0,
			"delivery_days": 14,
			"cover_letter": req.details or f"Applied on the requester's behalf via field rep {req.rep}.",
		}
	)
	proposal.flags.ignore_owner_check = True
	proposal.insert(ignore_permissions=True)
	return proposal
