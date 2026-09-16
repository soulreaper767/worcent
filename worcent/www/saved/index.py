import frappe

sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.title = "Saved"

	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/saved"
		raise frappe.Redirect

	from worcent.worcent_marketplace.saved_item_api import list_saved_items

	context.saved_items = list_saved_items()
