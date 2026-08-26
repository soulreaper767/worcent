"""Mirrors every real money-movement event (top-up, milestone funding,
release, refund, withdrawal, mentorship fees, referral commissions) into
real ERPNext General Ledger entries via Journal Entry, on top of Worcent's
own Wallet Transaction ledger (which stays the operational source of
truth). Employers post against Customer Advances (they've prepaid us);
Freelancers post against Creditors (we owe them their earnings) — both are
stock ERPNext accounts, so employers/freelancers get real Party Statement/
Accounts Receivable-Payable reporting for free.

Every call here is best-effort: a Chart of Accounts problem must never
block an actual wallet operation, so every public function swallows its
own exceptions (logged, not raised).
"""

import frappe
from frappe.utils import flt, today

COMPANY = "Worcent Platform"

ESCROW_ACCOUNT = "Escrow Held"
COMMISSION_INCOME_ACCOUNT = "Platform Commission Income"
REFERRAL_EXPENSE_ACCOUNT = "Referral Commission Expense"
BONUS_EXPENSE_ACCOUNT = "Promotional Bonuses Expense"
CASH_ACCOUNT = "Cash"
CUSTOMER_ADVANCES_ACCOUNT = "Customer Advances"
CREDITORS_ACCOUNT = "Creditors"


def _acc(short_name):
	abbr = frappe.db.get_value("Company", COMPANY, "abbr")
	return f"{short_name} - {abbr}"


def ensure_accounts():
	"""Idempotent: adds the handful of custom leaf accounts this engine
	needs on top of ERPNext's standard default Chart of Accounts, and sets
	the company defaults a Journal Entry needs."""
	if not frappe.db.exists("Company", COMPANY):
		return

	_ensure_account(ESCROW_ACCOUNT, "Current Liabilities", "Liability")
	_ensure_account(COMMISSION_INCOME_ACCOUNT, "Direct Income", "Income")
	_ensure_account(REFERRAL_EXPENSE_ACCOUNT, "Indirect Expenses", "Expense")
	_ensure_account(BONUS_EXPENSE_ACCOUNT, "Indirect Expenses", "Expense")

	frappe.db.set_value(
		"Company",
		COMPANY,
		{
			"default_cash_account": _acc(CASH_ACCOUNT),
			"default_income_account": _acc(COMMISSION_INCOME_ACCOUNT),
		},
	)
	frappe.db.set_default("company", COMPANY)


def _ensure_account(short_name, parent_short_name, root_type):
	name = _acc(short_name)
	if frappe.db.exists("Account", name):
		return name
	parent = _acc(parent_short_name)
	if not frappe.db.exists("Account", parent):
		return None
	frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": short_name,
			"parent_account": parent,
			"company": COMPANY,
			"root_type": root_type,
			"is_group": 0,
		}
	).insert(ignore_permissions=True)
	return name


# ---------------------------------------------------------------------------
# Party resolution — lazily creates the linked Customer/Supplier if the
# profile doesn't have one yet (covers profiles created before this engine
# existed) and keeps the profile's erp_customer/erp_supplier field in sync.
# ---------------------------------------------------------------------------


def _party_for(party_type, party_name):
	"""Returns (party_doctype, party_name, wallet_liability_account) for a
	Freelancer Profile or Employer Profile."""
	if party_type == "Freelancer Profile":
		field = "erp_supplier"
		party_doctype = "Supplier"
		account = _acc(CREDITORS_ACCOUNT)
	elif party_type == "Employer Profile":
		field = "erp_customer"
		party_doctype = "Customer"
		account = _acc(CUSTOMER_ADVANCES_ACCOUNT)
	else:
		return None, None, None

	existing = frappe.db.get_value(party_type, party_name, field)
	if existing and frappe.db.exists(party_doctype, existing):
		return party_doctype, existing, account

	created = _create_party(party_type, party_name, party_doctype)
	if created:
		frappe.db.set_value(party_type, party_name, field, created)
	return party_doctype, created, account


