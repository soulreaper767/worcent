import frappe
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series


class Milestone(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	@frappe.whitelist()
	def fund(self):
		from worcent.worcent_finance.escrow_engine import fund_milestone

		fund_milestone(self.name)
		self.reload()

	@frappe.whitelist()
	def approve_and_release(self):
		from worcent.worcent_finance.escrow_engine import release_milestone

		result = release_milestone(self.name)
		self.reload()
		return result

	@frappe.whitelist()
	def refund(self):
		from worcent.worcent_finance.escrow_engine import refund_milestone

		refund_milestone(self.name)
		self.reload()
