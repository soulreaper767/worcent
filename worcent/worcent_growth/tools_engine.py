"""Pure calculator functions for Worcent's free growth tools (Worcent Score,
Am I Underpaid, I Need Work). Each function takes a plain input dict and
returns a plain output dict — no DB writes here, so the same function can
serve an anonymous guest (ephemeral result) or a registered user (whose
result then gets persisted as a Growth Tool Result by the caller).

Estimates are heuristic, not real labour-market data — every tool that
quotes a number says so in its output.
"""

import frappe
from frappe.utils import flt, cint

# ---------------------------------------------------------------------------
# 1. Worcent Score
# ---------------------------------------------------------------------------

SCORE_TIERS = [
	(800, "Excellent — top-tier profile"),
	(600, "Strong — well above average"),
	(400, "Good — building solid credibility"),
	(200, "Fair — add more to stand out"),
	(0, "Just getting started"),
]


def calculate_worcent_score(inputs):
	skills = inputs.get("skills") or []
	years_experience = flt(inputs.get("years_experience"))
	certifications = cint(inputs.get("certifications"))
	portfolio_items = cint(inputs.get("portfolio_items"))
	completed_jobs = cint(inputs.get("completed_jobs"))
	rating_avg = flt(inputs.get("rating_avg"))

	breakdown = {
		"skills": min(len(skills), 10) * 15,
		"experience": min(years_experience, 15) * 20,
		"certifications": min(certifications, 10) * 15,
		"portfolio": min(portfolio_items, 10) * 10,
		"track_record": min(completed_jobs, 20) * 10,
		"rating": (min(rating_avg, 5) / 5) * 100 if rating_avg else 0,
	}
	total = round(sum(breakdown.values()))
	total = min(total, 1000)

	tier = next(label for threshold, label in SCORE_TIERS if total >= threshold)

	return {
		"total_score": total,
		"tier": tier,
		"breakdown": breakdown,
		"headline": f"Worcent Score: {total}/1000 — {tier}",
	}


# ---------------------------------------------------------------------------
# 2. Am I Underpaid?
# ---------------------------------------------------------------------------

# Deliberately broad category bands (monthly USD, mid-level baseline) —
# an estimate to prompt a conversation, not a wage survey.
JOB_CATEGORY_BANDS = {
	"tech": (1800, 4500, [
		"developer", "engineer", "programmer", "data", "devops", "frappe", "software",
		"python", "javascript", "java", "react", "node", "php", "sql", "aws", "cloud", "app", "web",
	]),
	"design": (1200, 3200, ["design", "ui", "ux", "graphic", "illustrat", "figma", "canva"]),
	"writing": (900, 2400, ["writer", "content", "copywriter", "editor", "translat", "blog"]),
	"marketing": (1100, 3000, ["marketing", "seo", "social media", "growth", "ads", "brand"]),
	"finance": (1300, 3600, ["account", "finance", "bookkeep", "audit", "tax"]),
	"admin": (700, 1800, ["assistant", "admin", "data entry", "support", "coordinator", "virtual assistant"]),
	"sales": (1000, 2800, ["sales", "business development", "bd executive"]),
	"general": (900, 2200, []),
}

COUNTRY_COST_MULTIPLIER = {
	"United States": 1.6, "United Kingdom": 1.4, "Germany": 1.3, "France": 1.25,
	"United Arab Emirates": 1.2, "Saudi Arabia": 1.1, "Pakistan": 0.4, "India": 0.45,
	"Philippines": 0.5, "Nigeria": 0.4,
}
EXPERIENCE_MULTIPLIER = [(8, 1.7), (4, 1.3), (1, 1.0), (0, 0.75)]  # (min_years, multiplier)


def _match_category(job_title):
	title = (job_title or "").lower()
	for category, (_, __, keywords) in JOB_CATEGORY_BANDS.items():
		if any(k in title for k in keywords):
			return category
	return "general"


