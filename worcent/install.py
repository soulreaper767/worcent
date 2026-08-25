import frappe
from frappe.utils import add_days, today

DEMO_PASSWORD = "Test@12345"


def after_install():
	configure_worcent_settings()
	seed_masters()
	seed_company_and_users()
	seed_demo_marketplace_data()
	frappe.db.set_value("Website Settings", "Website Settings", "home_page", "index")
	frappe.db.commit()


def after_migrate():
	configure_worcent_settings()
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
		settings.min_withdrawal_amount = 20
	if not settings.platform_currency:
		settings.platform_currency = "USD"
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
	for name in ["Payment Issue", "Account Issue", "Job/Contract Issue", "Technical Issue", "Other"]:
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
	create_user("arbitrator1.demo@worcent.test", "Ahmed Arbitrator", ["Dispute Arbitrator"])
	create_user("franchiseowner1.demo@worcent.test", "Farhan Franchise", ["Franchise Owner"])

	freelancer1_user = create_user("freelancer1.demo@worcent.test", "Zara Freelancer")
	freelancer2_user = create_user("freelancer2.demo@worcent.test", "Bilal Freelancer")
	employer1_user = create_user("employer1.demo@worcent.test", "Nadia Employer")
	dual_user = create_user("dual1.demo@worcent.test", "Kamran Dual")

	office_manager_user = create_user("officemanager1.demo@worcent.test", "Owais Manager")
	rep1_user = create_user("rep1.demo@worcent.test", "Rashid Rep")
	rep2_user = create_user("rep2.demo@worcent.test", "Rida Rep")

	owned_office = ensure_office("Worcent HQ - Karachi", "Owned", manager_user=office_manager_user)
	franchised_office = ensure_office(
		"Worcent Partner - Lahore", "Franchised", franchisee_name="Farhan Franchise", franchise_fee_percent=30
	)

	ensure_rep(rep1_user, owned_office, "Karachi Central")
	ensure_rep(rep2_user, franchised_office, "Lahore")

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
	ensure_employer_profile(dual_user, "Kamran Dual", "Kamran's Studio", "Design Services")

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


def ensure_freelancer_profile(user_email, headline, hourly_rate, skill_names):
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
		}
	)
	profile.insert(ignore_permissions=True)
	return profile.name


def ensure_employer_profile(user_email, contact_name, company_name, industry):
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


def ensure_proposal(job, freelancer, bid_amount, delivery_days, cover_letter):
	existing = frappe.db.get_value("Proposal", {"job_posting": job, "freelancer": freelancer}, "name")
	if existing:
		return existing
	proposal = frappe.get_doc(
		{
			"doctype": "Proposal",
			"job_posting": job,
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
