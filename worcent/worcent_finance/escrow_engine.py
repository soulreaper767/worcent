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

	from worcent.worcent_finance.accounting_engine import record_milestone_fund

	record_milestone_fund(contract.employer, milestone.amount, fee_amount, milestone.name)

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

	from worcent.worcent_finance.accounting_engine import record_milestone_release

	record_milestone_release(contract.freelancer, milestone.amount, commission_amount, net_amount, milestone.name)

	from worcent.worcent_core.notify import notify

	freelancer_user = frappe.db.get_value("Freelancer Profile", contract.freelancer, "user")
	if freelancer_user:
		notify(
			freelancer_user, _("Payment released"),
			_("{0} was released to your wallet for {1}.").format(frappe.utils.fmt_money(net_amount, currency="USD"), milestone.title),
			reference_doctype="Milestone", reference_name=milestone.name,
		)

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

	from worcent.worcent_finance.accounting_engine import record_milestone_refund

	record_milestone_refund(contract.employer, milestone.amount, milestone.name)

	from worcent.worcent_core.notify import notify

	employer_user = frappe.db.get_value("Employer Profile", contract.employer, "user")
	if employer_user:
		notify(
			employer_user, _("Milestone refunded"),
			_("{0} was refunded to your wallet for {1}.").format(frappe.utils.fmt_money(milestone.amount, currency="USD"), milestone.title),
			reference_doctype="Milestone", reference_name=milestone.name,
		)


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

	commission_for_je = 0
	freelancer_net = 0

	if freelancer_amount:
		rate = get_freelancer_commission_rate(contract.freelancer, contract.employer)
		commission_for_je = freelancer_amount * rate / 100
		freelancer_net = freelancer_amount - commission_for_je
		freelancer_wallet = frappe.get_doc("Wallet", ensure_wallet("Freelancer Profile", contract.freelancer))
		freelancer_wallet.balance = flt(freelancer_wallet.balance) + freelancer_net
		freelancer_wallet.save(ignore_permissions=True)
		_wallet_txn(
			freelancer_wallet.name, "Milestone Release", "Credit", freelancer_net, freelancer_wallet.balance,
			"Milestone", milestone.name, remarks=remarks or "Dispute split resolution",
		)
		_record_earning(
			"Freelancer Commission", commission_for_je, "Freelancer Profile", contract.freelancer,
			"Milestone", milestone.name, f"{rate}% commission on split-resolved milestone",
		)

	escrow.status = "Released"
	escrow.released_on = now_datetime()
	escrow.save(ignore_permissions=True)
	milestone.db_set("status", "Released")
	milestone.db_set("released_on", now_datetime())

	_recompute_completion(contract.name)

	from worcent.worcent_finance.accounting_engine import record_milestone_split

	record_milestone_split(
		contract.employer, employer_refund, contract.freelancer,
		freelancer_net, commission_for_je, milestone.amount, milestone.name,
	)


def compute_resolution_reversal(dispute_name):
	"""Read-only: works out exactly what reversing a dispute's original
	milestone resolution would mean in plain numbers, so an admin can see
	the real impact before committing to it (an upheld appeal doesn't say
	what the *correct* outcome should have been -- only that the original
	one was wrong -- so reversing puts the money back into escrow, neutral,
	for a fresh decision, rather than guessing a replacement outcome).

	Known limitation: if the original release already triggered a referral
	commission payout to a third party, that payout is NOT reversed here --
	it's rare enough (an appeal on a milestone whose freelancer was also a
	referred user) to leave as a manual correction rather than risk
	compounding the reversal logic."""
	dispute = frappe.get_doc("Dispute Case", dispute_name)
	if not dispute.milestone:
		return None
	milestone = frappe.get_doc("Milestone", dispute.milestone)
	contract = frappe.get_doc("Contract", dispute.contract)
	# Released covers Resolved-Freelancer/Resolved-Split; Resolved-Employer
	# uses refund_milestone(), which leaves the Escrow Transaction "Refunded"
	# instead -- both are "money already left escrow" states that a reversal
	# needs to find.
	escrow = frappe.db.get_value(
		"Escrow Transaction", {"milestone": dispute.milestone, "status": ["in", ["Released", "Refunded"]]},
		["name", "amount"], as_dict=True,
	)
	if not escrow:
		return None

	result = {"milestone": milestone.name, "escrow_transaction": escrow.name, "milestone_amount": escrow.amount, "lines": []}
	if dispute.status == "Resolved-Freelancer":
		commission_amount = flt(frappe.db.get_value(
			"Platform Earning", {"reference_doctype": "Milestone", "reference_name": milestone.name, "earning_type": "Freelancer Commission"}, "amount"
		))
		net_amount = flt(escrow.amount) - commission_amount
		result["lines"].append({"party_type": "Freelancer Profile", "party": contract.freelancer, "debit_wallet": net_amount})
	elif dispute.status == "Resolved-Employer":
		result["lines"].append({"party_type": "Employer Profile", "party": contract.employer, "debit_wallet": escrow.amount})
	elif dispute.status == "Resolved-Split":
		freelancer_amount = flt(escrow.amount) * flt(dispute.split_freelancer_percent) / 100
		employer_refund = flt(escrow.amount) - freelancer_amount
		commission_amount = flt(frappe.db.get_value(
			"Platform Earning", {"reference_doctype": "Milestone", "reference_name": milestone.name, "earning_type": "Freelancer Commission"}, "amount"
		))
		freelancer_net = freelancer_amount - commission_amount
		if employer_refund:
			result["lines"].append({"party_type": "Employer Profile", "party": contract.employer, "debit_wallet": employer_refund})
		if freelancer_net:
			result["lines"].append({"party_type": "Freelancer Profile", "party": contract.freelancer, "debit_wallet": freelancer_net})
	else:
		return None

	result["total_back_to_escrow"] = escrow.amount
	return result


