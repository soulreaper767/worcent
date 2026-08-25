import frappe

from worcent.worcent_growth.tools_engine import CAREER_QUIZ_QUESTIONS

sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.body_class = "worcent-tools"
	context.questions = CAREER_QUIZ_QUESTIONS
