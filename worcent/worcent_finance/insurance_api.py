import frappe
from frappe import _
from frappe.utils import add_days, flt, today

from worcent.worcent_core.permissions import assert_not_suspended, get_freelancer_profile


@frappe.whitelist()
def purchase_policy(insurance_plan):
	freelancer = get_freelancer_profile(frappe.session.user)
	if not freelancer:
		frappe.throw(_("Only freelancers can buy an insurance policy."))
	assert_not_suspended("Freelancer Profile", freelancer)

	plan = frappe.get_doc("Insurance Plan", insurance_plan)
	if frappe.db.exists("Insurance Policy", {"freelancer": freelancer, "insurance_plan": plan.name, "status": "Active"}):
		frappe.throw(_("You already have an active policy on this plan."))

	from worcent.worcent_core.wallet_utils import ensure_wallet
	from worcent.worcent_finance.escrow_engine import _record_earning, _wallet_txn

	wallet = frappe.get_doc("Wallet", ensure_wallet("Freelancer Profile", freelancer))
	premium = flt(plan.premium)
	if flt(wallet.balance) < premium:
		frappe.throw(_("Insufficient wallet balance for this plan's premium ({0}). Top up your wallet first.").format(
			frappe.utils.fmt_money(premium, currency="USD")
		))

	wallet.balance = flt(wallet.balance) - premium
	wallet.save(ignore_permissions=True)
	_wallet_txn(
		wallet.name, "Insurance Premium", "Debit", premium, wallet.balance,
		"Insurance Plan", plan.name, remarks=f"Premium for {plan.plan_name}",
	)
	_record_earning(
		"Insurance Premium", premium, "Freelancer Profile", freelancer,
		"Insurance Plan", plan.name, f"Premium for {plan.plan_name}",
	)

	policy = frappe.get_doc(
		{
			"doctype": "Insurance Policy",
			"freelancer": freelancer,
			"insurance_plan": plan.name,
			"status": "Active",
			"start_date": today(),
			"end_date": add_days(today(), 365),
		}
	)
	policy.insert(ignore_permissions=True)

	from worcent.worcent_finance.accounting_engine import record_insurance_premium

	record_insurance_premium(freelancer, premium, policy.name)

	return policy.name
