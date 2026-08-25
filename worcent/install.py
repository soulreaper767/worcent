import frappe
from frappe.utils import add_days, flt, today

DEMO_PASSWORD = "Test@12345"

ALL_WORCENT_ROLES = [
	"Worcent Admin", "Freelancer", "Employer", "Office Manager", "Franchise Owner",
	"Field Rep", "Support Agent", "Dispute Arbitrator", "Finance Manager", "Agency Manager",
	"Accounts Manager", "Office Managing Partner", "Rank Reviewer",
]

# Standard ERPNext/HRMS module workspaces that have nothing to do with a
# freelance marketplace — hidden outright so the Desk sidebar only shows
# Worcent's own workspaces plus genuinely relevant back-office bits.
IRRELEVANT_WORKSPACES = [
	"Buying", "CRM", "Manufacturing", "Quality", "Selling", "Stock", "Subcontracting",
	"Support", "Website", "Assets", "Projects", "Recruitment", "Performance", "Tenure",
]

_ADMIN_TIER = ["Worcent Admin", "System Manager"]
_FINANCE_TIER = _ADMIN_TIER + ["Finance Manager"]
# Office Manager / Field Rep / Franchise Owner are the roles backed by a real
# HRMS Employee record, so HR self-service workspaces are actually relevant
# to them (everyone else has no Employee record at all).
_HR_SELF_SERVICE_TIER = _ADMIN_TIER + [
	"Office Manager", "Field Rep", "Franchise Owner", "Accounts Manager", "Office Managing Partner",
]

# Remaining (non-hidden) workspaces, scoped to the roles that actually need
# them via the Workspace's own "roles" table. Worcent's own workspaces are
# included here too so a single function call keeps all of them in sync.
WORKSPACE_ROLE_RESTRICTIONS = {
	"Worcent Admin": _ADMIN_TIER,
	"My Freelance": ["Freelancer"],
	"My Business": ["Employer"],
	"Office Ops": ["Field Rep", "Office Manager", "Franchise Owner", "Office Managing Partner", "Worcent Admin"],
	"My Agency": ["Agency Manager"],
	"Support Desk": ["Support Agent", "Worcent Admin"],
	"Dispute Resolution": ["Dispute Arbitrator", "Rank Reviewer", "Worcent Admin"],
	"Finance Ops": ["Finance Manager", "Accounts Manager", "Worcent Admin"],
	"Leaves": _HR_SELF_SERVICE_TIER,
	"Expenses": _HR_SELF_SERVICE_TIER,
	"Shift & Attendance": _HR_SELF_SERVICE_TIER,
	"Financial Reports": _FINANCE_TIER,
	"Invoicing": _FINANCE_TIER,
	"Payroll": _FINANCE_TIER,
	"Tax & Benefits": _FINANCE_TIER,
	"HR Setup": _ADMIN_TIER,
	"ERPNext Settings": _ADMIN_TIER,
	"Integrations": _ADMIN_TIER,
	"Build": _ADMIN_TIER,
	"Users": _ADMIN_TIER,
	"Home": _ADMIN_TIER,
	"Welcome Workspace": _ADMIN_TIER,
}

# Where each role lands right after login (Role.home_page — the same
# mechanism/format already proven on the caonline site: "desk/<workspace-route>").
ROLE_HOME_PAGE = {
	"Worcent Admin": "desk/worcent-admin",
	"Freelancer": "desk/my-freelance",
	"Employer": "desk/my-business",
	"Office Manager": "desk/office-ops",
	"Franchise Owner": "desk/office-ops",
	"Field Rep": "desk/office-ops",
	"Agency Manager": "desk/my-agency",
	"Support Agent": "desk/support-desk",
	"Dispute Arbitrator": "desk/dispute-resolution",
	"Finance Manager": "desk/finance-ops",
	"Accounts Manager": "desk/finance-ops",
	"Office Managing Partner": "desk/office-ops",
	"Rank Reviewer": "desk/dispute-resolution",
}


def after_install():
	configure_worcent_settings()
	seed_letterhead()
	seed_masters()
	seed_company_and_users()
	seed_agency_ecosystem()
	seed_demo_marketplace_data()
	seed_extra_marketplace_data()
	seed_agency_separation_demo()
	seed_finance_and_office_roles_demo()
	seed_referral_demo()
	seed_paid_mentorship_demo()
	seed_currency_diverse_users()
	seed_rank_demo()
	grant_cross_app_permissions()
	configure_desk_experience()
	frappe.db.set_value("Website Settings", "Website Settings", "home_page", "index")
	frappe.db.commit()


def reseed_demo_data():
	"""Callable directly (bench execute worcent.install.reseed_demo_data) to
	top up demo data on an already-installed site without re-running the
	whole after_install flow. Every step below is idempotent."""
	seed_letterhead()
	seed_masters()
	seed_company_and_users()
	seed_agency_ecosystem()
	seed_demo_marketplace_data()
	seed_extra_marketplace_data()
	seed_agency_separation_demo()
	seed_finance_and_office_roles_demo()
	seed_referral_demo()
	seed_paid_mentorship_demo()
	seed_currency_diverse_users()
	seed_rank_demo()
	configure_desk_experience()
	frappe.db.commit()


def after_migrate():
	configure_worcent_settings()
	seed_letterhead()
	seed_currencies()
	grant_cross_app_permissions()
	configure_desk_experience()
	frappe.db.commit()


def grant_cross_app_permissions():
	"""Worcent roles need read access to a handful of standard Frappe/ERPNext
	doctypes that ship locked down to HR/Accounts roles by default (Employee,
	Branch) or to System Manager only (Currency's specific role list doesn't
	include our roles). Extending core doctype permissions must go through
	Custom DocPerm (frappe.permissions.add_permission), never by editing the
	vendor app's own DocType JSON directly."""
	from frappe.permissions import add_permission

	grants = {
		"Currency": ["Freelancer", "Employer", "Worcent Admin", "Accounts Manager", "Finance Manager"],
		"Employee": [
			"Worcent Admin", "Finance Manager", "Accounts Manager",
			"Office Manager", "Franchise Owner", "Field Rep", "Office Managing Partner",
		],
		"Branch": ["Office Manager", "Franchise Owner", "Field Rep", "Office Managing Partner", "Worcent Admin"],
	}
	for doctype, roles in grants.items():
		for role in roles:
			add_permission(doctype, role, 0)


def seed_letterhead():
	"""A4-sized placeholder letterhead — swap `content` for a real logo/address
	once one is provided; everything referencing it (Print Settings default,
	print formats) keeps working unchanged since only the content changes."""
	if frappe.db.exists("Letter Head", "Worcent"):
		return
	frappe.get_doc(
		{
			"doctype": "Letter Head",
			"letter_head_name": "Worcent",
			"source": "HTML",
			"is_default": 1,
			"disabled": 0,
			"content": (
				'<div style="display:flex; align-items:center; justify-content:space-between; '
				'border-bottom:2px solid #14805e; padding-bottom:10px;">'
				'<div style="font-size:22px; font-weight:800; color:#14805e;">Worcent</div>'
				'<div style="text-align:right; font-size:11px; color:#555;">'
				"Worcent Technologies<br>support@worcent.test | worcent.local</div></div>"
			),
			"footer": (
				'<div style="text-align:center; font-size:10px; color:#888; border-top:1px solid #ddd; '
				'padding-top:6px;">Worcent — the freelance marketplace built on trust</div>'
			),
		}
	).insert(ignore_permissions=True)
	frappe.db.set_value("Print Settings", "Print Settings", "pdf_page_size", "A4")


# ---------------------------------------------------------------------------
# Desk experience: each role lands on its own workspace, and the sidebar only
# shows workspaces relevant to a freelance marketplace (mirrors the proven
# pattern already running on the caonline site).
# ---------------------------------------------------------------------------


def configure_desk_experience():
	seed_role_home_pages()
	hide_irrelevant_workspaces()
	restrict_workspace_roles()
	sync_workspace_sidebars()


def sync_workspace_sidebars():
	"""In v16 a Workspace record alone doesn't make it appear in the Desk
	sidebar — that's driven by a separate Workspace Sidebar/Workspace Sidebar
	Item pair, normally only auto-created once by Frappe's own
	after_app_install hook. Since worcent's workspaces get created/updated by
	this install.py (not by bench install-app timing), that auto-creation
	can miss them entirely — this keeps the sidebar in sync on every
	migrate. frappe's own helper is idempotent (skips any workspace that
	already has a same-named sidebar)."""
	from frappe.desk.doctype.workspace_sidebar.workspace_sidebar import (
		create_workspace_sidebar_for_workspaces,
	)

	create_workspace_sidebar_for_workspaces()
	frappe.db.commit()


