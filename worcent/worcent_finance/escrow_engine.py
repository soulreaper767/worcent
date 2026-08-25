import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from worcent.worcent_core.wallet_utils import ensure_wallet
from worcent.worcent_finance.commission_engine import get_employer_fee_rate, get_freelancer_commission_rate


def _wallet_txn(wallet_name, transaction_type, direction, amount, balance_after, reference_doctype=None, reference_name=None, remarks=None):
	frappe.get_doc(
		{
			"doctype": "Wallet Transaction",
			"wallet": wallet_name,
			"transaction_type": transaction_type,
			"direction": direction,
			"amount": amount,
			"balance_after": balance_after,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"remarks": remarks,
		}
	).insert(ignore_permissions=True)


def fund_milestone(milestone_name):
	"""Employer funds a milestone: debit their wallet, hold amount in escrow."""
	milestone = frappe.get_doc("Milestone", milestone_name)
	contract = frappe.get_doc("Contract", milestone.contract)

	employer_wallet = frappe.get_doc("Wallet", ensure_wallet("Employer Profile", contract.employer))
	if flt(employer_wallet.balance) < flt(milestone.amount):
		frappe.throw(_("Insufficient wallet balance to fund this milestone. Top up your wallet first."))

	employer_wallet.balance = flt(employer_wallet.balance) - flt(milestone.amount)
	employer_wallet.held_in_escrow = flt(employer_wallet.held_in_escrow) + flt(milestone.amount)
	employer_wallet.save(ignore_permissions=True)

	_wallet_txn(
		employer_wallet.name, "Escrow Fund", "Debit", milestone.amount, employer_wallet.balance,
		"Milestone", milestone.name,
	)

	escrow = frappe.get_doc(
		{"doctype": "Escrow Transaction", "milestone": milestone.name, "amount": milestone.amount, "status": "Held"}
	).insert(ignore_permissions=True)

	milestone.db_set("status", "Funded")
	milestone.db_set("funded_on", now_datetime())
	return escrow.name


def release_milestone(milestone_name):
	"""Client approves (or auto-release fires): pay freelancer net of
	commission, deduct employer marketplace fee, close out escrow."""
	milestone = frappe.get_doc("Milestone", milestone_name)
	contract = frappe.get_doc("Contract", milestone.contract)
	escrow = frappe.get_doc("Escrow Transaction", {"milestone": milestone.name, "status": "Held"})

	employer_wallet = frappe.get_doc("Wallet", ensure_wallet("Employer Profile", contract.employer))
	employer_wallet.held_in_escrow = flt(employer_wallet.held_in_escrow) - flt(milestone.amount)
	employer_wallet.save(ignore_permissions=True)

	freelancer_rate = get_freelancer_commission_rate(contract.freelancer, contract.employer)
	employer_rate = get_employer_fee_rate(contract.employer)
	commission_amount = flt(milestone.amount) * freelancer_rate / 100
	employer_fee_amount = flt(milestone.amount) * employer_rate / 100
	net_amount = flt(milestone.amount) - commission_amount

	freelancer_wallet = frappe.get_doc("Wallet", ensure_wallet("Freelancer Profile", contract.freelancer))
	freelancer_wallet.balance = flt(freelancer_wallet.balance) + net_amount
	freelancer_wallet.save(ignore_permissions=True)

	_wallet_txn(
		freelancer_wallet.name, "Milestone Release", "Credit", net_amount, freelancer_wallet.balance,
		"Milestone", milestone.name, remarks=f"Commission {freelancer_rate}% deducted",
	)

	escrow.status = "Released"
	escrow.released_on = now_datetime()
	escrow.save(ignore_permissions=True)

	milestone.db_set("status", "Released")
	milestone.db_set("released_on", now_datetime())

	frappe.db.set_value("Contract", contract.name, "total_billed", flt(contract.total_billed) + flt(milestone.amount))
	frappe.db.set_value(
		"Freelancer Profile", contract.freelancer, "total_earned",
		flt(frappe.db.get_value("Freelancer Profile", contract.freelancer, "total_earned")) + net_amount,
	)
	frappe.db.set_value(
		"Employer Profile", contract.employer, "total_spent",
		flt(frappe.db.get_value("Employer Profile", contract.employer, "total_spent")) + flt(milestone.amount),
	)

	return {
		"freelancer_rate": freelancer_rate,
		"employer_rate": employer_rate,
		"commission_amount": commission_amount,
		"employer_fee_amount": employer_fee_amount,
		"net_amount": net_amount,
	}


