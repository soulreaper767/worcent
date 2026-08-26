import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class CurrencyExchangeRate(Document):
	def validate(self):
		if self.is_new() or self.has_value_changed("rate"):
			self.last_changed_by = frappe.session.user
			self.last_changed_on = now_datetime()