def seed_role_home_pages():
	for role, route in ROLE_HOME_PAGE.items():
		if frappe.db.get_value("Role", role, "home_page") != route:
			frappe.db.set_value("Role", role, "home_page", route)
	frappe.db.commit()


def hide_irrelevant_workspaces():
	"""Runs after every other app's own module sync has already completed
	for this migrate, so setting is_hidden here is the final word."""
	for name in IRRELEVANT_WORKSPACES:
		if frappe.db.exists("Workspace", name) and not frappe.db.get_value("Workspace", name, "is_hidden"):
			frappe.db.set_value("Workspace", name, "is_hidden", 1)
	frappe.db.commit()


def restrict_workspace_roles():
	"""Scope the remaining visible workspaces to the roles that actually need
	them, via the Workspace's own 'roles' child table. Manipulates the 'Has
	Role' rows directly instead of doc.save() on the parent, so a workspace
	record that fails full re-validation for an unrelated reason can't abort
	the whole run."""
	for name, roles in WORKSPACE_ROLE_RESTRICTIONS.items():
		if not frappe.db.exists("Workspace", name):
			continue
		existing = {
			d.role for d in frappe.get_all("Has Role", filters={"parent": name, "parenttype": "Workspace"}, fields=["role"])
		}
		wanted = {r for r in roles if frappe.db.exists("Role", r)}
		if existing == wanted:
			continue
		frappe.db.delete("Has Role", {"parent": name, "parenttype": "Workspace"})
		for role in wanted:
			frappe.get_doc(
				{"doctype": "Has Role", "parent": name, "parenttype": "Workspace", "parentfield": "roles", "role": role}
			).insert(ignore_permissions=True)
	frappe.clear_cache(doctype="Workspace")
	frappe.db.commit()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def configure_worcent_settings():
	settings = frappe.get_single("Worcent Settings")
	if not settings.escrow_auto_release_days:
		settings.escrow_auto_release_days = 14
	if not settings.dispute_response_days:
		settings.dispute_response_days = 14
	if not settings.min_withdrawal_amount:
		settings.min_withdrawal_amount = 100
	if not settings.platform_currency:
		settings.platform_currency = "USD"
	if not settings.signup_bonus_amount:
		settings.signup_bonus_amount = 5
	if not settings.verification_bonus_amount:
		settings.verification_bonus_amount = 5
	if not settings.default_platform_fee_percent:
		settings.default_platform_fee_percent = 5
	if not settings.whatsapp_support_number:
		settings.whatsapp_support_number = "15550100"
	if not settings.support_email:
		settings.support_email = "support@worcent.test"
	settings.kyc_required_for_payout = 1
	settings.enable_public_profiles = 1
	settings.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Masters
# ---------------------------------------------------------------------------


def seed_masters():
	seed_skill_categories()
	seed_skills()
	seed_commission_slabs()
	seed_employer_plans()
	seed_insurance_plans()
	seed_premium_plans()
	seed_ticket_categories()
	seed_badges()
	seed_currencies()
	seed_skill_challenges()


def seed_skill_challenges():
	challenges = {
		"excel-job-ready": ("30 Days to Excel Job Ready", "Web Development", [
			"Interface basics: cells, sheets, ribbon tour", "Entering & formatting data cleanly",
			"Basic formulas: SUM, AVERAGE, COUNT", "Relative vs absolute references ($)",
			"IF statements", "Nested IF / AND / OR", "Text functions: CONCAT, LEFT/RIGHT, TRIM",
			"Date functions", "Conditional formatting", "Data validation (dropdowns)",
			"Sorting & filtering", "Removing duplicates & cleaning messy data",
			"VLOOKUP basics", "XLOOKUP / INDEX-MATCH", "Practice: build a budget tracker",
			"Intro to Pivot Tables", "Pivot Table calculated fields", "Pivot Charts",
			"Charts: bar, line, pie — when to use which", "Combo charts",
			"Named ranges", "Data tables & what-if analysis", "Goal Seek",
			"Intro to macros (recording one)", "Keyboard shortcuts speed round",
			"Building a dashboard layout", "Linking sheets & workbooks",
			"Error handling: IFERROR, ISNA", "Practice: analyze a real dataset end-to-end",
			"Polish your practice workbook for a portfolio", "Apply to 3 jobs that need Excel",
		]),
		"python-developer-ready": ("30 Days to Python Developer Ready", "Web Development", [
			"Set up your environment (Python + editor)", "Variables & data types",
			"Strings & string methods", "Lists and list methods", "Dictionaries & sets",
			"Conditionals (if/elif/else)", "Loops: for & while", "Functions basics",
			"Function arguments & return values", "Practice: build a simple calculator",
			"File I/O basics", "Error handling: try/except", "Intro to classes & objects",
			"Class methods & attributes", "Practice: build a small OOP project",
			"Intro to pip & virtual environments", "Working with JSON", "Intro to APIs & requests",
			"Practice: consume a public API", "Intro to Git & GitHub",
			"Writing your first tests", "Intro to a web framework (Flask/Frappe basics)",
			"Building a simple route/endpoint", "Connecting to a database (basic SQL)",
			"CRUD operations", "Practice: build a mini CRUD app",
			"Debugging techniques", "Code readability & clean code habits",
			"Push your project to GitHub with a README", "Apply to 3 junior developer roles/gigs",
		]),
		"accounting-basics-ready": ("30 Days to Accounting Job Ready", "Admin Support", [
			"The accounting equation (assets = liabilities + equity)", "Debits & credits basics",
			"Chart of accounts", "Journal entries", "The general ledger",
			"Trial balance", "Practice: record 10 sample transactions",
			"Intro to financial statements", "The income statement", "The balance sheet",
			"The cash flow statement", "Accounts receivable basics",
			"Accounts payable basics", "Practice: reconcile a sample AR/AP ledger",
			"Bank reconciliation step by step", "Practice: reconcile a bank statement",
			"Intro to an accounting tool (QuickBooks/Xero/ERPNext)", "Setting up a company in the tool",
			"Recording invoices", "Recording bills/expenses", "Payroll basics",
			"Tax basics in your market", "Depreciation basics", "Month-end close checklist",
			"Budgeting basics", "Practice: build a simple budget",
			"Common bookkeeping mistakes to avoid", "Client communication for bookkeepers",
			"Build a sample bookkeeping case study", "Apply to 3 bookkeeping/accounting gigs",
		]),
		"freelancing-starter": ("30 Days to Your First Freelance Client", "Admin Support", [
			"Pick your one strongest skill to lead with", "Write a one-line value proposition",
			"List 10 things you could offer as a starter gig", "Set an intro price",
			"Create/clean up your Worcent profile", "Write a strong headline & bio",
			"Add 3 portfolio pieces (real or practice)", "Get your Worcent Score up",
			"List your skills accurately", "Take the Job Readiness test for your track",
			"Write 3 message templates for proposals", "Study 5 successful gig listings in your niche",
			"Create your first Gig listing", "Browse & shortlist 10 relevant jobs",
			"Send your first 3 proposals", "Follow up on any responses",
			"Ask 2 people for a testimonial/review", "Send 3 more proposals",
			"Join a community/forum in your niche", "Reach out to 5 past contacts about work",
			"Refine your pricing based on responses so far", "Send 3 more proposals",
			"Review what's working/not working, adjust", "Offer a small free sample to a promising lead",
			"Send 3 more proposals", "Follow up on all open conversations",
			"Ask for your first review after delivering work", "Update your profile with new proof",
			"Set a weekly proposal-sending habit going forward", "Celebrate — you're in motion",
		]),
	}

	for slug, (title, category, tasks) in challenges.items():
		if frappe.db.exists("Skill Challenge", slug):
			continue
		frappe.get_doc(
			{
				"doctype": "Skill Challenge",
				"title": title,
				"slug": slug,
				"category": category,
				"total_days": len(tasks),
				"description": f"A day-by-day plan to go from zero to job-ready: {title}.",
				"daily_tasks": [
					{"day_number": i + 1, "task_title": task} for i, task in enumerate(tasks)
				],
			}
		).insert(ignore_permissions=True)