def apply_resolution_reversal(dispute_name):
	"""Actually performs what compute_resolution_reversal() described: debits
	each party's wallet back by the amount they received, and restores the
	milestone to Funded / the Escrow Transaction to Held so an admin can
	make a fresh decision with Milestone.approve_and_release()/refund()."""
	from worcent.worcent_finance.accounting_engine import (
		COMMISSION_INCOME_ACCOUNT, ESCROW_ACCOUNT, _acc, _wallet_line, record_dispute_reversal,
	)

	plan = compute_resolution_reversal(dispute_name)
	if not plan:
		frappe.throw(_("There's nothing to reverse for this dispute (milestone was never released/refunded, or already reversed)."))

	je_lines = []
	for line in plan["lines"]:
		wallet = frappe.get_doc("Wallet", ensure_wallet(line["party_type"], line["party"]))
		amount = flt(line["debit_wallet"])
		if flt(wallet.balance) < amount:
			frappe.throw(
				_("{0}'s wallet balance is too low to reverse this ({1} needed) -- resolve manually instead.").format(
					line["party"], frappe.utils.fmt_money(amount, currency="USD")
				)
			)

	for line in plan["lines"]:
		wallet = frappe.get_doc("Wallet", ensure_wallet(line["party_type"], line["party"]))
		amount = flt(line["debit_wallet"])
		wallet.balance = flt(wallet.balance) - amount
		wallet.save(ignore_permissions=True)
		_wallet_txn(
			wallet.name, "Adjustment", "Debit", amount, wallet.balance,
			"Dispute Case", dispute_name, remarks="Appeal upheld -- original resolution reversed",
		)
		je_line = _wallet_line(line["party_type"], line["party"], amount, is_debit=True)
		if je_line:
			je_lines.append(je_line)

	employer = frappe.db.get_value("Contract", frappe.db.get_value("Milestone", plan["milestone"], "contract"), "employer")
	employer_wallet = frappe.get_doc("Wallet", ensure_wallet("Employer Profile", employer))
	employer_wallet.held_in_escrow = flt(employer_wallet.held_in_escrow) + flt(plan["total_back_to_escrow"])
	employer_wallet.save(ignore_permissions=True)

	je_lines.append({"account": _acc(ESCROW_ACCOUNT), "credit": plan["total_back_to_escrow"]})
	# The full milestone amount is going back into escrow, but the wallet
	# debits above only recovered the *net* amounts parties were paid --
	# the platform's commission on the original release/split was already
	# recognised as income, so un-recognise it here to make the entry balance
	# (debit Commission Income, clawing the earning back since the whole
	# transaction it was earned on is now void).
	total_debited = sum(flt(l["debit_wallet"]) for l in plan["lines"])
	unreversed_commission = flt(plan["total_back_to_escrow"]) - total_debited
	if unreversed_commission:
		je_lines.append({"account": _acc(COMMISSION_INCOME_ACCOUNT), "debit": unreversed_commission})

	frappe.db.set_value("Escrow Transaction", plan["escrow_transaction"], "status", "Held")
	frappe.db.set_value("Milestone", plan["milestone"], "status", "Funded")

	record_dispute_reversal(je_lines, dispute_name)

	return plan


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
