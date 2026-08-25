import frappe


def ensure_wallet(party_type, party_name):
	"""Create the Wallet for a Freelancer/Employer Profile if it doesn't exist yet."""
	if frappe.db.exists("Wallet", {"party_type": party_type, "party": party_name}):
		return frappe.db.get_value("Wallet", {"party_type": party_type, "party": party_name}, "name")

	wallet = frappe.get_doc(
		{
			"doctype": "Wallet",
			"party_type": party_type,
			"party": party_name,
			"balance": 0,
			"held_in_escrow": 0,
			"total_withdrawn": 0,
		}
	)
	wallet.insert(ignore_permissions=True)
	return wallet.name


def get_wallet(party_type, party_name):
	name = frappe.db.get_value("Wallet", {"party_type": party_type, "party": party_name}, "name")
	return frappe.get_doc("Wallet", name) if name else None
