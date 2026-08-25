import re
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils.password import update_password

ACCOUNT_TYPE_ROLE = {"Freelancer": "Freelancer", "Employer": "Employer"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@frappe.whitelist(allow_guest=True)
def register(email, password, full_name, account_type, country=None, referral_code=None):
	"""One-step sign-up: creates the User (with the correct marketplace role
	already attached, so there is never a moment where a logged-in user has
	no role/workspace), logs them in immediately (no email verification —
	the platform has no Email Account configured yet), and hands back where
	the frontend should send them next to finish their profile."""
	email = (email or "").strip().lower()
	full_name = (full_name or "").strip()
	account_type = (account_type or "").strip()

	if not EMAIL_RE.match(email):
		frappe.throw(_("Enter a valid email address."))
	if not full_name:
		frappe.throw(_("Enter your full name."))
	if not password or len(password) < 8:
		frappe.throw(_("Password must be at least 8 characters."))
	if account_type not in ACCOUNT_TYPE_ROLE:
		frappe.throw(_("Choose whether you're signing up as a Freelancer or an Employer."))
	if referral_code and not frappe.db.exists("Referral Code", {"name": referral_code, "status": "Active"}):
		frappe.throw(_("That referral code isn't valid."))

	if frappe.db.exists("User", email):
		frappe.throw(_("An account with this email already exists. Please log in instead."))

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": full_name.split(" ")[0],
			"full_name": full_name,
			"enabled": 1,
			"user_type": "System User",
			"send_welcome_email": 0,
			"roles": [{"role": ACCOUNT_TYPE_ROLE[account_type]}],
		}
	)
	user.flags.no_welcome_mail = True
	user.insert(ignore_permissions=True)
	update_password(user.name, password)

	frappe.local.login_manager.login_as(user.name)

	next_step = "freelancer-register" if account_type == "Freelancer" else "employer-register"
	params = f"?country={quote(country)}" if country else ""
	if referral_code:
		params += ("&" if params else "?") + f"referred_by_code={quote(referral_code)}"

	return {"redirect_to": f"/{next_step}{params}"}