def seed_currencies():
	from worcent.worcent_finance.currency_utils import BASE_CURRENCY

	for code in ["USD", "PKR", "EUR", "GBP", "AED", "SAR"]:
		if frappe.db.exists("Currency", code):
			frappe.db.set_value("Currency", code, "enabled", 1)

	# Approximate reference rates so wallet display-currency conversion has
	# something sane to work with; a real integration can overwrite these.
	rates = {"PKR": 278, "EUR": 0.92, "GBP": 0.79, "AED": 3.67, "SAR": 3.75}
	for code, rate in rates.items():
		if not frappe.db.exists("Currency Exchange", {"from_currency": BASE_CURRENCY, "to_currency": code}):
			frappe.get_doc(
				{
					"doctype": "Currency Exchange",
					"date": today(),
					"from_currency": BASE_CURRENCY,
					"to_currency": code,
					"exchange_rate": rate,
				}
			).insert(ignore_permissions=True)
		if not frappe.db.exists("Currency Exchange", {"from_currency": code, "to_currency": BASE_CURRENCY}):
			frappe.get_doc(
				{
					"doctype": "Currency Exchange",
					"date": today(),
					"from_currency": code,
					"to_currency": BASE_CURRENCY,
					"exchange_rate": round(1 / rate, 6),
				}
			).insert(ignore_permissions=True)

	settings = frappe.get_single("Worcent Settings")
	if not settings.default_employer_plan:
		settings.default_employer_plan = "Basic"
		settings.save(ignore_permissions=True)


def seed_skill_categories():
	for name in ["Web Development", "Design & Creative", "Writing & Translation", "Sales & Marketing", "Admin Support"]:
		if not frappe.db.exists("Skill Category", name):
			frappe.get_doc({"doctype": "Skill Category", "category_name": name}).insert(ignore_permissions=True)


def seed_skills():
	skills = {
		"Web Development": ["Python", "JavaScript", "React", "Frappe Framework"],
		"Design & Creative": ["Logo Design", "UI/UX Design", "Illustration"],
		"Writing & Translation": ["Content Writing", "Copywriting", "Translation"],
		"Sales & Marketing": ["SEO", "Social Media Marketing"],
		"Admin Support": ["Data Entry", "Virtual Assistance"],
	}
	for category, names in skills.items():
		for name in names:
			if not frappe.db.exists("Skill", name):
				frappe.get_doc({"doctype": "Skill", "skill_name": name, "category": category}).insert(
					ignore_permissions=True
				)


def seed_commission_slabs():
	if frappe.db.count("Commission Slab"):
		return
	for from_amount, to_amount, rate in [(0, 500, 20), (500, 10000, 10), (10000, None, 5)]:
		frappe.get_doc(
			{
				"doctype": "Commission Slab",
				"from_amount": from_amount,
				"to_amount": to_amount,
				"rate": rate,
			}
		).insert(ignore_permissions=True)


def seed_employer_plans():
	plans = [
		("Basic", 5, 0, 0, 3),
		("Business", 8, 2, 49, 20),
		("Enterprise", 10, 5, 199, 0),
	]
	for name, fee, initiation_fee, price, max_jobs in plans:
		if not frappe.db.exists("Employer Plan", name):
			frappe.get_doc(
				{
					"doctype": "Employer Plan",
					"plan_name": name,
					"marketplace_fee_rate": fee,
					"contract_initiation_fee": initiation_fee,
					"monthly_price": price,
					"max_active_jobs": max_jobs,
				}
			).insert(ignore_permissions=True)


def seed_insurance_plans():
	plans = [
		("Freelancer Health Basic", "Health", 15, 5000),
		("Income Protection Standard", "Income Protection", 20, 10000),
	]
	for name, coverage_type, premium, coverage in plans:
		if not frappe.db.exists("Insurance Plan", name):
			frappe.get_doc(
				{
					"doctype": "Insurance Plan",
					"plan_name": name,
					"coverage_type": coverage_type,
					"premium": premium,
					"coverage_amount": coverage,
				}
			).insert(ignore_permissions=True)


def seed_premium_plans():
	plans = [
		("Freelancer Pro", "Freelancer", 9.99, "More proposals per month, featured placement, advanced profile stats"),
		("Employer Business", "Employer", 49, "Lower marketplace fee, priority support, advanced reporting"),
	]
	for name, tier_for, price, features in plans:
		if not frappe.db.exists("Premium Subscription Plan", name):
			frappe.get_doc(
				{
					"doctype": "Premium Subscription Plan",
					"plan_name": name,
					"tier_for": tier_for,
					"price": price,
					"features": features,
				}
			).insert(ignore_permissions=True)


def seed_ticket_categories():
	for name in ["General Query", "Payment Issue", "Account Issue", "Job/Contract Issue", "Verification Issue", "Technical Issue", "Other"]:
		if not frappe.db.exists("Ticket Category", name):
			frappe.get_doc({"doctype": "Ticket Category", "category_name": name}).insert(ignore_permissions=True)


def seed_badges():
	badges = [
		("Top Rated", "Top Rated", "Consistently high ratings and on-time delivery"),
		("Rising Talent", "Rising Talent", "New freelancer showing strong early performance"),
		("Verified Pro", "Verified Pro", "Fully ID and business verified"),
	]
	for name, badge_type, description in badges:
		if not frappe.db.exists("Badge", name):
			frappe.get_doc(
				{"doctype": "Badge", "badge_name": name, "badge_type": badge_type, "description": description}
			).insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Company + test users
# ---------------------------------------------------------------------------