def _create_party(party_type, party_name, party_doctype):
	profile = frappe.get_doc(party_type, party_name)
	display_name = getattr(profile, "display_name", None) or getattr(profile, "company_name", None) or party_name

	if party_doctype == "Supplier":
		if not frappe.db.exists("Supplier Group", "Freelancers"):
			return None
		doc = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": f"{display_name} ({party_name})",
				"supplier_group": "Freelancers",
				"supplier_type": "Individual",
			}
		)
	else:
		if not frappe.db.exists("Customer Group", "Employers"):
			return None
		doc = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": f"{display_name} ({party_name})",
				"customer_group": "Employers",
				"customer_type": "Company" if party_doctype == "Customer" else "Individual",
			}
		)
	try:
		doc.insert(ignore_permissions=True)
		return doc.name
	except Exception:
		frappe.log_error(title="Worcent accounting: party creation failed")
		return None


# ---------------------------------------------------------------------------
# Generic Journal Entry poster
# ---------------------------------------------------------------------------


def _post_je(lines, remarks, reference_doctype=None, reference_name=None):
	"""lines: list of dicts {account, debit=0, credit=0, party_type=None, party=None}."""
	try:
		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": COMPANY,
				"posting_date": today(),
				"user_remark": remarks,
				"accounts": [
					{
						"account": line["account"],
						"debit_in_account_currency": flt(line.get("debit")),
						"credit_in_account_currency": flt(line.get("credit")),
						"party_type": line.get("party_type"),
						"party": line.get("party"),
					}
					for line in lines
				],
			}
		)
		if reference_doctype:
			je.cheque_no = reference_name
			je.cheque_date = today()
		je.insert(ignore_permissions=True)
		je.submit()
		return je.name
	except Exception:
		frappe.log_error(
			title=f"Worcent accounting: JE post failed ({remarks})",
			message=frappe.get_traceback(),
		)
		return None


def _wallet_line(party_type, party_name, amount, is_debit):
	party_doctype, party, account = _party_for(party_type, party_name)
	if not account or not amount:
		return None
	line = {"account": account, "debit" if is_debit else "credit": amount}
	if party:
		line["party_type"] = party_doctype
		line["party"] = party
	return line


# ---------------------------------------------------------------------------
# Event entry points — called from the actual wallet-affecting code
# ---------------------------------------------------------------------------


def record_topup(party_type, party_name, amount, reference_doctype, reference_name):
	wallet_line = _wallet_line(party_type, party_name, amount, is_debit=False)
	if not wallet_line:
		return
	_post_je(
		[{"account": _acc(CASH_ACCOUNT), "debit": amount}, wallet_line],
		remarks=f"Wallet top-up: {reference_name}",
		reference_doctype=reference_doctype,
		reference_name=reference_name,
	)


def record_milestone_fund(employer, milestone_amount, fee_amount, milestone_name):
	total = flt(milestone_amount) + flt(fee_amount)
	employer_line = _wallet_line("Employer Profile", employer, total, is_debit=True)
	if not employer_line:
		return
	lines = [employer_line, {"account": _acc(ESCROW_ACCOUNT), "credit": milestone_amount}]
	if fee_amount:
		lines.append({"account": _acc(COMMISSION_INCOME_ACCOUNT), "credit": fee_amount})
	_post_je(lines, remarks=f"Milestone funded: {milestone_name}", reference_name=milestone_name)


def record_milestone_release(freelancer, milestone_amount, commission_amount, net_amount, milestone_name):
	freelancer_line = _wallet_line("Freelancer Profile", freelancer, net_amount, is_debit=False)
	if not freelancer_line:
		return
	lines = [{"account": _acc(ESCROW_ACCOUNT), "debit": milestone_amount}, freelancer_line]
	if commission_amount:
		lines.append({"account": _acc(COMMISSION_INCOME_ACCOUNT), "credit": commission_amount})
	_post_je(lines, remarks=f"Milestone released: {milestone_name}", reference_name=milestone_name)


