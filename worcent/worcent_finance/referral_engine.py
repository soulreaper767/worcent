import frappe
from frappe import _
from frappe.utils import add_days, flt, random_string

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


def ensure_referral_code(profile_type, profile_name):
	"""Every Freelancer/Employer automatically gets a shareable referral code
	the moment their profile exists -- called from Freelancer/Employer
	Profile.on_update(), right next to the existing ensure_wallet() call.
	Idempotent: never creates a second code for the same profile."""
	user = frappe.db.get_value(profile_type, profile_name, "user")
	if not user or frappe.db.exists("Referral Code", {"owner_user": user}):
		return

	name_part = frappe.db.get_value(
		profile_type, profile_name, "display_name" if profile_type == "Freelancer Profile" else "company_name"
	) or user.split("@")[0]
	slug = "".join(ch for ch in name_part.upper() if ch.isalnum())[:10] or "WORCENT"

	code = f"{slug}-{random_string(4).upper()}"
	while frappe.db.exists("Referral Code", code):
		code = f"{slug}-{random_string(4).upper()}"

	frappe.get_doc(
		{
			"doctype": "Referral Code",
			"code": code,
			"owner_user": user,
			"status": "Active",
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

	from worcent.worcent_finance.accounting_engine import record_bonus

	record_bonus(profile_type, profile_name, bonus, profile_name, label="Signup bonus")


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

	from worcent.worcent_finance.accounting_engine import record_bonus

	record_bonus(profile_type, profile_name, bonus, profile_name, label="Verification bonus")


def apply_referral_signup(profile_type, profile_name, referral_code_name):
	"""Called right after a new Freelancer/Employer Profile is created with a
	referral code attached: validates the code's Referral Program conditions
	(active, not expired, under its redemption cap), credits the *referred*
	user's signup bonus, and logs the Referral for later reward payout."""
	if not referral_code_name or not frappe.db.exists("Referral Code", referral_code_name):
		return
	code = frappe.get_doc("Referral Code", referral_code_name)
	if code.status != "Active":
		frappe.throw(_("This referral link is no longer active."))

	if not code.program:
		return
	program = frappe.get_cached_doc("Referral Program", code.program)
	if not program.is_active:
		frappe.throw(_("This referral link is no longer valid."))
	if program.applies_to != "Both" and program.applies_to != profile_type.replace(" Profile", ""):
		frappe.throw(_("This referral link isn't valid for {0} sign-ups.").format(profile_type.replace(" Profile", "")))
	if program.validity_days and frappe.utils.getdate() > add_days(frappe.utils.getdate(code.creation), program.validity_days):
		frappe.throw(_("This referral link has expired."))
	if program.max_redemptions and flt(code.total_signups) >= program.max_redemptions:
		frappe.throw(_("This referral link has reached its maximum number of uses."))

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

	if program.referred_signup_bonus:
		_credit(
			profile_type, profile_name, program.referred_signup_bonus, "Signup Bonus",
			f"Referral sign-up bonus ({program.program_name})", profile_type, profile_name,
		)


def maybe_pay_referrer_commission(profile_type, profile_name, platform_earning_amount):
	"""Called whenever the referred user's activity generates a platform
	earning: once that earning crosses the program's min_qualifying_amount,
	pays the referrer according to the program's reward_type, then marks the
	Referral Rewarded (one_time_reward_only) so it never fires again."""
	referral = frappe.db.get_value(
		"Referral",
		{"referred_type": profile_type, "referred_profile": profile_name, "status": "Signed Up"},
		"name",
	)
	if not referral:
		return
	referral_doc = frappe.get_doc("Referral", referral)
	code = frappe.get_doc("Referral Code", referral_doc.referral_code)
	if not code.program:
		return
	program = frappe.get_cached_doc("Referral Program", code.program)

	referral_doc.total_earning_seen = flt(referral_doc.get("total_earning_seen")) + flt(platform_earning_amount)
	if program.min_qualifying_amount and flt(referral_doc.total_earning_seen) < flt(program.min_qualifying_amount):
		referral_doc.save(ignore_permissions=True)
		return

	referrer_freelancer = frappe.db.get_value("Freelancer Profile", {"user": code.owner_user}, "name")
	referrer_employer = frappe.db.get_value("Employer Profile", {"user": code.owner_user}, "name")
	if referrer_freelancer:
		referrer_type, referrer = "Freelancer Profile", referrer_freelancer
	elif referrer_employer:
		referrer_type, referrer = "Employer Profile", referrer_employer
	else:
		return

	reward = _compute_reward(program, referrer_type, referrer, platform_earning_amount)
	if reward:
		_credit(
			referrer_type, referrer, reward, "Referral Commission",
			f"Referral reward for {profile_name} ({program.program_name})", "Referral", referral_doc.name,
		)

		from worcent.worcent_finance.accounting_engine import record_referral_commission

		record_referral_commission(referrer_type, referrer, reward, referral_doc.name)

		code.total_commission_earned = flt(code.total_commission_earned) + reward
		code.save(ignore_permissions=True)

	referral_doc.status = "Rewarded"
	referral_doc.commission_paid = flt(reward)
	referral_doc.save(ignore_permissions=True)


def _compute_reward(program, referrer_type, referrer, platform_earning_amount):
	if program.reward_type == "Percent of First Platform Earning":
		return flt(platform_earning_amount) * flt(program.reward_value) / 100
	if program.reward_type in ("Flat Signup Bonus", "Flat Bonus on First Milestone"):
		return flt(program.reward_value)
	if program.reward_type == "Free Premium Days":
		_extend_premium_days(referrer_type, referrer, int(program.reward_value))
		return 0
	return 0


def _extend_premium_days(referrer_type, referrer, days):
	if not days:
		return
	tier_for = "Freelancer" if referrer_type == "Freelancer Profile" else "Employer"
	sub = frappe.db.get_value(
		"Premium Subscription",
		{"user": frappe.db.get_value(referrer_type, referrer, "user"), "status": "Active"},
		"name",
	)
	if sub:
		current = frappe.db.get_value("Premium Subscription", sub, "renews_on")
		frappe.db.set_value("Premium Subscription", sub, "renews_on", add_days(current, days))