def calculate_underpaid(inputs):
	job_title = inputs.get("job_title") or ""
	experience_years = flt(inputs.get("experience_years"))
	country = inputs.get("country") or ""
	current_salary = flt(inputs.get("current_salary"))

	category = _match_category(job_title)
	base_min, base_max, _ = JOB_CATEGORY_BANDS[category]

	exp_multiplier = next(m for min_years, m in EXPERIENCE_MULTIPLIER if experience_years >= min_years)
	country_multiplier = COUNTRY_COST_MULTIPLIER.get(country, 0.6)

	est_min = round(base_min * exp_multiplier * country_multiplier)
	est_max = round(base_max * exp_multiplier * country_multiplier)
	est_mid = (est_min + est_max) / 2

	if not current_salary:
		gap_percent = 0
		verdict = "Unknown — enter your current salary to compare"
	else:
		gap_percent = round(((est_mid - current_salary) / est_mid) * 100, 1)
		if gap_percent >= 15:
			verdict = f"You may be underpaid by ~{gap_percent}%"
		elif gap_percent <= -15:
			verdict = f"You're paid ~{abs(gap_percent)}% above the estimated range — nice"
		else:
			verdict = "Your pay looks roughly in line with the estimated range"

	return {
		"category": category,
		"estimated_min": est_min,
		"estimated_max": est_max,
		"gap_percent": gap_percent,
		"verdict": verdict,
		"headline": f"Estimated range: ${est_min:,}–${est_max:,}/mo. {verdict}.",
		"disclaimer": "A rough estimate from broad category/experience/location bands, not a wage survey — use it as a starting point for a conversation, not a guarantee.",
	}


# ---------------------------------------------------------------------------
# 3. I Need Work
# ---------------------------------------------------------------------------

QUICK_TASK_IDEAS = {
	"tech": ["Fix small bugs on Fiverr-style gigs", "Offer a 1-hour code review service", "Build a landing page for a local business"],
	"design": ["Offer logo design packages", "Redesign a small business's social media templates", "Sell Canva/Figma templates as a Gig"],
	"writing": ["Offer product description writing in bulk", "Start a paid newsletter proofreading gig", "Write LinkedIn posts for busy professionals"],
	"marketing": ["Run a free social audit as a lead magnet, then upsell", "Offer a 5-post content calendar as a starter gig", "Help a local business set up Google Business Profile"],
	"finance": ["Offer bookkeeping clean-up for small shops", "Help freelancers organize invoices/expenses", "Offer a 1-hour tax-readiness review"],
	"admin": ["Offer inbox/calendar management as a Gig", "Data entry cleanup packages", "Virtual assistant starter package (5 hrs/week)"],
	"sales": ["Cold-outreach-as-a-service for small B2B teams", "LinkedIn lead list building", "CRM cleanup for a small sales team"],
	"general": ["Offer a starter gig in your strongest skill at an intro price to build reviews", "Reach out to 10 past contacts about available work"],
}


def find_work_now(inputs):
	skill_area = inputs.get("skill_area") or ""
	location_preference = inputs.get("location_preference") or ""
	category = _match_category(skill_area)

	skill_filter = [s.strip() for s in skill_area.split(",") if s.strip()][:1]

	job_filters = {"published": 1, "status": "Open"}
	jobs = frappe.get_all(
		"Job Posting",
		filters=job_filters,
		or_filters=(
			[["title", "like", f"%{skill_filter[0]}%"]] if skill_filter else None
		),
		fields=["title", "route", "budget_type", "budget_min", "budget_max"],
		limit_page_length=5,
		order_by="creation desc",
	) if skill_filter else frappe.get_all(
		"Job Posting", filters=job_filters, fields=["title", "route", "budget_type", "budget_min", "budget_max"],
		limit_page_length=5, order_by="creation desc",
	)

	gigs = frappe.get_all(
		"Gig",
		filters={"published": 1, "status": "Active"},
		fields=["title", "route"],
		limit_page_length=5,
		order_by="creation desc",
	)

	return {
		"category": category,
		"matched_jobs": jobs,
		"matched_gigs": gigs,
		"quick_task_ideas": QUICK_TASK_IDEAS.get(category, QUICK_TASK_IDEAS["general"]),
		"headline": f"{len(jobs)} open jobs and {len(gigs)} gigs on Worcent right now, plus {len(QUICK_TASK_IDEAS.get(category, []))} things you can start today.",
	}


