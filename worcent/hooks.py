app_name = "worcent"
app_title = "Worcent"
app_publisher = "soulreaper767"
app_description = "Complete freelance marketplace platform: jobs, gigs, escrow, disputes, franchised local offices, field reps, and freelancer facilities"
app_email = "jwabdms@gmail.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["frappe", "erpnext", "payments", "hrms"]

# Fixtures
fixtures = [
	{"dt": "Role", "filters": [["name", "in", [
		"Worcent Admin", "Freelancer", "Employer", "Office Manager", "Franchise Owner",
		"Field Rep", "Support Agent", "Dispute Arbitrator", "Finance Manager", "Agency Manager",
		"Accounts Manager", "Office Managing Partner",
	]]]},
]

# Includes in <head>
# ------------------

app_include_css = "/assets/worcent/css/worcent.css"
app_include_js = "/assets/worcent/js/worcent.js"

web_include_css = "/assets/worcent/css/worcent.css"
web_include_js = "/assets/worcent/js/worcent.js"

brand_html = '<span class="wc-brand-mark"><svg viewBox="0 0 32 32" width="26" height="26" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="9" fill="#14805e"/><path d="M8 11L13 21L16 14L19 21L24 11" stroke="white" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg><span class="wc-brand-word">Worcent</span></span>'

# Website route rules
# ------------------
website_generators = ["Freelancer Profile", "Employer Profile", "Job Posting", "Gig", "Agency"]

update_website_context = [
	"worcent.worcent_core.website_context.update_context",
]

has_website_permission = {
	"Freelancer Profile": "worcent.worcent_core.doctype.freelancer_profile.freelancer_profile.has_website_permission",
	"Employer Profile": "worcent.worcent_core.doctype.employer_profile.employer_profile.has_website_permission",
	"Job Posting": "worcent.worcent_marketplace.doctype.job_posting.job_posting.has_website_permission",
	"Gig": "worcent.worcent_marketplace.doctype.gig.gig.has_website_permission",
	"Agency": "worcent.worcent_core.doctype.agency.agency.has_website_permission",
}

# Installation
# ------------
after_install = "worcent.install.after_install"

# Migration
# ------------------
after_migrate = "worcent.install.after_migrate"

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"worcent.worcent_finance.escrow_engine.auto_release_overdue_milestones",
	],
}

# Permissions
# -----------
permission_query_conditions = {
	"Contract": "worcent.worcent_core.permissions.contract_query_conditions",
	"Milestone": "worcent.worcent_core.permissions.milestone_query_conditions",
	"Wallet": "worcent.worcent_core.permissions.wallet_query_conditions",
	"Support Ticket": "worcent.worcent_core.permissions.support_ticket_query_conditions",
	"Assisted Request": "worcent.worcent_core.permissions.assisted_request_query_conditions",
	"Wallet Transaction": "worcent.worcent_core.permissions.wallet_transaction_query_conditions",
	"Platform Earning": "worcent.worcent_core.permissions.platform_earning_query_conditions",
	"Payout Account": "worcent.worcent_core.permissions.payout_account_query_conditions",
	"Withdrawal Request": "worcent.worcent_core.permissions.withdrawal_request_query_conditions",
	"Referral Code": "worcent.worcent_core.permissions.referral_code_query_conditions",
	"Referral": "worcent.worcent_core.permissions.referral_query_conditions",
}

has_permission = {
	"Contract": "worcent.worcent_core.permissions.contract_has_permission",
	"Milestone": "worcent.worcent_core.permissions.milestone_has_permission",
	"Wallet": "worcent.worcent_core.permissions.wallet_has_permission",
	"Support Ticket": "worcent.worcent_core.permissions.support_ticket_has_permission",
	"Assisted Request": "worcent.worcent_core.permissions.assisted_request_has_permission",
	"Wallet Transaction": "worcent.worcent_core.permissions.wallet_transaction_has_permission",
	"Platform Earning": "worcent.worcent_core.permissions.platform_earning_has_permission",
	"Payout Account": "worcent.worcent_core.permissions.payout_account_has_permission",
	"Withdrawal Request": "worcent.worcent_core.permissions.withdrawal_request_has_permission",
	"Referral Code": "worcent.worcent_core.permissions.referral_code_has_permission",
	"Referral": "worcent.worcent_core.permissions.referral_has_permission",
}