def seed_company_and_users():
	ensure_company()
	create_user("admin1.demo@worcent.test", "Ayesha Admin", ["Worcent Admin"])
	create_user("finance1.demo@worcent.test", "Faisal Finance", ["Finance Manager"])
	create_user("support1.demo@worcent.test", "Sara Support", ["Support Agent"])
	create_user("support2.demo@worcent.test", "Sana Support", ["Support Agent"])
	create_user("arbitrator1.demo@worcent.test", "Ahmed Arbitrator", ["Dispute Arbitrator"])
	create_user("arbitrator2.demo@worcent.test", "Bushra Arbitrator", ["Dispute Arbitrator"])
	create_user("rankreviewer1.demo@worcent.test", "Rafay Reviewer", ["Rank Reviewer"])
	create_user("rankreviewer2.demo@worcent.test", "Rida Reviewer", ["Rank Reviewer"])
	create_user("franchiseowner1.demo@worcent.test", "Farhan Franchise", ["Franchise Owner"])

	freelancer1_user = create_user("freelancer1.demo@worcent.test", "Zara Freelancer")
	freelancer2_user = create_user("freelancer2.demo@worcent.test", "Bilal Freelancer")
	employer1_user = create_user("employer1.demo@worcent.test", "Nadia Employer")
	employer2_user = create_user("employer2.demo@worcent.test", "Omar Employer")
	dual_user = create_user("dual1.demo@worcent.test", "Kamran Dual")

	office_manager_user = create_user("officemanager1.demo@worcent.test", "Owais Manager")
	rep1_user = create_user("rep1.demo@worcent.test", "Rashid Rep")
	rep2_user = create_user("rep2.demo@worcent.test", "Rida Rep")

	rep3_user = create_user("rep3.demo@worcent.test", "Imran Rep")

	owned_office = ensure_office("Worcent HQ - Karachi", "Owned", manager_user=office_manager_user)
	franchised_office = ensure_office(
		"Worcent Partner - Lahore", "Franchised", franchisee_name="Farhan Franchise", franchise_fee_percent=30
	)
	franchised_office_2 = ensure_office(
		"Worcent Partner - Islamabad", "Franchised", franchisee_name="Islamabad Business Services", franchise_fee_percent=25
	)

	ensure_rep(rep1_user, owned_office, "Karachi Central")
	ensure_rep(rep2_user, franchised_office, "Lahore")
	ensure_rep(rep3_user, franchised_office_2, "Islamabad")

	freelancer1 = ensure_freelancer_profile(
		freelancer1_user, "Full-stack Frappe & React developer", 35, ["Python", "JavaScript", "React", "Frappe Framework"]
	)
	freelancer2 = ensure_freelancer_profile(
		freelancer2_user, "SEO and content marketing specialist", 20, ["SEO", "Content Writing", "Social Media Marketing"]
	)
	ensure_freelancer_profile(
		dual_user, "Product designer who also hires contract developers", 40, ["UI/UX Design", "Logo Design"]
	)

	employer1 = ensure_employer_profile(employer1_user, "Nadia Employer", "Acme Retail Co", "Retail")
	employer2 = ensure_employer_profile(employer2_user, "Omar Employer", "Bright Path Media", "Media & Publishing")
	ensure_employer_profile(dual_user, "Kamran Dual", "Kamran's Studio", "Design Services")

	frappe.db.set_value("Employer Profile", employer2, "status", "Active")
	frappe.db.set_value("Employer Profile", employer2, "published", 1)
	frappe.db.set_value("Employer Profile", employer2, "verification_level", "Email Verified")

	frappe.db.set_value("Freelancer Profile", freelancer1, "status", "Active")
	frappe.db.set_value("Freelancer Profile", freelancer1, "published", 1)
	frappe.db.set_value("Freelancer Profile", freelancer1, "verification_level", "ID Verified")
	frappe.db.set_value("Freelancer Profile", freelancer2, "status", "Active")
	frappe.db.set_value("Freelancer Profile", freelancer2, "published", 1)
	frappe.db.set_value("Employer Profile", employer1, "status", "Active")
	frappe.db.set_value("Employer Profile", employer1, "published", 1)
	frappe.db.set_value("Employer Profile", employer1, "verification_level", "Business Verified")

	if not frappe.db.exists("Mentor Program", freelancer1):
		frappe.get_doc(
			{
				"doctype": "Mentor Program",
				"mentor": freelancer1,
				"status": "Active",
				"slots_available": 3,
				"specialties": "Career growth for new Frappe developers",
				"bio": "5+ years building on Frappe/ERPNext, happy to mentor newcomers.",
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Industry Guru", freelancer1):
		frappe.get_doc(
			{
				"doctype": "Industry Guru",
				"freelancer": freelancer1,
				"industry": "Enterprise Software",
				"credentials": "10+ years, led engineering teams at 2 unicorn startups",
				"is_featured": 1,
			}
		).insert(ignore_permissions=True)

	frappe.db.commit()


def seed_finance_and_office_roles_demo():
	accounts_manager_user = create_user("accountsmanager1.demo@worcent.test", "Amina Accounts", ["Accounts Manager"])
	ensure_employee(accounts_manager_user, "Amina", "Finance")

	managing_partner_user = create_user("managingpartner1.demo@worcent.test", "Majid Partner", ["Office Managing Partner"])
	ensure_employee(managing_partner_user, "Majid", "Field Operations")
	frappe.db.commit()


def seed_referral_demo():
	"""One referral code owned by an existing demo freelancer, and one new
	freelancer who signs up using it — demonstrates the referral capture
	flow end to end (signup bonus + Referral row). Commission payout itself
	only fires once the referred user generates a real Platform Earning via
	a released milestone, which is exercised separately in the escrow tests."""
	referrer = frappe.db.get_value("Freelancer Profile", {"user": "freelancer2.demo@worcent.test"}, "name")
	if not referrer:
		return

	code_name = "WELCOME-BILAL"
	if not frappe.db.exists("Referral Code", code_name):
		frappe.get_doc(
			{
				"doctype": "Referral Code",
				"code": code_name,
				"owner_user": "freelancer2.demo@worcent.test",
				"status": "Active",
				"signup_bonus_referred": 5,
				"commission_percent_referrer": 1,
			}
		).insert(ignore_permissions=True)

	referred_user = create_user("freelancer5.demo@worcent.test", "Hina Referred")
	if not frappe.db.exists("Freelancer Profile", {"user": referred_user}):
		ensure_freelancer_profile(
			referred_user, "Junior WordPress developer", 12, ["JavaScript"],
			extra_fields={"country": "Pakistan", "referred_by_code": code_name},
		)
	frappe.db.commit()


def seed_paid_mentorship_demo():
	"""Drives one Mentorship Request all the way through payment so the
	Mentor Fee Platform Earning ledger and the mentor's net payout are both
	populated with a real example, not just zero-fee mentoring."""
	mentor = frappe.db.get_value("Freelancer Profile", {"user": "freelancer1.demo@worcent.test"}, "name")
	if not mentor or not frappe.db.exists("Mentor Program", mentor):
		return
	frappe.db.set_value("Mentor Program", mentor, "session_fee", 15)

	mentee = frappe.db.get_value("Freelancer Profile", {"user": "freelancer2.demo@worcent.test"}, "name")
	if not mentee:
		return

	from worcent.worcent_core.wallet_utils import ensure_wallet

	mentee_wallet = ensure_wallet("Freelancer Profile", mentee)
	frappe.db.set_value("Wallet", mentee_wallet, "balance", 100)

	existing = frappe.db.exists("Mentorship Request", {"mentor_program": mentor, "mentee": mentee})
	if existing:
		req = frappe.get_doc("Mentorship Request", existing)
		if not req.fee_charged and req.payment_status != "Paid":
			# Predates the session_fee being set above (e.g. seeded before this
			# demo existed) — bring it in line so the payment flow below fires.
			req.db_set("fee_charged", 15)
			req.db_set("payment_status", "Pending")
			req.reload()
	else:
		req = frappe.get_doc(
			{
				"doctype": "Mentorship Request",
				"mentor_program": mentor,
				"mentee": mentee,
				"status": "Requested",
				"session_notes": "First 1:1 session — getting started with Frappe custom apps.",
			}
		)
		req.insert(ignore_permissions=True)

	if req.status != "Accepted":
		req.status = "Accepted"
		req.save(ignore_permissions=True)
	frappe.db.commit()


def seed_currency_diverse_users():
	"""A couple of demo profiles outside Pakistan so preferred_currency isn't
	uniformly PKR across every seeded account."""
	uk_employer_user = create_user("employer3.demo@worcent.test", "Oliver UK")
	ensure_employer_profile(
		uk_employer_user, "Oliver UK", "Thames Digital Agency", "Media & Publishing",
		extra_fields={"country": "United Kingdom"},
	)

	uae_freelancer_user = create_user("freelancer6.demo@worcent.test", "Yousef Dubai")
	ensure_freelancer_profile(
		uae_freelancer_user, "Mobile app developer", 45, ["Python", "React"],
		extra_fields={"country": "United Arab Emirates"},
	)
	frappe.db.commit()


def seed_rank_demo():
	"""Exercises both Rank Application paths so the demo data shows a clean
	approval and a rejected-then-appealed-and-upheld example, each reviewed
	by a different Rank Reviewer (the appeal enforces a second reviewer)."""
	freelancer1 = frappe.db.get_value("Freelancer Profile", {"user": "freelancer1.demo@worcent.test"}, "name")
	freelancer2 = frappe.db.get_value("Freelancer Profile", {"user": "freelancer2.demo@worcent.test"}, "name")

	if freelancer1 and not frappe.db.exists("Rank Application", {"freelancer": freelancer1}):
		app1 = frappe.get_doc(
			{
				"doctype": "Rank Application",
				"freelancer": freelancer1,
				"requested_rank": "Silver",
				"justification": "Strong track record on Worcent plus 5+ years of prior agency experience.",
			}
		)
		app1.insert(ignore_permissions=True)
		frappe.set_user("rankreviewer1.demo@worcent.test")
		frappe.get_doc("Rank Application", app1.name).approve("Solid history, approved.")
		frappe.set_user("Administrator")

	if freelancer2 and not frappe.db.exists("Rank Application", {"freelancer": freelancer2}):
		app2 = frappe.get_doc(
			{
				"doctype": "Rank Application",
				"freelancer": freelancer2,
				"requested_rank": "Silver",
				"justification": "Recently featured in an industry newsletter; picking up more marketing clients.",
			}
		)
		app2.insert(ignore_permissions=True)
		frappe.set_user("rankreviewer1.demo@worcent.test")
		frappe.get_doc("Rank Application", app2.name).reject("Not enough completed jobs on Worcent yet.")
		frappe.set_user("freelancer2.demo@worcent.test")
		from worcent.worcent_core.wallet_utils import ensure_wallet

		frappe.db.set_value("Wallet", ensure_wallet("Freelancer Profile", freelancer2), "balance", 50)
		frappe.get_doc("Rank Application", app2.name).appeal()
		frappe.set_user("rankreviewer2.demo@worcent.test")
		frappe.get_doc("Rank Application", app2.name).approve("On reconsideration, the newsletter feature is a fair basis.")
		frappe.set_user("Administrator")

	frappe.db.commit()


def ensure_company():
	if frappe.db.exists("Company", "Worcent Platform"):
		return "Worcent Platform"

	# Normally seeded by the Setup Wizard; needed by Company.create_default_warehouses()
	for warehouse_type in ("Transit",):
		if not frappe.db.exists("Warehouse Type", warehouse_type):
			frappe.get_doc({"doctype": "Warehouse Type", "name": warehouse_type}).insert(ignore_permissions=True)

	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": "Worcent Platform",
			"abbr": "WCT",
			"default_currency": "USD",
			"country": "United States",
		}
	)
	company.insert(ignore_permissions=True)
	frappe.db.set_default("company", company.name)
	return company.name


def create_user(email, full_name, roles=None):
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		first, *rest = full_name.split(" ", 1)
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first,
				"last_name": rest[0] if rest else "",
				"send_welcome_email": 0,
				"enabled": 1,
			}
		)
		user.insert(ignore_permissions=True)
		user.new_password = DEMO_PASSWORD
		user.save(ignore_permissions=True)

	existing_roles = {r.role for r in user.roles}
	for role in roles or []:
		if role not in existing_roles:
			user.append("roles", {"role": role})
	user.save(ignore_permissions=True)
	return user.name