# ---------------------------------------------------------------------------
# 4. CV Score (Job Description -> CV Match %)
# ---------------------------------------------------------------------------

STOPWORDS = set(
	"the a an and or for with to of in on at by is are be was were will would should "
	"could can may might must this that these those you your we our i it its as from "
	"into about over under between within without more most other than then also into "
	"if not no yes has have had do does did but so such per via etc using use used "
	"job role position looking seeking candidate ideal responsibilities requirements "
	"required years experience skills ability strong good excellent working work team".split()
)

# A curated list of common professional skill/tool phrases — matched as whole
# phrases first (so "project management" counts as one skill, not two noise
# words), then remaining single significant words are matched individually.
KNOWN_SKILL_PHRASES = [
	"project management", "data analysis", "content writing", "social media", "customer service",
	"machine learning", "graphic design", "search engine optimization", "email marketing",
	"business development", "financial modeling", "public speaking", "team leadership",
	"time management", "problem solving", "attention to detail",
]


def _tokenize(text):
	text = (text or "").lower()
	words = "".join(c if c.isalnum() or c.isspace() else " " for c in text).split()
	return [w for w in words if len(w) >= 3 and w not in STOPWORDS]


def calculate_cv_score(inputs):
	cv_text = inputs.get("cv_text") or ""
	jd_text = inputs.get("job_description") or ""
	cv_lower = cv_text.lower()

	found_phrases = [p for p in KNOWN_SKILL_PHRASES if p in jd_text.lower()]
	remaining_jd = jd_text.lower()
	for p in found_phrases:
		remaining_jd = remaining_jd.replace(p, " ")

	jd_words = sorted(set(_tokenize(remaining_jd)))
	jd_keywords = found_phrases + jd_words

	if not jd_keywords:
		return {
			"match_percent": 0,
			"matched_keywords": [],
			"missing_keywords": [],
			"headline": "Paste a job description to check your CV against it.",
		}

	matched = [k for k in jd_keywords if k in cv_lower]
	missing = [k for k in jd_keywords if k not in cv_lower]
	match_percent = round(len(matched) / len(jd_keywords) * 100)

	return {
		"match_percent": match_percent,
		"matched_keywords": matched[:20],
		"missing_keywords": missing[:15],
		"headline": f"JOB MATCH: {match_percent}%",
	}


# ---------------------------------------------------------------------------
# 5. What Job Should I Do? (career quiz)
# ---------------------------------------------------------------------------

CAREER_QUIZ_QUESTIONS = [
	{"id": "tech", "text": "I enjoy working with computers, software or technical tools."},
	{"id": "people", "text": "I'm energized by talking to and persuading people."},
	{"id": "creative", "text": "I like visual/creative work — design, writing, storytelling."},
	{"id": "numbers", "text": "I'm comfortable with numbers, spreadsheets and analysis."},
	{"id": "structure", "text": "I prefer clear processes and detail-oriented work over ambiguity."},
	{"id": "helping", "text": "I get satisfaction from directly helping/supporting other people."},
	{"id": "leading", "text": "I like taking ownership and directing a project or team."},
	{"id": "remote", "text": "I want work I can do fully remote, on my own schedule."},
]

# question_id -> {career: weight (-2..+2)}
CAREER_WEIGHTS = {
	"tech": {"Software Developer": 2, "Data Analyst": 2, "Product Manager": 1, "UI/UX Designer": 1, "IT Support Specialist": 2},
	"people": {"Sales Executive": 2, "Product Manager": 1, "HR Coordinator": 2, "Customer Support Specialist": 1, "Digital Marketer": 1},
	"creative": {"UI/UX Designer": 2, "Content Writer": 2, "Digital Marketer": 1},
	"numbers": {"Data Analyst": 2, "Accountant": 2, "Financial Analyst": 2, "Software Developer": 1},
	"structure": {"Accountant": 2, "Financial Analyst": 1, "IT Support Specialist": 1, "Data Analyst": 1},
	"helping": {"Customer Support Specialist": 2, "HR Coordinator": 2, "Virtual Assistant": 1},
	"leading": {"Product Manager": 2, "Sales Executive": 1, "HR Coordinator": 1},
	"remote": {"Content Writer": 1, "Virtual Assistant": 1, "Software Developer": 1, "Data Analyst": 1, "Digital Marketer": 1},
}