def refund_milestone(milestone_name):
	"""Full refund to employer (e.g. dispute resolved in employer's favour)."""
	milestone = frappe.get_doc("Milestone", milestone_name)
	contract = frappe.get_doc("Contract", milestone.contract)
	escrow = frappe.get_doc("Escrow Transaction", {"milestone": milestone.name, "status": "Held"})

	employer_wallet = frappe.get_doc("Wallet", ensure_wallet("Employer Profile", contract.employer))
	employer_wallet.held_in_escrow = flt(employer_wallet.held_in_escrow) - flt(milestone.amount)
	employer_wallet.balance = flt(employer_wallet.balance) + flt(milestone.amount)
	employer_wallet.save(ignore_permissions=True)

	_wallet_txn(
		employer_wallet.name, "Escrow Refund", "Credit", milestone.amount, employer_wallet.balance,
		"Milestone", milestone.name, remarks="Dispute resolved in employer's favour",
	)

	escrow.status = "Refunded"
	escrow.released_on = now_datetime()
	escrow.save(ignore_permissions=True)
	milestone.db_set("status", "Pending")


def split_milestone(milestone_name, freelancer_percent, remarks=None):
	"""Partial release for a split dispute resolution: freelancer_percent% of
	the milestone (net of commission) to the freelancer, the rest refunded
	to the employer."""
	milestone = frappe.get_doc("Milestone", milestone_name)
	contract = frappe.get_doc("Contract", milestone.contract)
	escrow = frappe.get_doc("Escrow Transaction", {"milestone": milestone.name, "status": "Held"})

	freelancer_amount = flt(milestone.amount) * flt(freelancer_percent) / 100
	employer_refund = flt(milestone.amount) - freelancer_amount

	employer_wallet = frappe.get_doc("Wallet", ensure_wallet("Employer Profile", contract.employer))
	employer_wallet.held_in_escrow = flt(employer_wallet.held_in_escrow) - flt(milestone.amount)
	employer_wallet.balance = flt(employer_wallet.balance) + employer_refund
	employer_wallet.save(ignore_permissions=True)
	if employer_refund:
		_wallet_txn(
			employer_wallet.name, "Escrow Refund", "Credit", employer_refund, employer_wallet.balance,
			"Milestone", milestone.name, remarks=remarks or "Dispute split resolution",
		)

	if freelancer_amount:
		rate = get_freelancer_commission_rate(contract.freelancer, contract.employer)
		net = freelancer_amount - (freelancer_amount * rate / 100)
		freelancer_wallet = frappe.get_doc("Wallet", ensure_wallet("Freelancer Profile", contract.freelancer))
		freelancer_wallet.balance = flt(freelancer_wallet.balance) + net
		freelancer_wallet.save(ignore_permissions=True)
		_wallet_txn(
			freelancer_wallet.name, "Milestone Release", "Credit", net, freelancer_wallet.balance,
			"Milestone", milestone.name, remarks=remarks or "Dispute split resolution",
		)

	escrow.status = "Released"
	escrow.released_on = now_datetime()
	escrow.save(ignore_permissions=True)
	milestone.db_set("status", "Released")
	milestone.db_set("released_on", now_datetime())


def auto_release_overdue_milestones():
	"""Scheduled daily: a Milestone whose Work Submission has sat awaiting
	client review past the configured window auto-releases, same as
	Upwork/Freelancer.com's "no action = approved" rule."""
	days = frappe.db.get_single_value("Worcent Settings", "escrow_auto_release_days") or 14
	cutoff = frappe.utils.add_days(frappe.utils.now_datetime(), -days)

	overdue_milestones = frappe.get_all(
		"Work Submission",
		filters={"status": "Submitted", "submitted_on": ["<=", cutoff]},
		pluck="milestone",
	)
	for milestone_name in set(overdue_milestones):
		if frappe.db.get_value("Milestone", milestone_name, "status") == "Submitted":
			release_milestone(milestone_name)
