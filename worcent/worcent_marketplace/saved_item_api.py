import frappe
from frappe import _

VALID_DOCTYPES = {"Gig", "Job Posting", "Freelancer Profile", "Agency"}


@frappe.whitelist()
def toggle_saved_item(item_doctype, item_name):
	if item_doctype not in VALID_DOCTYPES:
		frappe.throw(_("Can't save that kind of item."))
	if not frappe.db.exists(item_doctype, item_name):
		frappe.throw(_("Not found."))

	existing = frappe.db.exists(
		"Saved Item", {"user": frappe.session.user, "item_doctype": item_doctype, "item_name": item_name}
	)
	if existing:
		frappe.delete_doc("Saved Item", existing, ignore_permissions=True)
		return {"saved": False}

	frappe.get_doc(
		{
			"doctype": "Saved Item",
			"user": frappe.session.user,
			"item_doctype": item_doctype,
			"item_name": item_name,
		}
	).insert(ignore_permissions=True)
	return {"saved": True}


@frappe.whitelist()
def list_saved_items():
	rows = frappe.get_all(
		"Saved Item",
		filters={"user": frappe.session.user},
		fields=["name", "item_doctype", "item_name", "creation"],
		order_by="creation desc",
	)
	title_field = {"Gig": "title", "Job Posting": "title", "Freelancer Profile": "display_name", "Agency": "agency_name"}
	route_field = "route"
	for row in rows:
		info = frappe.db.get_value(row.item_doctype, row.item_name, [title_field[row.item_doctype], route_field], as_dict=True)
		row["title"] = info.get(title_field[row.item_doctype]) if info else row.item_name
		row["route"] = info.get(route_field) if info else None
	return rows
