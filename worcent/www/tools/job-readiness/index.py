import frappe

from worcent.worcent_growth.tools_engine import JOB_READINESS_BANKS

sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.body_class = "worcent-tools"
	context.careers = list(JOB_READINESS_BANKS.keys())
	banks = {career: [q for q, _ in items] for career, items in JOB_READINESS_BANKS.items()}
	context.banks_json = frappe.as_json(banks)