ALL_CAREERS = sorted({c for weights in CAREER_WEIGHTS.values() for c in weights})


def calculate_career_match(inputs):
	answers = inputs.get("answers") or {}
	scores = {c: 0 for c in ALL_CAREERS}
	max_possible = {c: 0 for c in ALL_CAREERS}

	for q in CAREER_QUIZ_QUESTIONS:
		raw = flt(answers.get(q["id"], 3))
		delta = raw - 3
		for career, weight in CAREER_WEIGHTS.get(q["id"], {}).items():
			scores[career] += delta * weight
			max_possible[career] += 2 * abs(weight)

	results = []
	for career in ALL_CAREERS:
		mx = max_possible[career] or 1
		pct = round(((scores[career] + mx) / (2 * mx)) * 100)
		results.append({"career": career, "match_percent": max(0, min(100, pct))})

	results.sort(key=lambda r: r["match_percent"], reverse=True)
	top3 = results[:3]

	return {
		"top_matches": top3,
		"all_matches": results,
		"headline": f"Top match: {top3[0]['career']} ({top3[0]['match_percent']}%)" if top3 else "Answer the questions to see your matches.",
	}


# ---------------------------------------------------------------------------
# 6. 1-Minute Job Readiness Test
# ---------------------------------------------------------------------------

JOB_READINESS_BANKS = {
	"Data Analyst": [
		("Excel/Google Sheets (formulas, pivot tables)", "Excel pivot tables & formulas"),
		("SQL basics (SELECT, JOIN, GROUP BY)", "SQL fundamentals"),
		("Data visualization (charts/dashboards)", "Data visualization (e.g. Power BI/Tableau)"),
		("Basic statistics (mean, median, correlation)", "Basic statistics"),
		("Cleaning messy/real-world data", "Data cleaning techniques"),
		("Python or R for data (pandas etc.)", "Python for data analysis"),
		("Presenting findings to non-technical people", "Data storytelling / presentation"),
		("Working with large datasets", "Working with large datasets"),
		("Understanding business KPIs", "Business KPI fundamentals"),
		("A portfolio project you can show", "Building a portfolio project"),
	],
	"Software Developer": [
		("Comfortable with at least one programming language", "Pick and commit to one language"),
		("Version control (Git)", "Git fundamentals"),
		("Building and debugging small projects end-to-end", "Build a complete small project"),
		("Understanding of APIs / how frontend-backend talk", "API fundamentals"),
		("Basic database knowledge (SQL/NoSQL)", "Database basics"),
		("Writing readable, maintainable code", "Clean code practices"),
		("Testing your own code", "Basic testing practices"),
		("Deploying a project so others can use it", "Deployment basics"),
		("Reading other people's code/docs", "Reading documentation/codebases"),
		("A portfolio/GitHub you can show", "Building a public portfolio"),
	],
	"Accountant": [
		("Understanding debits/credits and the accounting equation", "Accounting fundamentals"),
		("Comfortable with Excel/Sheets for finance", "Excel for finance"),
		("Basic knowledge of financial statements", "Reading financial statements"),
		("Familiar with at least one accounting software", "Accounting software (QuickBooks/Xero/ERPNext)"),
		("Understanding of tax basics in your market", "Tax fundamentals"),
		("Bank reconciliation experience", "Bank reconciliation practice"),
		("Invoicing/accounts receivable & payable basics", "AR/AP fundamentals"),
		("Attention to detail with numbers", "Detail-checking discipline"),
		("Basic budgeting/forecasting", "Budgeting & forecasting basics"),
		("A sample of bookkeeping work you can show", "Building a sample bookkeeping case"),
	],
	"Graphic Designer": [
		("Comfortable with a design tool (Figma/Canva/Adobe)", "Pick one design tool and go deep"),
		("Understanding of typography basics", "Typography fundamentals"),
		("Understanding of color theory", "Color theory basics"),
		("Can design a simple logo", "Logo design practice"),
		("Can design social media graphics", "Social media graphics practice"),
		("Understanding of layout/composition", "Layout & composition basics"),
		("Comfortable taking client feedback/revisions", "Handling client revisions"),
		("Basic branding concepts", "Branding fundamentals"),
		("Exporting files correctly for different uses", "File formats/export basics"),
		("A portfolio you can show", "Building a design portfolio"),
	],
	"Digital Marketer": [
		("Understanding of SEO basics", "SEO fundamentals"),
		("Running/understanding paid ads (Meta/Google)", "Paid ads fundamentals"),
		("Content calendar planning", "Content planning"),
		("Basic analytics reading (traffic, conversions)", "Analytics fundamentals"),
		("Email marketing basics", "Email marketing fundamentals"),
		("Social media platform know-how", "Social media strategy"),
		("Copywriting for ads/posts", "Copywriting practice"),
		("Understanding target audience/personas", "Audience research"),
		("Basic design skills for marketing assets", "Basic design for marketing"),
		("A campaign example you can show", "Building a sample campaign"),
	],
	"Virtual Assistant / Admin Support": [
		("Comfortable with email/calendar management", "Inbox & calendar management"),
		("Comfortable with spreadsheets", "Spreadsheet basics"),
		("Good written communication", "Written communication practice"),
		("Familiar with common tools (Slack, Notion, Zoom)", "Common productivity tools"),
		("Data entry accuracy", "Data entry practice"),
		("Basic scheduling/coordination", "Scheduling & coordination"),
		("Confidentiality/discretion with sensitive info", "Confidentiality practices"),
		("Comfortable multitasking across small tasks", "Multitasking practice"),
		("Basic research skills", "Research skills"),
		("A sample task log/portfolio you can show", "Building a sample work log"),
	],
	"Customer Support Specialist": [
		("Clear written communication", "Written communication practice"),
		("Staying calm/patient with frustrated customers", "De-escalation practice"),
		("Familiar with helpdesk tools (Zendesk/Freshdesk etc.)", "Helpdesk tool familiarity"),
		("Understanding of SLAs/response times", "SLA fundamentals"),
		("Basic troubleshooting mindset", "Troubleshooting practice"),
		("Comfortable following scripts/knowledge bases", "Knowledge base usage"),
		("Empathy and active listening", "Active listening practice"),
		("Multitasking across tickets/chats", "Multitasking practice"),
		("Basic reporting on ticket trends", "Basic reporting"),
		("A sample of your writing tone you can show", "Building sample response templates"),
	],
}


