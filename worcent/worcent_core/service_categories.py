"""The full Skill Category tree: broad service groups plus their specific,
selectable sub-categories. Shared by the fresh-install seed (install.py) and
the migration patch for already-installed sites (patches/v1_0/
seed_service_categories.py) so both stay in sync from one source of truth.
"""

import frappe

ROOT = "All Categories"

# Existing flat categories become groups under the root, each gaining specific,
# selectable sub-categories. New groups: Regulated Services (license-gated) and Sports.
CATEGORIES = {
	"Web Development": {
		"children": [
			"Frontend Development",
			"Backend Development",
			"Full-Stack Development",
			"Mobile App Development",
			"E-commerce Development",
			"WordPress Development",
			"DevOps & Cloud Infrastructure",
			"QA & Software Testing",
			"API Development & Integration",
			"Blockchain & Web3 Development",
			"Game Development",
		],
	},
	"Design & Creative": {
		"children": [
			"Graphic Design",
			"UI/UX Design",
			"Logo & Brand Identity",
			"Video Editing",
			"Animation & Motion Graphics",
			"Illustration",
			"Photography",
			"Audio & Music Production",
			"3D Modelling & CAD",
		],
	},
	"Writing & Translation": {
		"children": [
			"Content Writing",
			"Copywriting",
			"Technical Writing",
			"Translation & Localization",
			"Proofreading & Editing",
			"Ghostwriting",
			"Resume & Cover Letter Writing",
			"Scriptwriting & Screenwriting",
		],
	},
	"Sales & Marketing": {
		"children": [
			"Digital Marketing Strategy",
			"Search Engine Optimization (SEO)",
			"Social Media Marketing",
			"Email Marketing",
			"Lead Generation & Sales",
			"Market Research & Analysis",
			"Public Relations",
			"Affiliate & Influencer Marketing",
			"Paid Advertising (PPC)",
		],
	},
	"Admin Support": {
		"children": [
			"Virtual Assistance",
			"Data Entry",
			"Customer Service & Support",
			"Project Management",
			"Transcription",
			"General Bookkeeping (Non-Statutory)",
			"Scheduling & Calendar Management",
			"Research & Data Collection",
		],
	},
	"Regulated Services": {
		"requires_license": 1,
		"children": {
			"Audit & Assurance Services": (
				"Valid Chartered Accountant / CPA license with statutory audit signing "
				"authority (e.g. ICAP, ACCA, AICPA)."
			),
			"Statutory Tax & Accounting Practice": (
				"Recognized CA/CPA/ACCA membership or licensed tax practitioner registration."
			),
			"Legal Services & Advocacy": (
				"Active Bar Council / Law Society enrollment as a practicing advocate or attorney."
			),
			"Notary & Conveyancing": "Government-issued Notary Public commission.",
			"Medical & Clinical Practice": (
				"Valid medical license/registration from the relevant Medical Council "
				"(e.g. PMDC, GMC, state medical board)."
			),
			"Dental Services": "Valid dental council registration/license.",
			"Pharmacy & Pharmaceutical Dispensing": (
				"Registered Pharmacist license from the relevant Pharmacy Council."
			),
			"Nursing & Allied Health": (
				"Valid nursing council registration or allied-health practicing license."
			),
			"Mental Health Counseling & Psychology": (
				"Licensed psychologist/counselor credential from the relevant psychological "
				"association or health authority."
			),
			"Veterinary Services": "Registered Veterinary Council license.",
			"Engineering Services (Civil/Structural/Electrical)": (
				"Licensed Professional Engineer (PE) or equivalent engineering council "
				"registration (e.g. PEC)."
			),
			"Architecture Services": (
				"Registered Architect license from the relevant Architects' council/board."
			),
			"Financial & Investment Advisory": (
				"Licensed financial advisor / securities registration (e.g. SEC, SECP, FCA)."
			),
			"Insurance Brokerage & Underwriting": (
				"Valid insurance broker/agent license from the relevant regulator."
			),
			"Real Estate Brokerage": "Licensed real estate broker/agent registration.",
			"Customs & Freight Forwarding Agency": "Licensed customs clearing agent registration.",
			"Aviation & Marine Piloting": (
				"Valid pilot license or master mariner certification from the relevant "
				"aviation/maritime authority."
			),
		},
	},
	"Sports": {
		"children": [
			"Football (Soccer)",
			"Cricket",
			"Basketball",
			"Tennis",
			"Badminton",
			"Table Tennis",
			"Volleyball",
			"Handball",
			"Field Hockey",
			"Ice Hockey",
			"Rugby",
			"American Football",
			"Baseball",
			"Softball",
			"Golf",
			"Boxing",
			"Mixed Martial Arts",
			"Wrestling",
			"Judo",
			"Karate",
			"Taekwondo",
			"Fencing",
			"Swimming",
			"Diving",
			"Water Polo",
			"Athletics (Track & Field)",
			"Marathon & Long-Distance Running",
			"Cycling",
			"Gymnastics",
			"Weightlifting & Powerlifting",
			"CrossFit & Functional Fitness",
			"Yoga & Personal Training",
			"Squash",
			"Snooker & Billiards",
			"Archery",
			"Shooting Sports",
			"Equestrian Sports",
			"Sailing & Rowing",
			"Surfing",
			"Skiing & Snowboarding",
			"Skating (Ice/Roller)",
			"Triathlon",
			"Chess (Competitive)",
			"Esports & Competitive Gaming",
		],
	},
}


def seed_service_categories():
	_upsert(ROOT, parent=None, is_group=1)

	for top_level, meta in CATEGORIES.items():
		requires_license = meta.get("requires_license", 0)
		_upsert(top_level, parent=ROOT, is_group=1, requires_license=requires_license)

		children = meta["children"]
		if isinstance(children, dict):
			for child_name, guidance in children.items():
				_upsert(
					child_name,
					parent=top_level,
					is_group=0,
					requires_license=requires_license,
					license_guidance=guidance,
				)
		else:
			for child_name in children:
				_upsert(child_name, parent=top_level, is_group=0, requires_license=requires_license)


def _upsert(name, parent, is_group, requires_license=0, license_guidance=None):
	if frappe.db.exists("Skill Category", name):
		doc = frappe.get_doc("Skill Category", name)
	else:
		doc = frappe.new_doc("Skill Category")
		doc.category_name = name

	doc.parent_skill_category = parent
	doc.is_group = is_group
	doc.requires_license = requires_license
	if license_guidance:
		doc.license_guidance = license_guidance

	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)


def category_and_descendants(category_name):
	"""A visitor picking a group category (e.g. "Sports") to filter/browse by
	should still match content tagged to its specific leaf children (e.g.
	"Cricket") -- Skill Category became a tree, but Gig/Job Posting/Skill
	still store a single exact category name, so filtering needs to expand
	a group into itself + every descendant rather than exact-match alone."""
	from frappe.utils.nestedset import get_descendants_of

	if not category_name or not frappe.db.exists("Skill Category", category_name):
		return [category_name] if category_name else []
	descendants = get_descendants_of("Skill Category", category_name, ignore_permissions=True)
	return [category_name] + list(descendants)