def record_milestone_refund(employer, milestone_amount, milestone_name):
	employer_line = _wallet_line("Employer Profile", employer, milestone_amount, is_debit=False)
	if not employer_line:
		return
	_post_je(
		[{"account": _acc(ESCROW_ACCOUNT), "debit": milestone_amount}, employer_line],
		remarks=f"Milestone refunded: {milestone_name}",
		reference_name=milestone_name,
	)


def record_milestone_split(employer, employer_refund, freelancer, freelancer_net, commission_amount, milestone_amount, milestone_name):
	lines = [{"account": _acc(ESCROW_ACCOUNT), "debit": milestone_amount}]
	if employer_refund:
		employer_line = _wallet_line("Employer Profile", employer, employer_refund, is_debit=False)
		if employer_line:
			lines.append(employer_line)
	if freelancer_net:
		freelancer_line = _wallet_line("Freelancer Profile", freelancer, freelancer_net, is_debit=False)
		if freelancer_line:
			lines.append(freelancer_line)
	if commission_amount:
		lines.append({"account": _acc(COMMISSION_INCOME_ACCOUNT), "credit": commission_amount})
	_post_je(lines, remarks=f"Milestone split-resolved: {milestone_name}", reference_name=milestone_name)


def record_withdrawal(party_type, party_name, amount, reference_name):
	wallet_line = _wallet_line(party_type, party_name, amount, is_debit=True)
	if not wallet_line:
		return
	_post_je(
		[wallet_line, {"account": _acc(CASH_ACCOUNT), "credit": amount}],
		remarks=f"Withdrawal paid: {reference_name}",
		reference_name=reference_name,
	)


def record_mentorship_fee(mentee, mentor, fee_charged, commission_amount, net_amount, reference_name):
	mentee_line = _wallet_line("Freelancer Profile", mentee, fee_charged, is_debit=True)
	mentor_line = _wallet_line("Freelancer Profile", mentor, net_amount, is_debit=False)
	if not mentee_line or not mentor_line:
		return
	lines = [mentee_line, mentor_line]
	if commission_amount:
		lines.append({"account": _acc(COMMISSION_INCOME_ACCOUNT), "credit": commission_amount})
	_post_je(lines, remarks=f"Mentorship fee: {reference_name}", reference_name=reference_name)


def record_referral_commission(referrer_party_type, referrer_party, amount, reference_name):
	referrer_line = _wallet_line(referrer_party_type, referrer_party, amount, is_debit=False)
	if not referrer_line:
		return
	_post_je(
		[{"account": _acc(REFERRAL_EXPENSE_ACCOUNT), "debit": amount}, referrer_line],
		remarks=f"Referral commission: {reference_name}",
		reference_name=reference_name,
	)


def record_fee_charged(party_type, party_name, amount, reference_name, label="Fee"):
	"""Simple two-line JE for a flat fee charged straight to platform
	revenue (e.g. the Rank Application appeal fee) — debit the party's
	wallet liability, credit commission income."""
	party_line = _wallet_line(party_type, party_name, amount, is_debit=True)
	if not party_line:
		return
	_post_je(
		[party_line, {"account": _acc(COMMISSION_INCOME_ACCOUNT), "credit": amount}],
		remarks=f"{label}: {reference_name}",
		reference_name=reference_name,
	)


def record_bonus(party_type, party_name, amount, reference_name, label="Bonus"):
	party_line = _wallet_line(party_type, party_name, amount, is_debit=False)
	if not party_line:
		return
	_post_je(
		[{"account": _acc(BONUS_EXPENSE_ACCOUNT), "debit": amount}, party_line],
		remarks=f"{label}: {reference_name}",
		reference_name=reference_name,
	)
