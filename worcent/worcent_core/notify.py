import frappe


def notify(user, subject, message, reference_doctype=None, reference_name=None):
	"""Thin wrapper around Frappe's own built-in Notification Log — shows up
	in the desk bell for that user and is queryable from the portal, with no
	new doctype and no email dependency (this box has no Email Account
	configured, so anything email-based would be unverifiable)."""
	if not user or user == "Guest":
		return
	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": user,
			"from_user": frappe.session.user,
			"type": "Alert",
			"title": subject,
			"email_content": f"<p>{frappe.utils.escape_html(message)}</p>",
			"document_type": reference_doctype,
			"document_name": reference_name,
		}
	).insert(ignore_permissions=True)
