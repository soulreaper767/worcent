import frappe
from urllib.parse import quote

sitemap = 0


def get_context(context):
	# Plain query-string form (/r?code=XXXX) rather than a path segment
	# (/r/XXXX) -- avoids depending on Frappe's DB-configured dynamic website
	# route rules just for a redirect, and is just as copy-paste-able.
	code = frappe.form_dict.get("code")
	frappe.local.flags.redirect_location = f"/join?ref={quote(code)}" if code else "/join"
	raise frappe.Redirect
