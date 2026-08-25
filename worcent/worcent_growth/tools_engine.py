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
}


def run_tool(tool_name, inputs):
	config = TOOL_REGISTRY.get(tool_name)
	if not config:
		frappe.throw(f"Unknown tool: {tool_name}")
	output = config["fn"](inputs)
	metric = output.get(config["metric_key"]) if config["metric_key"] else None
	return output, metric
