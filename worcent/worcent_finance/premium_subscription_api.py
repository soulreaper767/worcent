import frappe
from frappe import _
from frappe.utils import add_days, flt, today

TIER_FIELDS = {"Freelancer": "Freelancer Profile", "Employer": "Employer Profile"}
CYCLE_DAYS = {"Monthly": 30, "Yearly": 365}


def _resolve_party(tier_for):
	from worcent.worcent_core.permissions import get_employer_profile, get_freelancer_profile

	if tier_for == "Freelancer":
		party = get_freelancer_profile(frappe.session.user)
	else:
		party = get_employer_profile(frappe.session.user)
	if not party:
		frappe.throw(_("You need a {0} profile for this plan.").format(tier_for))
	return "Freelancer Profile" if tier_for == "Freelancer" else "Employer Profile", party


def _charge_and_extend(subscription, plan, party_type, party):
	from worcent.worcent_core.wallet_utils import ensure_wallet
	from worcent.worcent_finance.escrow_engine import _record_earning, _wallet_txn

	wallet = frappe.get_doc("Wallet", ensure_wallet(party_type, party))
	price = flt(plan.price)
	if flt(wallet.balance) < price:
		return False

	wallet.balance = flt(wallet.balance) - price
	wallet.save(ignore_permissions=True)
	_wallet_txn(
		wallet.name, "Premium Subscription", "Debit", price, wallet.balance,
		"Premium Subscription", subscription, remarks=f"{plan.plan_name} subscription charge",
	)
	_record_earning(
		"Premium Subscription", price, party_type, party,
		"Premium Subscription", subscription, f"{plan.plan_name} subscription charge",
	)

	from worcent.worcent_finance.accounting_engine import record_subscription_charge

	record_subscription_charge(party_type, party, price, subscription)
	return True


@frappe.whitelist()
def subscribe(plan):
	plan_doc = frappe.get_doc("Premium Subscription Plan", plan)
	party_type, party = _resolve_party(plan_doc.tier_for)

	from worcent.worcent_core.permissions import assert_not_suspended

	assert_not_suspended(party_type, party)

	if frappe.db.exists("Premium Subscription", {"user": frappe.session.user, "status": "Active"}):
		frappe.throw(_("You already have an active subscription. Cancel it before subscribing to a different plan."))

	subscription = frappe.get_doc(
		{
			"doctype": "Premium Subscription",
			"user": frappe.session.user,
			"plan": plan,
			"status": "Active",
			"start_date": today(),
			"renews_on": add_days(today(), CYCLE_DAYS.get(plan_doc.billing_cycle, 30)),
		}
	)
	subscription.insert(ignore_permissions=True)

	if not _charge_and_extend(subscription.name, plan_doc, party_type, party):
		subscription.delete(ignore_permissions=True)
		frappe.throw(_("Insufficient wallet balance for this plan ({0}). Top up your wallet first.").format(
			frappe.utils.fmt_money(plan_doc.price, currency="USD")
		))

	if plan_doc.tier_for == "Freelancer":
		frappe.db.set_value("Freelancer Profile", party, "premium_tier", "Pro")

	return subscription.name


@frappe.whitelist()
def cancel_subscription(subscription):
	sub = frappe.get_doc("Premium Subscription", subscription)
	if sub.user != frappe.session.user and "Worcent Admin" not in frappe.get_roles() and frappe.session.user != "Administrator":
		frappe.throw(_("You can only cancel your own subscription."))
	sub.status = "Cancelled"
	sub.save(ignore_permissions=True)

	plan_doc = frappe.get_doc("Premium Subscription Plan", sub.plan)
	if plan_doc.tier_for == "Freelancer":
		freelancer = frappe.db.get_value("Freelancer Profile", {"user": sub.user}, "name")
		if freelancer:
			frappe.db.set_value("Freelancer Profile", freelancer, "premium_tier", "None")