def ensure_office(office_name, office_type, manager_user=None, franchisee_name=None, franchise_fee_percent=None):
	if frappe.db.exists("Office", office_name):
		return office_name

	manager_employee = None
	if manager_user:
		first_name = frappe.db.get_value("User", manager_user, "first_name")
		manager_employee = ensure_employee(manager_user, first_name, office_name)
		user = frappe.get_doc("User", manager_user)
		if "Office Manager" not in [r.role for r in user.roles]:
			user.append("roles", {"role": "Office Manager"})
			user.save(ignore_permissions=True)

	office = frappe.get_doc(
		{
			"doctype": "Office",
			"office_name": office_name,
			"office_type": office_type,
			"status": "Active",
			"franchisee_name": franchisee_name,
			"franchise_fee_percent": franchise_fee_percent,
			"manager": manager_employee,
			"city": office_name.split("-")[-1].strip() if "-" in office_name else "",
			"country": "United States",
		}
	)
	office.insert(ignore_permissions=True)
	return office.name


def ensure_employee(user_email, first_name, department_hint):
	existing = frappe.db.get_value("Employee", {"user_id": user_email}, "name")
	if existing:
		return existing
	company = frappe.db.get_default("company") or ensure_company()
	if not frappe.db.exists("Gender", "Other"):
		frappe.get_doc({"doctype": "Gender", "gender": "Other"}).insert(ignore_permissions=True)
	employee = frappe.get_doc(
		{
			"doctype": "Employee",
			"employee_name": frappe.db.get_value("User", user_email, "full_name") or first_name,
			"first_name": first_name,
			"user_id": user_email,
			"company": company,
			"status": "Active",
			"date_of_joining": today(),
			"gender": "Other",
			"date_of_birth": add_days(today(), -365 * 30),
		}
	)
	employee.insert(ignore_permissions=True)
	return employee.name


def ensure_rep(user_email, office, territory):
	employee = ensure_employee(user_email, frappe.db.get_value("User", user_email, "first_name"), office)
	existing = frappe.db.get_value("Rep", {"employee": employee}, "name")
	if existing:
		return existing
	rep = frappe.get_doc(
		{
			"doctype": "Rep",
			"employee": employee,
			"office": office,
			"territory": territory,
			"status": "Active",
			"commission_per_job": 5,
		}
	)
	rep.insert(ignore_permissions=True)
	return rep.name


def ensure_freelancer_profile(user_email, headline, hourly_rate, skill_names, extra_fields=None):
	existing = frappe.db.get_value("Freelancer Profile", {"user": user_email}, "name")
	if existing:
		return existing
	profile = frappe.get_doc(
		{
			"doctype": "Freelancer Profile",
			"user": user_email,
			"headline": headline,
			"hourly_rate": hourly_rate,
			"availability": "Full Time",
			"status": "Pending Verification",
			"bio": headline,
			"skills": [{"skill": s, "proficiency": "Expert", "years_experience": 5} for s in skill_names],
			**(extra_fields or {}),
		}
	)
	profile.insert(ignore_permissions=True)
	return profile.name


def ensure_employer_profile(user_email, contact_name, company_name, industry, extra_fields=None):
	existing = frappe.db.get_value("Employer Profile", {"user": user_email}, "name")
	if existing:
		return existing
	profile = frappe.get_doc(
		{
			"doctype": "Employer Profile",
			"user": user_email,
			"company_name": company_name,
			"industry": industry,
			"status": "Pending Verification",
			"bio": f"{company_name} is hiring on Worcent.",
			**(extra_fields or {}),
		}
	)
	profile.insert(ignore_permissions=True)
	return profile.name


# ---------------------------------------------------------------------------
# Demo marketplace flow (job -> proposal -> contract -> escrow -> release)
# ---------------------------------------------------------------------------


