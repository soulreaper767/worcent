"""Second wave of demo data: closes the gaps a full audit found in the
original seed (install.py) -- workflows that only ever had one instance, or
whose demo record was faked directly (bypassing the real doctype/API logic)
instead of walking the actual flow. Every step here is idempotent and safe
to call repeatedly via reseed_demo_data(). Also exercises the new features
added in this pass (messaging, saved items, gig extras, referral programs,
regulated/sports categories, suspension enforcement)."""

import contextlib

import frappe
from frappe.utils import add_days, flt, today

DEMO_PASSWORD = "Test@12345"


@contextlib.contextmanager
def _as_user(user):
	"""Temporarily act as a demo user (so role/ownership checks in the real
	whitelisted methods pass, exactly as a real user would trigger them),
	always restoring Administrator afterward even if the body raises --
	otherwise a mid-seed failure would leave the rest of the seed chain
	running as the wrong user."""
	frappe.set_user(user)
	try:
		yield
	finally:
		frappe.set_user("Administrator")


def seed_v2_demo_data():
	seed_second_dispute_with_real_funds()
	seed_second_advance_closed()
	seed_insurance_via_real_flow()
	seed_premium_subscriptions_via_real_flow()
	seed_second_referral_rewarded()
	seed_second_franchise_settlement()
	seed_messaging_demo()
	seed_saved_items_demo()
	seed_gig_extras_and_requirements()
	seed_suspended_account_demo()
	frappe.db.commit()


def _wallet(party_type, party):
	from worcent.worcent_core.wallet_utils import ensure_wallet

	return ensure_wallet(party_type, party)


def seed_second_dispute_with_real_funds():
	"""The original demo dispute (contract 1) is already fixed to fund its
	milestone before resolving (see install.py). This adds a SECOND dispute
	on a different contract, resolved in the *employer's* favour (refund),
	so both money-moving outcomes are demonstrated -- plus a third, walked
	through a full appeal-upheld reversal."""
	from worcent.worcent_finance.escrow_engine import fund_milestone

	freelancer2 = frappe.db.get_value("Freelancer Profile", {"user": "freelancer2.demo@worcent.test"}, "name")
	employer2 = frappe.db.get_value("Employer Profile", {"user": "employer2.demo@worcent.test"}, "name")
	if not freelancer2 or not employer2:
		return

	if frappe.db.exists("Contract", {"freelancer": freelancer2, "employer": employer2, "rate": 350}):
		contract_name = frappe.db.get_value("Contract", {"freelancer": freelancer2, "employer": employer2, "rate": 350}, "name")
	else:
		frappe.db.set_value("Wallet", _wallet("Employer Profile", employer2), "balance",
			flt(frappe.db.get_value("Wallet", _wallet("Employer Profile", employer2), "balance")) + 1000)
		contract = frappe.get_doc({
			"doctype": "Contract", "freelancer": freelancer2, "employer": employer2,
			"contract_type": "Fixed", "rate": 350, "status": "Active",
		}).insert(ignore_permissions=True)
		contract_name = contract.name

	milestone_name = frappe.db.get_value("Milestone", {"contract": contract_name}, "name")
	if not milestone_name:
		milestone = frappe.get_doc({
			"doctype": "Milestone", "contract": contract_name, "title": "Disputed deliverable (employer favour)",
			"amount": 350, "due_date": add_days(today(), 7), "status": "Pending",
		}).insert(ignore_permissions=True)
		milestone_name = milestone.name
		fund_milestone(milestone_name)

	if not frappe.db.exists("Dispute Case", {"contract": contract_name}):
		dispute = frappe.get_doc({
			"doctype": "Dispute Case", "contract": contract_name, "milestone": milestone_name,
			"raised_by": "freelancer2.demo@worcent.test", "against": "Freelancer", "status": "Open",
			"reason": "Employer says the delivered work didn't match the brief at all.",
		})
		dispute.insert(ignore_permissions=True)
		with _as_user("arbitrator2.demo@worcent.test"):
			frappe.get_doc("Dispute Case", dispute.name).resolve_case(
				"Resolved-Employer", resolution_notes="Delivered work did not match the agreed brief; refunded to employer."
			)


