import frappe
from frappe.utils import flt

# Small, deliberately curated map rather than all 195 countries — covers the
# currencies this platform actually seeds/supports. Falls back to the
# platform base currency (USD) for anything else.
COUNTRY_CURRENCY_MAP = {
	"Pakistan": "PKR",
	"United States": "USD",
	"United Kingdom": "GBP",
	"United Arab Emirates": "AED",
	"Saudi Arabia": "SAR",
	"Germany": "EUR",
	"France": "EUR",
	"Spain": "EUR",
	"Italy": "EUR",
	"Netherlands": "EUR",
	"Ireland": "EUR",
}

BASE_CURRENCY = "USD"

# Display-only fallback for a country not in the map above (or no country
# set at all) — deliberately separate from BASE_CURRENCY, which is the
# wallet ledger's real unit of account and must never change here.
DEFAULT_DISPLAY_CURRENCY = "PKR"


def get_currency_for_country(country):
	return COUNTRY_CURRENCY_MAP.get(country, DEFAULT_DISPLAY_CURRENCY)


def get_exchange_rate(from_currency, to_currency):
	if from_currency == to_currency:
		return 1.0
	rate = frappe.db.get_value(
		"Currency Exchange Rate",
		{"from_currency": from_currency, "to_currency": to_currency},
		"rate",
	)
	if rate:
		return flt(rate)
	rate = frappe.db.get_value(
		"Currency Exchange",
		{"from_currency": from_currency, "to_currency": to_currency},
		"exchange_rate",
	)
	if rate:
		return flt(rate)
	# fall back through the base currency if a direct pair isn't seeded
	if from_currency != BASE_CURRENCY and to_currency != BASE_CURRENCY:
		to_base = get_exchange_rate(from_currency, BASE_CURRENCY)
		from_base = get_exchange_rate(BASE_CURRENCY, to_currency)
		if to_base and from_base:
			return flt(to_base * from_base)
	return 1.0


def convert(amount, from_currency, to_currency):
	return flt(flt(amount) * get_exchange_rate(from_currency, to_currency))


def format_in_currency(amount, currency):
	return frappe.utils.fmt_money(amount, currency=currency)
