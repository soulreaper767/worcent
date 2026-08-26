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
		"Accounts Manager", "Office Managing Partner", "Rank Reviewer", "Payment Officer",
	]]]},
]

# Includes in <head>
# ------------------
# The public website gets Worcent's marketing CSS/JS; Desk gets its own,
# separate, much smaller JS file (never the website one) so Frappe's own
# Desk styling stays untouched.

web_include_css = "/assets/worcent/css/worcent.css"
web_include_js = "/assets/worcent/js/worcent.js"
app_include_js = "/assets/worcent/js/worcent_desk.js"

extend_bootinfo = "worcent.boot.extend_bootinfo"

# Worcent's website pages get a fully custom shell (own navbar/footer, no
# Bootstrap) instead of Frappe's default templates/base.html — this is what
# actually wires that override in (file-path Jinja overrides alone, like the
# footer_powered.html one below, don't apply to base_template_path).
base_template = "templates/base.html"

brand_html = '<span class="wc-brand-mark"><svg viewBox="0 0 32 32" width="26" height="26" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="9" fill="#2563eb"/><path d="M8 11L13 21L16 14L19 21L24 11" stroke="white" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg><span class="wc-brand-word">Worcent</span></span>'

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
	"hourly": [
		"worcent.worcent_trust_support.doctype.support_ticket.support_ticket_engine.escalate_unanswered_tickets",
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
	"Growth Tool Result": "worcent.worcent_core.permissions.growth_tool_result_query_conditions",
	"Skill Challenge Enrollment": "worcent.worcent_core.permissions.skill_challenge_enrollment_query_conditions",
	"Rank Application": "worcent.worcent_core.permissions.rank_application_query_conditions",
	"Support Ticket Reply": "worcent.worcent_core.permissions.support_ticket_reply_query_conditions",
	"Proposal": "worcent.worcent_core.permissions.proposal_query_conditions",
	"Time Log": "worcent.worcent_core.permissions.time_log_query_conditions",
	"Physical Verification Appointment": "worcent.worcent_core.permissions.physical_verification_appointment_query_conditions",
	"Rep": "worcent.worcent_core.permissions.rep_query_conditions",
	"Insurance Policy": "worcent.worcent_core.permissions.insurance_policy_query_conditions",
	"Insurance Claim": "worcent.worcent_core.permissions.insurance_claim_query_conditions",
	"Premium Subscription": "worcent.worcent_core.permissions.premium_subscription_query_conditions",
	"Dispute Case": "worcent.worcent_core.permissions.dispute_case_query_conditions",
	"Agency Membership": "worcent.worcent_core.permissions.agency_membership_query_conditions",
	"Verification Request": "worcent.worcent_core.permissions.verification_request_query_conditions",
	"Office": "worcent.worcent_core.permissions.office_query_conditions",
	"Franchise Settlement": "worcent.worcent_core.permissions.franchise_settlement_query_conditions",
	"Mentorship Request": "worcent.worcent_core.permissions.mentorship_request_query_conditions",
	"Work Submission": "worcent.worcent_core.permissions.work_submission_query_conditions",
	"Advance Request": "worcent.worcent_core.permissions.advance_request_query_conditions",
	"Wallet Top Up": "worcent.worcent_core.permissions.wallet_top_up_query_conditions",
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
	"Growth Tool Result": "worcent.worcent_core.permissions.growth_tool_result_has_permission",
	"Skill Challenge Enrollment": "worcent.worcent_core.permissions.skill_challenge_enrollment_has_permission",
	"Rank Application": "worcent.worcent_core.permissions.rank_application_has_permission",
	"Support Ticket Reply": "worcent.worcent_core.permissions.support_ticket_reply_has_permission",
	"Freelancer Profile": "worcent.worcent_core.permissions.freelancer_profile_has_permission",
	"Employer Profile": "worcent.worcent_core.permissions.employer_profile_has_permission",
	"Gig": "worcent.worcent_core.permissions.gig_has_permission",
	"Job Posting": "worcent.worcent_core.permissions.job_posting_has_permission",
	"Proposal": "worcent.worcent_core.permissions.proposal_has_permission",
	"Time Log": "worcent.worcent_core.permissions.time_log_has_permission",
	"Physical Verification Appointment": "worcent.worcent_core.permissions.physical_verification_appointment_has_permission",
	"Rep": "worcent.worcent_core.permissions.rep_has_permission",
	"Insurance Policy": "worcent.worcent_core.permissions.insurance_policy_has_permission",
	"Insurance Claim": "worcent.worcent_core.permissions.insurance_claim_has_permission",
	"Premium Subscription": "worcent.worcent_core.permissions.premium_subscription_has_permission",
	"Dispute Case": "worcent.worcent_core.permissions.dispute_case_has_permission",
	"Agency Membership": "worcent.worcent_core.permissions.agency_membership_has_permission",
	"Verification Request": "worcent.worcent_core.permissions.verification_request_has_permission",
	"Office": "worcent.worcent_core.permissions.office_has_permission",
	"Franchise Settlement": "worcent.worcent_core.permissions.franchise_settlement_has_permission",
	"Mentor Program": "worcent.worcent_core.permissions.mentor_program_has_permission",
	"Mentorship Request": "worcent.worcent_core.permissions.mentorship_request_has_permission",
	"Work Submission": "worcent.worcent_core.permissions.work_submission_has_permission",
	"Advance Request": "worcent.worcent_core.permissions.advance_request_has_permission",
	"Wallet Top Up": "worcent.worcent_core.permissions.wallet_top_up_has_permission",
}
