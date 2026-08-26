import frappe
from frappe import _
from frappe.utils import flt, fmt_money

from worcent.worcent_finance.currency_utils import BASE_CURRENCY, convert

DISPLAY_CURRENCIES = ["USD", "PKR", "EUR", "GBP", "AED", "SAR"]


def _resolve_wallet(wallet):
	"""Staff can look up any wallet (by name); everyone else only ever sees
	their own -- resolved from their own Freelancer/Employer Profile,
	ignoring whatever the client may have sent."""
	staff_roles = {"Finance Manager", "Accounts Manager", "Worcent Admin", "System Manager"}
	if wallet and (frappe.session.user == "Administrator" or staff_roles.intersection(frappe.get_roles())):
		if not frappe.db.exists("Wallet", wallet):
			frappe.throw(_("Wallet not found."))
		return wallet

	freelancer = frappe.db.get_value("Freelancer Profile", {"user": frappe.session.user}, "name")
	employer = frappe.db.get_value("Employer Profile", {"user": frappe.session.user}, "name")
	party_type, party_name = ("Freelancer Profile", freelancer) if freelancer else ("Employer Profile", employer)
	if not party_name:
		frappe.throw(_("No Freelancer or Employer profile found for your account."))

	from worcent.worcent_core.wallet_utils import get_wallet

	wallet_doc = get_wallet(party_type, party_name)
	return wallet_doc.name if wallet_doc else None


def _money(amount, currency):
	"""Formatted server-side (not left to the client's format_currency, which
	depends on that currency's symbol/precision being cached client-side) so
	the label and the figure can never disagree about which currency they're
	in."""
	return fmt_money(amount, currency=currency)


@frappe.whitelist()
def get_wallet_ledger(wallet=None, currency=None):
	wallet_name = _resolve_wallet(wallet)
	currency = currency if currency in DISPLAY_CURRENCIES else BASE_CURRENCY

	if not wallet_name:
		return {
			"wallet": None, "party_type": None, "currency": currency, "rows": [],
			"current_balance_fmt": _money(0, currency),
			"total_earnings_fmt": _money(0, currency), "total_deductions_fmt": _money(0, currency),
			"currencies": DISPLAY_CURRENCIES,
		}

	wallet_doc = frappe.db.get_value("Wallet", wallet_name, ["party_type", "party", "balance"], as_dict=True)

	txns = frappe.get_list(
		"Wallet Transaction",
		filters={"wallet": wallet_name},
		fields=["name", "creation", "transaction_type", "direction", "amount", "balance_after", "remarks"],
		order_by="creation asc",
		limit_page_length=0,
	)

	rows = []
	total_earnings = 0.0
	total_deductions = 0.0
	for t in txns:
		earnings = flt(t.amount) if t.direction == "Credit" else 0
		deductions = flt(t.amount) if t.direction == "Debit" else 0
		total_earnings += earnings
		total_deductions += deductions
		earnings_disp = convert(earnings, BASE_CURRENCY, currency) if earnings else 0
		deductions_disp = convert(deductions, BASE_CURRENCY, currency) if deductions else 0
		balance_disp = convert(flt(t.balance_after), BASE_CURRENCY, currency)
		rows.append(
			{
				"date": frappe.utils.format_datetime(t.creation, "medium"),
				"label": t.transaction_type,
				"remarks": t.remarks or "",
				"earnings_fmt": _money(earnings_disp, currency) if earnings else "",
				"deductions_fmt": _money(deductions_disp, currency) if deductions else "",
				"balance_fmt": _money(balance_disp, currency),
			}
		)

	current_balance = convert(flt(wallet_doc.balance), BASE_CURRENCY, currency)

	return {
		"wallet": wallet_name,
		"party_type": wallet_doc.party_type,
		"currency": currency,
		"rows": rows,
		"current_balance_fmt": _money(current_balance, currency),
		"total_earnings_fmt": _money(convert(total_earnings, BASE_CURRENCY, currency), currency),
		"total_deductions_fmt": _money(convert(total_deductions, BASE_CURRENCY, currency), currency),
		"currencies": DISPLAY_CURRENCIES,
	}
