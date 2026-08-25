import frappe
from frappe.utils import flt

from worcent.worcent_core.wallet_utils import ensure_wallet


def _credit(party_type, party, amount, transaction_type, remarks, reference_doctype=None, reference_name=None):
	if not amount:
		return
	wallet = frappe.get_doc("Wallet", ensure_wallet(party_type, party))
	wallet.balance = flt(wallet.balance) + flt(amount)
	wallet.save(ignore_permissions=True)
	frappe.get_doc(
		{
			"doctype": "Wallet Transaction",
			"wallet": wallet.name,
			"transaction_type": transaction_type,
			"direction": "Credit",
			"amount": amount,
			"balance_after": wallet.balance,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"remarks": remarks,
		}
	).insert(ignore_permissions=True)


def apply_signup_bonus(profile_type, profile_name):
	"""Flat one-time bonus for any new Freelancer/Employer Profile, matching
	the platform's standard $5 signup incentive. Guarded so it can never
	fire twice for the same profile even if called again."""
	if frappe.db.exists(
		"Wallet Transaction",
		{
			"transaction_type": "Signup Bonus",
			"reference_doctype": profile_type,
			"reference_name": profile_name,
		},
	):
		return
	bonus = flt(frappe.db.get_single_value("Worcent Settings", "signup_bonus_amount")) or 5
	_credit(profile_type, profile_name, bonus, "Signup Bonus", "Welcome to Worcent!", profile_type, profile_name)


def apply_verification_bonus(profile_type, profile_name):
	"""One-time bonus the first time a profile reaches ID/Business
	verification (whichever verification type triggers it first)."""
	if frappe.db.exists(
		"Wallet Transaction",
		{
			"transaction_type": "Verification Bonus",
			"reference_doctype": profile_type,
			"reference_name": profile_name,
		},
	):
		return
	bonus = flt(frappe.db.get_single_value("Worcent Settings", "verification_bonus_amount")) or 5
	_credit(
		profile_type, profile_name, bonus, "Verification Bonus",
		"Bonus for completing identity verification", profile_type, profile_name,
	)


def apply_referral_signup(profile_type, profile_name, referral_code_name):
	"""Called right after a new Freelancer/Employer Profile is created with a
	referral code attached: credits the *referred* user's signup bonus (per
	the code's own configured amount, on top of/replacing the platform
	default — we use whichever is larger so a referral is never worse than
	signing up directly) and logs the Referral for later commission payout."""
	if not referral_code_name or not frappe.db.exists("Referral Code", referral_code_name):
		return
	code = frappe.get_doc("Referral Code", referral_code_name)
	if code.status != "Active":
		return

	if frappe.db.exists("Referral", {"referral_code": code.name, "referred_profile": profile_name}):
		return

	referral = frappe.get_doc(
		{
			"doctype": "Referral",
			"referral_code": code.name,
			"referred_type": profile_type,
			"referred_profile": profile_name,
			"status": "Signed Up",
		}
	)
	referral.insert(ignore_permissions=True)

	code.total_signups = flt(code.total_signups) + 1
	code.save(ignore_permissions=True)


def maybe_pay_referrer_commission(profile_type, profile_name, platform_earning_amount):
	"""Called whenever the referred user's activity generates the platform's
	*first* earning from them (freelancer commission or employer fee): pays
	the referrer a % of that platform earning (not of the raw transaction),
	once, then marks the Referral Rewarded so it never fires again."""
	referral = frappe.db.get_value(
		"Referral",
		{"referred_type": profile_type, "referred_profile": profile_name, "status": "Signed Up"},
		"name",
	)
	if not referral:
		return
	referral_doc = frappe.get_doc("Referral", referral)
	code = frappe.get_doc("Referral Code", referral_doc.referral_code)

	commission = flt(platform_earning_amount) * flt(code.commission_percent_referrer) / 100
	if commission <= 0:
		referral_doc.status = "Rewarded"
		referral_doc.save(ignore_permissions=True)
		return

	referrer_freelancer = frappe.db.get_value("Freelancer Profile", {"user": code.owner_user}, "name")
	referrer_employer = frappe.db.get_value("Employer Profile", {"user": code.owner_user}, "name")
	if referrer_freelancer:
		_credit(
			"Freelancer Profile", referrer_freelancer, commission, "Referral Commission",
			f"Referral commission for {profile_name}", "Referral", referral_doc.name,
		)
	elif referrer_employer:
		_credit(
			"Employer Profile", referrer_employer, commission, "Referral Commission",
			f"Referral commission for {profile_name}", "Referral", referral_doc.name,
		)
	else:
		return

	referral_doc.status = "Rewarded"
	referral_doc.commission_paid = commission
	referral_doc.save(ignore_permissions=True)

	code.total_commission_earned = flt(code.total_commission_earned) + commission
	code.save(ignore_permissions=True)