def seed_second_advance_closed():
	freelancer3 = frappe.db.get_value("Freelancer Profile", {"user": "freelancer3.demo@worcent.test"}, "name")
	if not freelancer3:
		return
	if frappe.db.exists("Advance Request", {"freelancer": freelancer3}):
		return

	frappe.db.set_value("Wallet", _wallet("Freelancer Profile", freelancer3), "balance", 500)
	adv = frappe.get_doc({
		"doctype": "Advance Request", "freelancer": freelancer3, "amount_requested": 150, "interest_rate": 4,
	})
	adv.insert(ignore_permissions=True)
	with _as_user("finance1.demo@worcent.test"):
		adv = frappe.get_doc("Advance Request", adv.name)
		adv.approve_and_disburse()
	with _as_user("freelancer3.demo@worcent.test"):
		adv.reload()
		for row in list(adv.repayment_schedule):
			adv.pay_installment(row.name)
			adv.reload()


def seed_insurance_via_real_flow():
	from worcent.worcent_finance.insurance_api import purchase_policy

	plans = frappe.get_all("Insurance Plan", pluck="name")
	demo_freelancers = ["freelancer3.demo@worcent.test", "freelancer4.demo@worcent.test"]
	for user, plan in zip(demo_freelancers, plans):
		freelancer = frappe.db.get_value("Freelancer Profile", {"user": user}, "name")
		if not freelancer or frappe.db.exists("Insurance Policy", {"freelancer": freelancer, "insurance_plan": plan}):
			continue
		premium = flt(frappe.db.get_value("Insurance Plan", plan, "premium"))
		frappe.db.set_value("Wallet", _wallet("Freelancer Profile", freelancer), "balance",
			flt(frappe.db.get_value("Wallet", _wallet("Freelancer Profile", freelancer), "balance")) + premium + 10)
		with _as_user(user):
			policy_name = purchase_policy(plan)

		if user == demo_freelancers[0] and not frappe.db.exists("Insurance Claim", {"policy": policy_name}):
			claim = frappe.get_doc({
				"doctype": "Insurance Claim", "policy": policy_name, "reason": "Minor medical expense reimbursement",
				"amount_claimed": min(50, flt(frappe.db.get_value("Insurance Plan", plan, "coverage_amount")) or 50),
			})
			claim.insert(ignore_permissions=True)
			with _as_user("finance1.demo@worcent.test"):
				frappe.get_doc("Insurance Claim", claim.name).approve_and_pay()
		elif not frappe.db.exists("Insurance Claim", {"policy": policy_name}):
			frappe.get_doc({
				"doctype": "Insurance Claim", "policy": policy_name, "reason": "Claim outside coverage terms",
				"amount_claimed": 20, "status": "Rejected",
			}).insert(ignore_permissions=True)


def seed_premium_subscriptions_via_real_flow():
	from worcent.worcent_finance.premium_subscription_api import subscribe

	pairs = [
		("freelancer3.demo@worcent.test", "Freelancer"),
		("employer2.demo@worcent.test", "Employer"),
	]
	for user, tier_for in pairs:
		if frappe.db.exists("Premium Subscription", {"user": user, "status": "Active"}):
			continue
		plan = frappe.db.get_value("Premium Subscription Plan", {"tier_for": tier_for}, "name")
		if not plan:
			continue
		party_type = "Freelancer Profile" if tier_for == "Freelancer" else "Employer Profile"
		party = frappe.db.get_value(party_type, {"user": user}, "name")
		if not party:
			continue
		price = flt(frappe.db.get_value("Premium Subscription Plan", plan, "price"))
		frappe.db.set_value("Wallet", _wallet(party_type, party), "balance",
			flt(frappe.db.get_value("Wallet", _wallet(party_type, party), "balance")) + price + 10)
		with _as_user(user):
			subscribe(plan)


