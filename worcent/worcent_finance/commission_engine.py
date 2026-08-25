import frappe
from frappe.utils import flt

DEFAULT_FREELANCER_RATE = 20
DEFAULT_EMPLOYER_RATE = 5


def get_freelancer_commission_rate(freelancer, employer):
	"""Tiered commission based on cumulative amount already released between
	this freelancer/employer pair (Upwork-style: rate drops as the
	relationship grows)."""
	cumulative = flt(
		frappe.db.sql(
			"""
			select coalesce(sum(et.amount), 0)
			from `tabEscrow Transaction` et
			join `tabMilestone` m on m.name = et.milestone
			join `tabContract` c on c.name = m.contract
			where c.freelancer = %s and c.employer = %s and et.status = 'Released'
			""",
			(freelancer, employer),
		)[0][0]
	)

	slabs = frappe.get_all(
		"Commission Slab", fields=["from_amount", "to_amount", "rate"], order_by="from_amount asc"
	)
	for slab in slabs:
		if cumulative >= flt(slab.from_amount) and (not slab.to_amount or cumulative < flt(slab.to_amount)):
			return flt(slab.rate)
	return DEFAULT_FREELANCER_RATE


def get_employer_fee_rate(employer):
	plan = frappe.db.get_value("Employer Profile", employer, "plan")
	if not plan:
		return DEFAULT_EMPLOYER_RATE
	rate = frappe.db.get_value("Employer Plan", plan, "marketplace_fee_rate")
	return flt(rate) if rate else DEFAULT_EMPLOYER_RATE