def seed_demo_marketplace_data():
	from worcent.worcent_finance.escrow_engine import fund_milestone, release_milestone
	from worcent.worcent_core.wallet_utils import ensure_wallet

	freelancer1 = frappe.db.get_value("Freelancer Profile", {"user": "freelancer1.demo@worcent.test"}, "name")
	freelancer2 = frappe.db.get_value("Freelancer Profile", {"user": "freelancer2.demo@worcent.test"}, "name")
	employer1 = frappe.db.get_value("Employer Profile", {"user": "employer1.demo@worcent.test"}, "name")
	if not (freelancer1 and freelancer2 and employer1):
		return

	job = ensure_job_posting(
		employer1,
		"Build a customer portal on Frappe",
		"We need a Frappe-based customer self-service portal with login, order history and support tickets.",
		"Web Development",
		"Fixed",
		2000,
		4000,
		["Python", "Frappe Framework"],
	)
	ensure_job_posting(
		employer1,
		"SEO audit and 3-month content plan",
		"Looking for an experienced SEO freelancer to audit our site and build a content calendar.",
		"Sales & Marketing",
		"Fixed",
		500,
		1200,
		["SEO", "Content Writing"],
	)

	if not frappe.db.exists("Gig", {"freelancer": freelancer2, "title": "I will do a full SEO audit of your website"}):
		frappe.get_doc(
			{
				"doctype": "Gig",
				"freelancer": freelancer2,
				"title": "I will do a full SEO audit of your website",
				"category": "Sales & Marketing",
				"status": "Active",
				"published": 1,
				"description": "Comprehensive technical + content SEO audit with a prioritized action plan.",
				"packages": [
					{"package_type": "Basic", "price": 80, "delivery_days": 3, "revisions": 1, "description": "Technical audit only"},
					{"package_type": "Standard", "price": 150, "delivery_days": 5, "revisions": 2, "description": "Technical + content audit"},
					{"package_type": "Premium", "price": 300, "delivery_days": 7, "revisions": 3, "description": "Full audit + 3-month plan"},
				],
			}
		).insert(ignore_permissions=True)

	proposal_name = ensure_proposal(job, freelancer1, 3200, 30, "I've built several Frappe portals — happy to share examples. Can start this week.")

	contract = ensure_contract(job, None, proposal_name, freelancer1, employer1, "Fixed", 3200)

	milestone1 = ensure_milestone(contract, "Design & data model", 1200, "Submitted")
	milestone2 = ensure_milestone(contract, "Build & deploy portal", 2000, "Pending")

	ensure_wallet("Employer Profile", employer1)
	frappe.db.set_value("Wallet", frappe.db.get_value("Wallet", {"party": employer1}, "name"), "balance", 10000)

	m1_doc = frappe.get_doc("Milestone", milestone1)
	if m1_doc.status == "Submitted" and not frappe.db.exists("Escrow Transaction", {"milestone": milestone1}):
		fund_milestone(milestone1)
		if not frappe.db.exists("Work Submission", {"milestone": milestone1}):
			frappe.get_doc(
				{
					"doctype": "Work Submission",
					"milestone": milestone1,
					"notes": "Data model + wireframes attached for review.",
					"status": "Submitted",
				}
			).insert(ignore_permissions=True)
		release_milestone(milestone1)

	if not frappe.db.exists("Review", {"contract": contract, "reviewer_type": "Employer"}):
		frappe.get_doc(
			{
				"doctype": "Review",
				"contract": contract,
				"reviewer_type": "Employer",
				"reviewer": "employer1.demo@worcent.test",
				"reviewee_type": "Freelancer Profile",
				"reviewee_profile": freelancer1,
				"rating": 1,
				"comment": "Excellent first milestone, clear communication throughout.",
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Support Ticket", {"subject": "Can't see my released milestone payment"}):
		frappe.get_doc(
			{
				"doctype": "Support Ticket",
				"subject": "Can't see my released milestone payment",
				"raised_by": "freelancer2.demo@worcent.test",
				"category": "Payment Issue",
				"priority": "Medium",
				"status": "Open",
				"description": "My milestone was approved but I don't see it reflected in my wallet balance yet.",
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Dispute Case", {"contract": contract}):
		frappe.get_doc(
			{
				"doctype": "Dispute Case",
				"contract": contract,
				"milestone": milestone2,
				"raised_by": "employer1.demo@worcent.test",
				"against": "Freelancer",
				"status": "Open",
				"reason": "Milestone 2 deadline was missed by a week without prior notice.",
			}
		).insert(ignore_permissions=True)

	frappe.db.commit()


def ensure_job_posting(employer, title, description, category, budget_type, budget_min, budget_max, skill_names):
	existing = frappe.db.get_value("Job Posting", {"employer": employer, "title": title}, "name")
	if existing:
		return existing
	job = frappe.get_doc(
		{
			"doctype": "Job Posting",
			"employer": employer,
			"title": title,
			"description": description,
			"category": category,
			"budget_type": budget_type,
			"budget_min": budget_min,
			"budget_max": budget_max,
			"status": "Open",
			"published": 1,
			"skills_required": [{"skill": s} for s in skill_names],
		}
	)
	job.insert(ignore_permissions=True)
	return job.name


def ensure_proposal(job, freelancer, bid_amount, delivery_days, cover_letter, gig=None):
	filters = {"job_posting": job, "freelancer": freelancer} if job else {"gig": gig, "freelancer": freelancer}
	existing = frappe.db.get_value("Proposal", filters, "name")
	if existing:
		return existing
	proposal = frappe.get_doc(
		{
			"doctype": "Proposal",
			"job_posting": job,
			"gig": gig,
			"freelancer": freelancer,
			"bid_amount": bid_amount,
			"delivery_days": delivery_days,
			"cover_letter": cover_letter,
			"status": "Accepted",
		}
	)
	proposal.insert(ignore_permissions=True)
	return proposal.name


def ensure_contract(job, gig, proposal, freelancer, employer, contract_type, rate):
	existing = frappe.db.get_value("Contract", {"proposal": proposal}, "name")
	if existing:
		return existing
	contract = frappe.get_doc(
		{
			"doctype": "Contract",
			"job_posting": job,
			"gig": gig,
			"proposal": proposal,
			"freelancer": freelancer,
			"employer": employer,
			"contract_type": contract_type,
			"rate": rate,
			"status": "Active",
		}
	)
	contract.insert(ignore_permissions=True)
	if job:
		frappe.db.set_value("Job Posting", job, "status", "In Progress")
	return contract.name


def ensure_milestone(contract, title, amount, status):
	existing = frappe.db.get_value("Milestone", {"contract": contract, "title": title}, "name")
	if existing:
		return existing
	milestone = frappe.get_doc(
		{
			"doctype": "Milestone",
			"contract": contract,
			"title": title,
			"amount": amount,
			"due_date": add_days(today(), 14),
			"status": status,
		}
	)
	milestone.insert(ignore_permissions=True)
	return milestone.name


def fund_submit_and_release(milestone, notes="Work delivered as scoped, ready for review."):
	"""Drive a Pending/Submitted milestone all the way to Released through
	the real escrow_engine calls, same as a live employer/freelancer would."""
	from worcent.worcent_finance.escrow_engine import fund_milestone, release_milestone

	if not frappe.db.exists("Escrow Transaction", {"milestone": milestone}):
		fund_milestone(milestone)
	if not frappe.db.exists("Work Submission", {"milestone": milestone}):
		frappe.get_doc(
			{"doctype": "Work Submission", "milestone": milestone, "notes": notes, "status": "Submitted"}
		).insert(ignore_permissions=True)
	if frappe.db.get_value("Milestone", milestone, "status") != "Released":
		release_milestone(milestone)


def ensure_review(contract, reviewer_type, reviewer_user, reviewee_type, reviewee, rating, comment):
	if frappe.db.exists("Review", {"contract": contract, "reviewer_type": reviewer_type, "reviewee_profile": reviewee}):
		return
	frappe.get_doc(
		{
			"doctype": "Review",
			"contract": contract,
			"reviewer_type": reviewer_type,
			"reviewer": reviewer_user,
			"reviewee_type": reviewee_type,
			"reviewee_profile": reviewee,
			"rating": rating,
			"comment": comment,
		}
	).insert(ignore_permissions=True)


def top_up_wallet(party_type, party, amount):
	from worcent.worcent_core.wallet_utils import ensure_wallet

	wallet_name = ensure_wallet(party_type, party)
	wallet = frappe.get_doc("Wallet", wallet_name)
	wallet.balance = flt(wallet.balance) + flt(amount)
	wallet.save(ignore_permissions=True)
	return wallet_name


# ---------------------------------------------------------------------------
# Agencies: agency-affiliated freelancers, and career history on separation
# ---------------------------------------------------------------------------


def seed_agency_ecosystem():
	agency_owner_1 = create_user("agencyowner1.demo@worcent.test", "Adeel Agency", ["Agency Manager"])
	create_user("agencyowner2.demo@worcent.test", "Beenish Agency", ["Agency Manager"])

	agency1 = ensure_agency(agency_owner_1, "Pixel Perfect Studio", "Design & Creative", "A boutique creative studio pairing vetted designers and writers with growing brands.")
	ensure_agency("agencyowner2.demo@worcent.test", "WordSmith Collective", "Writing & Translation", "A collective of professional writers and translators for content-heavy businesses.")

	freelancer3_user = create_user("freelancer3.demo@worcent.test", "Hina Freelancer")
	freelancer4_user = create_user("freelancer4.demo@worcent.test", "Junaid Freelancer")

	freelancer3 = ensure_freelancer_profile(
		freelancer3_user, "Brand identity and illustration designer", 28, ["Illustration", "Logo Design", "UI/UX Design"]
	)
	freelancer4 = ensure_freelancer_profile(
		freelancer4_user, "Long-form content writer for SaaS and fintech", 22, ["Content Writing", "Copywriting"]
	)
	frappe.db.set_value("Freelancer Profile", freelancer3, "status", "Active")
	frappe.db.set_value("Freelancer Profile", freelancer3, "published", 1)
	frappe.db.set_value("Freelancer Profile", freelancer4, "status", "Active")
	frappe.db.set_value("Freelancer Profile", freelancer4, "published", 1)

	# freelancer3 stays an active agency member throughout the demo.
	ensure_agency_membership(agency1, freelancer3)

	frappe.db.commit()


def ensure_agency(owner_user, agency_name, industry, bio):
	existing = frappe.db.get_value("Agency", {"agency_name": agency_name}, "name")
	if existing:
		return existing
	agency = frappe.get_doc(
		{
			"doctype": "Agency",
			"agency_name": agency_name,
			"owner_user": owner_user,
			"status": "Active",
			"published": 1,
			"verification_level": "Business Verified",
			"bio": bio,
		}
	)
	agency.insert(ignore_permissions=True)
	return agency.name


def ensure_agency_membership(agency, freelancer, status="Active"):
	existing = frappe.db.get_value("Agency Membership", {"agency": agency, "freelancer": freelancer}, "name")
	if existing:
		return existing
	membership = frappe.get_doc(
		{"doctype": "Agency Membership", "agency": agency, "freelancer": freelancer, "status": status}
	)
	membership.insert(ignore_permissions=True)
	return membership.name


def seed_agency_separation_demo():
	"""The headline scenario the platform needs to demonstrate: a freelancer
	joins an agency, completes real paid work while affiliated, then
	separates — and their jobs/earnings/rating from that period stay
	permanently visible on their own public profile as career history."""
	agency1 = frappe.db.get_value("Agency", {"agency_name": "Pixel Perfect Studio"}, "name")
	freelancer4 = frappe.db.get_value("Freelancer Profile", {"user": "freelancer4.demo@worcent.test"}, "name")
	employer2 = frappe.db.get_value("Employer Profile", {"user": "employer2.demo@worcent.test"}, "name")
	if not (agency1 and freelancer4 and employer2):
		return

	membership = ensure_agency_membership(agency1, freelancer4, status="Active")

	# Do a full paid contract *while* freelancer4 is an active agency member,
	# so the contract records the agency and the payout counts toward their
	# jobs_completed / total_earned before we separate them.
	job = ensure_job_posting(
		employer2,
		"Write 10 blog posts for our fintech launch",
		"Need a strong technical writer to produce 10 SEO-friendly blog posts (1200-1500 words each) for our product launch.",
		"Writing & Translation",
		"Fixed",
		1000,
		1500,
		["Content Writing", "Copywriting"],
	)
	proposal = ensure_proposal(job, freelancer4, 1300, 20, "I've written extensively for fintech clients — portfolio attached.")
	contract = ensure_contract(job, None, proposal, freelancer4, employer2, "Fixed", 1300)
	milestone = ensure_milestone(contract, "Deliver 10 blog posts", 1300, "Pending")

	top_up_wallet("Employer Profile", employer2, 5000)
	fund_submit_and_release(milestone, notes="All 10 posts delivered, SEO-optimized, with meta descriptions.")

	ensure_review(
		contract, "Employer", "employer2.demo@worcent.test", "Freelancer Profile", freelancer4,
		1, "Fantastic writer, hit every deadline. Would happily work with them again directly.",
	)
	contract_doc = frappe.get_doc("Contract", contract)
	if contract_doc.status != "Completed":
		contract_doc.status = "Completed"
		contract_doc.save(ignore_permissions=True)
	frappe.db.set_value("Job Posting", job, "status", "Completed")

	# Now separate them from the agency — this is what snapshots the
	# jobs/earnings/rating achieved above onto their permanent career history.
	membership_doc = frappe.get_doc("Agency Membership", membership)
	if membership_doc.status != "Separated":
		membership_doc.status = "Separated"
		membership_doc.separation_note = "Went independent to work directly with clients."
		membership_doc.save(ignore_permissions=True)

	frappe.db.commit()


# ---------------------------------------------------------------------------
# Everything else: more jobs/gigs/contracts at varied stages, dispute
# resolution, withdrawals, advances, insurance, subscriptions, verification,
# physical verification, assisted requests, mentorship, franchise settlement.
# ---------------------------------------------------------------------------


def seed_extra_marketplace_data():
	freelancer1 = frappe.db.get_value("Freelancer Profile", {"user": "freelancer1.demo@worcent.test"}, "name")
	freelancer2 = frappe.db.get_value("Freelancer Profile", {"user": "freelancer2.demo@worcent.test"}, "name")
	freelancer3 = frappe.db.get_value("Freelancer Profile", {"user": "freelancer3.demo@worcent.test"}, "name")
	dual_freelancer = frappe.db.get_value("Freelancer Profile", {"user": "dual1.demo@worcent.test"}, "name")
	employer1 = frappe.db.get_value("Employer Profile", {"user": "employer1.demo@worcent.test"}, "name")
	employer2 = frappe.db.get_value("Employer Profile", {"user": "employer2.demo@worcent.test"}, "name")
	dual_employer = frappe.db.get_value("Employer Profile", {"user": "dual1.demo@worcent.test"}, "name")
	if not (freelancer1 and freelancer2 and freelancer3 and employer1 and employer2):
		return

	top_up_wallet("Employer Profile", employer1, 10000)
	top_up_wallet("Employer Profile", employer2, 5000)
	top_up_wallet("Employer Profile", dual_employer, 3000)

	# --- more open jobs across categories, some posted via a field rep for
	# users who called it in rather than using the site (the assisted flow) ---
	ensure_job_posting(
		employer1, "Redesign our product landing page", "Looking for a UI/UX designer to modernize our SaaS landing page and improve conversion.",
		"Design & Creative", "Fixed", 600, 1500, ["UI/UX Design", "Logo Design"],
	)
	ensure_job_posting(
		employer2, "Weekly newsletter ghostwriting (ongoing)", "Need a writer to ghostwrite our weekly newsletter, hourly, ongoing engagement.",
		"Writing & Translation", "Hourly", 15, 30, ["Copywriting", "Content Writing"],
	)
	rep_posted_job = ensure_job_posting(
		dual_employer, "Data entry for 2,000 product listings", "Bulk data entry job, no smartphone needed to apply — call our local office.",
		"Admin Support", "Fixed", 150, 300, ["Data Entry"],
	)

	# --- more gigs ---
	if not frappe.db.exists("Gig", {"freelancer": freelancer1, "title": "I will build your Frappe/ERPNext custom app"}):
		frappe.get_doc(
			{
				"doctype": "Gig", "freelancer": freelancer1, "title": "I will build your Frappe/ERPNext custom app",
				"category": "Web Development", "status": "Active", "published": 1,
				"description": "End-to-end custom Frappe app: doctypes, workflows, website, deployed and documented.",
				"packages": [
					{"package_type": "Basic", "price": 300, "delivery_days": 5, "revisions": 1, "description": "Single doctype + list/report"},
					{"package_type": "Standard", "price": 800, "delivery_days": 10, "revisions": 2, "description": "Small app, 3-5 doctypes"},
					{"package_type": "Premium", "price": 2000, "delivery_days": 21, "revisions": 3, "description": "Full module with website + roles"},
				],
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Gig", {"freelancer": freelancer3, "title": "I will design a complete brand identity kit"}):
		frappe.get_doc(
			{
				"doctype": "Gig", "freelancer": freelancer3, "title": "I will design a complete brand identity kit",
				"category": "Design & Creative", "status": "Active", "published": 1,
				"description": "Logo, color palette, typography and a mini brand guideline PDF.",
				"packages": [
					{"package_type": "Basic", "price": 120, "delivery_days": 4, "revisions": 2, "description": "Logo only"},
					{"package_type": "Standard", "price": 250, "delivery_days": 7, "revisions": 3, "description": "Logo + palette + type"},
					{"package_type": "Premium", "price": 450, "delivery_days": 10, "revisions": 4, "description": "Full brand kit + guideline PDF"},
				],
			}
		).insert(ignore_permissions=True)

	# --- Contract 2: Pending, no funding yet (proposal just accepted) ---
	job2 = ensure_job_posting(
		employer1, "Build an internal reporting dashboard", "Need custom reports and dashboards built on our existing Frappe site.",
		"Web Development", "Fixed", 800, 1600, ["Python", "Frappe Framework"],
	)
	proposal2 = ensure_proposal(job2, freelancer2, 1400, 15, "I can start immediately, similar dashboards built before.")
	contract2 = ensure_contract(job2, None, proposal2, freelancer2, employer1, "Fixed", 1400)
	ensure_milestone(contract2, "Requirements & wireframes", 400, "Pending")
	ensure_milestone(contract2, "Build dashboards", 1000, "Pending")

	# --- Contract 3: one milestone Funded, awaiting submission ---
	job3 = ensure_job_posting(
		employer2, "Illustrate 5 blog header images", "Custom illustrated header images matching our brand style.",
		"Design & Creative", "Fixed", 300, 600, ["Illustration"],
	)
	proposal3 = ensure_proposal(job3, freelancer3, 500, 10, "Love this kind of editorial illustration work — samples attached.")
	contract3 = ensure_contract(job3, None, proposal3, freelancer3, employer2, "Fixed", 500)
	milestone3 = ensure_milestone(contract3, "5 illustrated headers", 500, "Pending")
	if not frappe.db.exists("Escrow Transaction", {"milestone": milestone3}):
		from worcent.worcent_finance.escrow_engine import fund_milestone

		fund_milestone(milestone3)

	# --- Contract 4: Gig-based, fully released ---
	seo_gig = frappe.db.get_value("Gig", {"freelancer": freelancer2}, "name")
	if seo_gig:
		proposal4 = ensure_proposal(None, freelancer2, 150, 5, "Ordering the Standard SEO audit package.", gig=seo_gig)
		contract4 = ensure_contract(None, seo_gig, proposal4, freelancer2, dual_employer, "Gig", 150)
		milestone4 = ensure_milestone(contract4, "SEO audit delivery", 150, "Pending")
		fund_submit_and_release(milestone4, notes="Full audit report + prioritized action plan delivered.")
		contract4_doc = frappe.get_doc("Contract", contract4)
		if contract4_doc.status != "Completed":
			contract4_doc.status = "Completed"
			contract4_doc.save(ignore_permissions=True)
		ensure_review(contract4, "Employer", "dual1.demo@worcent.test", "Freelancer Profile", freelancer2, 0.9, "Thorough audit, actionable recommendations.")
		ensure_review(contract4, "Freelancer", "freelancer2.demo@worcent.test", "Employer Profile", dual_employer, 1, "Clear scope, paid promptly.")

	# --- rep-assisted job posting conversion (non-smartphone flow) ---
	rep1 = frappe.db.get_value("Rep", {"territory": "Karachi Central"}, "name")
	if rep1 and not frappe.db.exists("Assisted Request", {"requester_phone": "+92-300-1112222"}):
		frappe.get_doc(
			{
				"doctype": "Assisted Request", "rep": rep1, "requester_name": "Kamran Dual (via phone)",
				"requester_phone": "+92-300-1112222", "request_type": "Post Job", "status": "Converted",
				"details": "Client called in wanting bulk data entry work posted — no smartphone, walked through the office.",
				"converted_to_doctype": "Job Posting", "converted_to_name": rep_posted_job,
			}
		).insert(ignore_permissions=True)
	rep2 = frappe.db.get_value("Rep", {"territory": "Lahore"}, "name")
	if rep2 and not frappe.db.exists("Assisted Request", {"requester_phone": "+92-321-4445555"}):
		frappe.get_doc(
			{
				"doctype": "Assisted Request", "rep": rep2, "requester_name": "Saima Bibi",
				"requester_phone": "+92-321-4445555", "request_type": "Register as Freelancer", "status": "New",
				"details": "Walked into the Lahore office wanting to register as a stitching/tailoring freelancer.",
			}
		).insert(ignore_permissions=True)

	# --- physical verification appointments ---
	office1 = frappe.db.get_value("Office", {"office_type": "Owned"}, "name")
	if office1 and rep1 and not frappe.db.exists("Physical Verification Appointment", {"party": freelancer1}):
		frappe.get_doc(
			{
				"doctype": "Physical Verification Appointment", "office": office1, "rep": rep1,
				"party_type": "Freelancer Profile", "party": freelancer1, "verification_type": "ID",
				"scheduled_date": add_days(today(), -10), "status": "Completed",
				"result_notes": "CNIC verified in person, matches profile details.",
			}
		).insert(ignore_permissions=True)
	if office1 and rep1 and employer1 and not frappe.db.exists("Physical Verification Appointment", {"party": employer1}):
		frappe.get_doc(
			{
				"doctype": "Physical Verification Appointment", "office": office1, "rep": rep1,
				"party_type": "Employer Profile", "party": employer1, "verification_type": "Business",
				"scheduled_date": add_days(today(), -6), "status": "Completed",
				"result_notes": "Business registration certificate verified.",
			}
		).insert(ignore_permissions=True)
	if office1 and rep1 and freelancer2 and not frappe.db.exists("Physical Verification Appointment", {"party": freelancer2}):
		frappe.get_doc(
			{
				"doctype": "Physical Verification Appointment", "office": office1, "rep": rep1,
				"party_type": "Freelancer Profile", "party": freelancer2, "verification_type": "Address",
				"scheduled_date": add_days(today(), 3), "status": "Scheduled",
			}
		).insert(ignore_permissions=True)

	# --- verification requests (the online/self-serve counterpart) ---
	if not frappe.db.exists("Verification Request", {"party": freelancer1, "verification_type": "ID"}):
		frappe.get_doc(
			{
				"doctype": "Verification Request", "party_type": "Freelancer Profile", "party": freelancer1,
				"verification_type": "ID", "status": "Approved", "reviewed_by": "admin1.demo@worcent.test",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Verification Request", {"party": freelancer3, "verification_type": "ID"}):
		frappe.get_doc(
			{
				"doctype": "Verification Request", "party_type": "Freelancer Profile", "party": freelancer3,
				"verification_type": "ID", "status": "Pending",
			}
		).insert(ignore_permissions=True)

	# --- withdrawal requests ---
	freelancer1_wallet = frappe.db.get_value("Wallet", {"party": freelancer1}, "name")
	if freelancer1_wallet and not frappe.db.exists("Withdrawal Request", {"wallet": freelancer1_wallet}):
		wr = frappe.get_doc(
			{
				"doctype": "Withdrawal Request", "wallet": freelancer1_wallet, "amount": 400,
				"method": "Bank Transfer", "status": "Paid", "paid_on": frappe.utils.now_datetime(),
			}
		)
		wr.insert(ignore_permissions=True)
		wallet = frappe.get_doc("Wallet", freelancer1_wallet)
		wallet.balance = flt(wallet.balance) - 400
		wallet.total_withdrawn = flt(wallet.total_withdrawn) + 400
		wallet.save(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Wallet Transaction", "wallet": freelancer1_wallet, "transaction_type": "Withdrawal",
				"direction": "Debit", "amount": 400, "balance_after": wallet.balance,
				"reference_doctype": "Withdrawal Request", "reference_name": wr.name,
			}
		).insert(ignore_permissions=True)

	freelancer2_wallet = frappe.db.get_value("Wallet", {"party": freelancer2}, "name")
	if freelancer2_wallet and not frappe.db.exists(
		"Withdrawal Request", {"wallet": freelancer2_wallet, "status": "Pending"}
	):
		frappe.get_doc(
			{"doctype": "Withdrawal Request", "wallet": freelancer2_wallet, "amount": 100, "method": "PayPal", "status": "Pending"}
		).insert(ignore_permissions=True)

	# --- advance request, disbursed ---
	if not frappe.db.exists("Advance Request", {"freelancer": freelancer2}):
		adv = frappe.get_doc(
			{
				"doctype": "Advance Request", "freelancer": freelancer2, "amount_requested": 200,
				"against_contract": contract2, "interest_rate": 3, "status": "Approved",
				"repayment_schedule": [
					{"due_date": add_days(today(), 30), "amount": 100, "status": "Pending"},
					{"due_date": add_days(today(), 60), "amount": 100, "status": "Pending"},
				],
			}
		)
		adv.insert(ignore_permissions=True)
		adv.status = "Disbursed"
		adv.save(ignore_permissions=True)

	# --- insurance policy + claim ---
	health_plan = frappe.db.get_value("Insurance Plan", {"coverage_type": "Health"}, "name")
	if health_plan and not frappe.db.exists("Insurance Policy", {"freelancer": freelancer1}):
		policy = frappe.get_doc(
			{
				"doctype": "Insurance Policy", "freelancer": freelancer1, "insurance_plan": health_plan,
				"status": "Active", "start_date": add_days(today(), -60), "end_date": add_days(today(), 305),
			}
		)
		policy.insert(ignore_permissions=True)
		if not frappe.db.exists("Insurance Claim", {"policy": policy.name}):
			frappe.get_doc(
				{
					"doctype": "Insurance Claim", "policy": policy.name, "reason": "Minor medical expense reimbursement",
					"amount_claimed": 120, "status": "Approved",
				}
			).insert(ignore_permissions=True)

	# --- premium subscriptions ---
	pro_plan = frappe.db.get_value("Premium Subscription Plan", {"tier_for": "Freelancer"}, "name")
	if pro_plan and not frappe.db.exists("Premium Subscription", {"user": "freelancer1.demo@worcent.test"}):
		frappe.get_doc(
			{
				"doctype": "Premium Subscription", "user": "freelancer1.demo@worcent.test", "plan": pro_plan,
				"status": "Active", "start_date": add_days(today(), -20), "renews_on": add_days(today(), 10),
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Freelancer Profile", freelancer1, "premium_tier", "Pro")

	business_plan = frappe.db.get_value("Premium Subscription Plan", {"tier_for": "Employer"}, "name")
	if business_plan and not frappe.db.exists("Premium Subscription", {"user": "employer1.demo@worcent.test"}):
		frappe.get_doc(
			{
				"doctype": "Premium Subscription", "user": "employer1.demo@worcent.test", "plan": business_plan,
				"status": "Active", "start_date": add_days(today(), -15), "renews_on": add_days(today(), 15),
			}
		).insert(ignore_permissions=True)

	# --- mentorship request ---
	mentor_program = frappe.db.get_value("Mentor Program", {"mentor": freelancer1}, "name")
	if mentor_program and not frappe.db.exists("Mentorship Request", {"mentee": freelancer2}):
		frappe.get_doc(
			{
				"doctype": "Mentorship Request", "mentor_program": mentor_program, "mentee": freelancer2,
				"status": "Accepted", "session_notes": "First session covered pricing strategy for SEO gigs.",
			}
		).insert(ignore_permissions=True)

	# --- franchise settlement for the Lahore office ---
	lahore_office = frappe.db.get_value("Office", {"office_name": "Worcent Partner - Lahore"}, "name")
	if lahore_office and not frappe.db.exists("Franchise Settlement", {"office": lahore_office}):
		frappe.get_doc(
			{
				"doctype": "Franchise Settlement", "office": lahore_office,
				"period_start": add_days(today(), -30), "period_end": today(),
				"gross_commission_collected": 640, "status": "Settled",
			}
		).insert(ignore_permissions=True)

	# --- resolve the open dispute from the first demo contract as a split ---
	dispute = frappe.get_all("Dispute Case", filters={"status": "Open"}, fields=["name"], limit_page_length=1)
	if dispute:
		dispute_doc = frappe.get_doc("Dispute Case", dispute[0].name)
		dispute_doc.status = "Resolved-Split"
		dispute_doc.split_freelancer_percent = 60
		dispute_doc.resolution_notes = "Freelancer delivered partial work before the missed deadline; split 60/40 in their favour."
		dispute_doc.save(ignore_permissions=True)

	# --- one more support ticket, resolved this time ---
	if not frappe.db.exists("Support Ticket", {"subject": "How do I switch between freelancer and employer view?"}):
		frappe.get_doc(
			{
				"doctype": "Support Ticket", "subject": "How do I switch between freelancer and employer view?",
				"raised_by": "dual1.demo@worcent.test", "category": "Account Issue", "priority": "Low",
				"status": "Resolved", "assigned_to": "support1.demo@worcent.test",
				"description": "I have both a freelancer and employer profile, how do I switch between them?",
			}
		).insert(ignore_permissions=True)

	frappe.db.commit()