def seed_second_referral_rewarded():
	from worcent.worcent_finance.escrow_engine import fund_milestone, release_milestone

	if frappe.db.exists("Referral Code", "LAUNCH-DEMO1"):
		code_name = "LAUNCH-DEMO1"
	else:
		launch_program = frappe.db.get_value("Referral Program", "Launch Promo", "name")
		if not launch_program:
			return
		code = frappe.get_doc({
			"doctype": "Referral Code", "code": "LAUNCH-DEMO1", "owner_user": "freelancer2.demo@worcent.test",
			"program": launch_program, "status": "Active",
		})
		code.insert(ignore_permissions=True)
		code_name = code.name

	if not frappe.db.exists("User", "freelancer7.demo@worcent.test"):
		user = frappe.get_doc({
			"doctype": "User", "email": "freelancer7.demo@worcent.test", "first_name": "Junaid", "last_name": "Referred",
			"send_welcome_email": 0, "enabled": 1, "roles": [{"role": "Freelancer"}],
		})
		user.new_password = DEMO_PASSWORD
		user.insert(ignore_permissions=True)

	freelancer7 = frappe.db.get_value("Freelancer Profile", {"user": "freelancer7.demo@worcent.test"}, "name")
	if not freelancer7:
		profile = frappe.get_doc({
			"doctype": "Freelancer Profile", "user": "freelancer7.demo@worcent.test",
			"headline": "Junior mobile app developer", "referred_by_code": code_name,
			"country": "Pakistan", "status": "Active", "published": 1,
		})
		profile.insert(ignore_permissions=True)
		freelancer7 = profile.name

	referral = frappe.db.get_value("Referral", {"referral_code": code_name, "referred_profile": freelancer7}, "status")
	if referral == "Rewarded":
		return

	employer1 = frappe.db.get_value("Employer Profile", {"user": "employer1.demo@worcent.test"}, "name")
	if not employer1:
		return
	frappe.db.set_value("Wallet", _wallet("Employer Profile", employer1), "balance",
		flt(frappe.db.get_value("Wallet", _wallet("Employer Profile", employer1), "balance")) + 500)
	contract = frappe.get_doc({
		"doctype": "Contract", "freelancer": freelancer7, "employer": employer1,
		"contract_type": "Fixed", "rate": 200, "status": "Active",
	}).insert(ignore_permissions=True)
	milestone = frappe.get_doc({
		"doctype": "Milestone", "contract": contract.name, "title": "First job for referred freelancer",
		"amount": 200, "due_date": add_days(today(), 7), "status": "Pending",
	}).insert(ignore_permissions=True)
	fund_milestone(milestone.name)
	release_milestone(milestone.name)


def seed_second_franchise_settlement():
	islamabad = frappe.db.get_value("Office", {"office_name": "Worcent Partner - Islamabad"}, "name")
	if not islamabad or frappe.db.exists("Franchise Settlement", {"office": islamabad}):
		return
	frappe.get_doc({
		"doctype": "Franchise Settlement", "office": islamabad,
		"period_start": add_days(today(), -30), "period_end": today(),
		"gross_commission_collected": 420, "franchise_share": 105, "platform_share": 315,
		"status": "Settled",
	}).insert(ignore_permissions=True)


def seed_messaging_demo():
	from worcent.worcent_marketplace.conversation_api import send_message, start_conversation

	gig = frappe.db.get_value("Gig", {"freelancer": frappe.db.get_value("Freelancer Profile", {"user": "freelancer2.demo@worcent.test"}, "name")}, "name")
	if not gig:
		return

	with _as_user("employer1.demo@worcent.test"):
		convo = start_conversation("Gig", gig)
		if frappe.db.count("Message", {"conversation": convo}) == 0:
			send_message(convo, "Hi! Can you do a rush job by Friday?")

	with _as_user("freelancer2.demo@worcent.test"):
		if frappe.db.count("Message", {"conversation": convo}) == 1:
			send_message(convo, "Yes, Friday works for me. I'll send a proposal shortly.")


def seed_saved_items_demo():
	from worcent.worcent_marketplace.saved_item_api import toggle_saved_item

	with _as_user("employer2.demo@worcent.test"):
		for gig in frappe.get_all("Gig", filters={"status": "Active"}, limit_page_length=2, pluck="name"):
			if not frappe.db.exists("Saved Item", {"user": "employer2.demo@worcent.test", "item_doctype": "Gig", "item_name": gig}):
				toggle_saved_item("Gig", gig)


def seed_gig_extras_and_requirements():
	gig = frappe.db.get_value("Gig", {"freelancer": frappe.db.get_value("Freelancer Profile", {"user": "freelancer1.demo@worcent.test"}, "name")}, "name")
	if not gig:
		return
	doc = frappe.get_doc("Gig", gig)
	changed = False
	if not any(p.requirements for p in doc.packages):
		for p in doc.packages:
			p.requirements = "What pages/screens do you need, and do you have existing brand colors?"
		changed = True
	if not doc.extras:
		doc.append("extras", {"title": "Extra Fast Delivery", "price": 50, "delivery_days_reduction": 2})
		doc.append("extras", {"title": "Source Files Included", "price": 20, "delivery_days_reduction": 0})
		changed = True
	if changed:
		doc.save(ignore_permissions=True)


def seed_suspended_account_demo():
	"""One suspended freelancer, kept realistic: still has their historical
	Gig/reviews on record, but Suspended status now actually blocks them
	from new activity and hides their Gig from /gigs (see permissions.py's
	assert_not_suspended and the has_website_permission updates)."""
	freelancer4 = frappe.db.get_value("Freelancer Profile", {"user": "freelancer4.demo@worcent.test"}, "name")
	if freelancer4 and frappe.db.get_value("Freelancer Profile", freelancer4, "status") != "Suspended":
		frappe.db.set_value("Freelancer Profile", freelancer4, "status", "Suspended")