def calculate_job_readiness(inputs):
	career = inputs.get("career")
	answers = inputs.get("answers") or {}
	bank = JOB_READINESS_BANKS.get(career)
	if not bank:
		frappe.throw(f"Unknown career track: {career}")

	yes_count = 0
	gaps = []
	for idx, (question, learn) in enumerate(bank):
		if answers.get(str(idx)) or answers.get(idx):
			yes_count += 1
		else:
			gaps.append(learn)

	score = round((yes_count / len(bank)) * 100)
	return {
		"career": career,
		"score": score,
		"gaps": gaps[:3],
		"headline": f"{score}/100 ready for {career}." + (" You're close." if score >= 70 else " Keep building."),
	}


TOOL_REGISTRY = {
	"Worcent Score": {
		"fn": calculate_worcent_score,
		"metric_key": "total_score",
		"direction": "higher_better",
	},
	"Am I Underpaid": {
		"fn": calculate_underpaid,
		"metric_key": "gap_percent",
		"direction": "lower_better",
	},
	"I Need Work": {
		"fn": find_work_now,
		"metric_key": None,
		"direction": "neutral",
	},
	"CV Score": {
		"fn": calculate_cv_score,
		"metric_key": "match_percent",
		"direction": "higher_better",
	},
	"Career Match": {
		"fn": calculate_career_match,
		"metric_key": None,
		"direction": "neutral",
	},
	"Job Readiness": {
		"fn": calculate_job_readiness,
		"metric_key": "score",
		"direction": "higher_better",
	},
}


def run_tool(tool_name, inputs):
	config = TOOL_REGISTRY.get(tool_name)
	if not config:
		frappe.throw(f"Unknown tool: {tool_name}")
	output = config["fn"](inputs)
	metric = output.get(config["metric_key"]) if config["metric_key"] else None
	return output, metric
