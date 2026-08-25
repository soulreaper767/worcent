import re

import frappe


def slugify(text):
	text = re.sub(r"[^a-zA-Z0-9\s-]", "", text or "").strip().lower()
	return re.sub(r"[\s-]+", "-", text)


def unique_route(doctype, prefix, title, exclude_name=None):
	base = f"{prefix}/{slugify(title)}"
	route = base
	i = 1
	while True:
		filters = {"route": route}
		if exclude_name:
			filters["name"] = ["!=", exclude_name]
		if not frappe.db.exists(doctype, filters):
			return route
		i += 1
		route = f"{base}-{i}"
