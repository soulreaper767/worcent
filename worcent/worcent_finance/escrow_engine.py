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


def _record_earning(earning_type, amount, party_type=None, party=None, reference_doctype=None, reference_name=None, remarks=None):
	if not amount:
		return None
	earning = frappe.get_doc(
		{
			"doctype": "Platform Earning",
			"earning_type": earning_type,
			"amount": amount,
			"party_type": party_type,
			"party": party,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"remarks": remarks,
		}
	)
	earning.insert(ignore_permissions=True)
	return earning


def _recompute_completion(contract_name):
	totals = frappe.db.sql(
		"""select
			coalesce(sum(amount), 0) as total,
			coalesce(sum(case when status = 'Released' then amount else 0 end), 0) as released
		from `tabMilestone` where contract = %s""",
		contract_name,
		as_dict=True,
	)[0]
	percent = (flt(totals.released) / flt(totals.total) * 100) if totals.total else 0
	frappe.db.set_value("Contract", contract_name, "completion_percent", round(percent, 2))


def fund_milestone(milestone_name):
	"""Employer funds a milestone: they pay the milestone amount *plus* the
	platform's marketplace fee on top (charged and recognised as platform
	earning immediately — it isn't held in escrow and isn't refundable, same
	as a real payment-processing/service fee). Only the milestone amount
	itself goes into escrow, refundable to the employer if a dispute
	resolves in their favour."""
	milestone = frappe.get_doc("Milestone", milestone_name)
	contract = frappe.get_doc("Contract", milestone.contract)

	employer_rate = get_employer_fee_rate(contract.employer)
	fee_amount = flt(milestone.amount) * employer_rate / 100
	total_charge = flt(milestone.amount) + fee_amount

	employer_wallet = frappe.get_doc("Wallet", ensure_wallet("Employer Profile", contract.employer))
	if flt(employer_wallet.balance) < total_charge:
		frappe.throw(
			_("Insufficient wallet balance. This milestone needs {0} (includes a {1}% platform fee). Top up your wallet first.").format(
				frappe.utils.fmt_money(total_charge, currency="USD"), employer_rate
			)
		)

	employer_wallet.balance = flt(employer_wallet.balance) - total_charge
	employer_wallet.held_in_escrow = flt(employer_wallet.held_in_escrow) + flt(milestone.amount)
	employer_wallet.save(ignore_permissions=True)

	_wallet_txn(
		employer_wallet.name, "Escrow Fund", "Debit", milestone.amount, flt(employer_wallet.balance) + fee_amount,
		"Milestone", milestone.name, remarks="Milestone amount moved to escrow",
	)
	if fee_amount:
		_wallet_txn(
			employer_wallet.name, "Platform Fee", "Debit", fee_amount, employer_wallet.balance,
			"Milestone", milestone.name, remarks=f"Platform fee ({employer_rate}%)",
		)
		_record_earning(
			"Employer Fee", fee_amount, "Employer Profile", contract.employer,
			"Milestone", milestone.name, f"{employer_rate}% marketplace fee on milestone funding",
		)

	escrow = frappe.get_doc(
		{"doctype": "Escrow Transaction", "milestone": milestone.name, "amount": milestone.amount, "status": "Held"}
	).insert(ignore_permissions=True)

	milestone.db_set("status", "Funded")
	milestone.db_set("funded_on", now_datetime())
	return escrow.name


def release_milestone(milestone_name):
	"""Client approves (or auto-release fires): pay freelancer net of their
	commission, close out escrow, record the platform's commission earning
	and (if applicable) pay the referrer their cut of that earning."""
	milestone = frappe.get_doc("Milestone", milestone_name)
	contract = frappe.get_doc("Contract", milestone.contract)
	escrow = frappe.get_doc("Escrow Transaction", {"milestone": milestone.name, "status": "Held"})

	employer_wallet = frappe.get_doc("Wallet", ensure_wallet("Employer Profile", contract.employer))
	employer_wallet.held_in_escrow = flt(employer_wallet.held_in_escrow) - flt(milestone.amount)
	employer_wallet.save(ignore_permissions=True)

	freelancer_rate = get_freelancer_commission_rate(contract.freelancer, contract.employer)
	commission_amount = flt(milestone.amount) * freelancer_rate / 100
	net_amount = flt(milestone.amount) - commission_amount

	freelancer_wallet = frappe.get_doc("Wallet", ensure_wallet("Freelancer Profile", contract.freelancer))
	freelancer_wallet.balance = flt(freelancer_wallet.balance) + net_amount
	freelancer_wallet.save(ignore_permissions=True)

	_wallet_txn(
		freelancer_wallet.name, "Milestone Release", "Credit", net_amount, freelancer_wallet.balance,
		"Milestone", milestone.name, remarks=f"Commission {freelancer_rate}% deducted",
	)
	earning = _record_earning(
		"Freelancer Commission", commission_amount, "Freelancer Profile", contract.freelancer,
		"Milestone", milestone.name, f"{freelancer_rate}% commission on milestone release",
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

	if earning:
		from worcent.worcent_finance.referral_engine import maybe_pay_referrer_commission

		maybe_pay_referrer_commission("Freelancer Profile", contract.freelancer, earning.amount)

	_recompute_completion(contract.name)

	return {"freelancer_rate": freelancer_rate, "commission_amount": commission_amount, "net_amount": net_amount}


def refund_milestone(milestone_name):
	"""Refund the escrowed milestone amount to the employer (e.g. dispute
	resolved in their favour). The platform fee charged at funding time is
	NOT refunded — same as a real payment-processing fee."""
	milestone = frappe.get_doc("Milestone", milestone_name)
	contract = frappe.get_doc("Contract", milestone.contract)
	escrow = frappe.get_doc("Escrow Transaction", {"milestone": milestone.name, "status": "Held"})

	employer_wallet = frappe.get_doc("Wallet", ensure_wallet("Employer Profile", contract.employer))
	employer_wallet.held_in_escrow = flt(employer_wallet.held_in_escrow) - flt(milestone.amount)
	employer_wallet.balance = flt(employer_wallet.balance) + flt(milestone.amount)
	employer_wallet.save(ignore_permissions=True)

	_wallet_txn(
		employer_wallet.name, "Escrow Refund", "Credit", milestone.amount, employer_wallet.balance,
		"Milestone", milestone.name, remarks="Dispute resolved in employer's favour (platform fee not refunded)",
	)

	escrow.status = "Refunded"
	escrow.released_on = now_datetime()
	escrow.save(ignore_permissions=True)
	milestone.db_set("status", "Pending")

	_recompute_completion(contract.name)


def split_milestone(milestone_name, freelancer_percent, remarks=None):
	"""Partial release for a split dispute resolution: freelancer_percent% of
	the escrowed milestone amount (net of commission) to the freelancer, the
	rest refunded to the employer. Platform fee from funding is unaffected."""
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
		commission = freelancer_amount * rate / 100
		net = freelancer_amount - commission
		freelancer_wallet = frappe.get_doc("Wallet", ensure_wallet("Freelancer Profile", contract.freelancer))
		freelancer_wallet.balance = flt(freelancer_wallet.balance) + net
		freelancer_wallet.save(ignore_permissions=True)
		_wallet_txn(
			freelancer_wallet.name, "Milestone Release", "Credit", net, freelancer_wallet.balance,
			"Milestone", milestone.name, remarks=remarks or "Dispute split resolution",
		)
		_record_earning(
			"Freelancer Commission", commission, "Freelancer Profile", contract.freelancer,
			"Milestone", milestone.name, f"{rate}% commission on split-resolved milestone",
		)

	escrow.status = "Released"
	escrow.released_on = now_datetime()
	escrow.save(ignore_permissions=True)
	milestone.db_set("status", "Released")
	milestone.db_set("released_on", now_datetime())

	_recompute_completion(contract.name)


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
