import frappe
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import flt


class FranchiseSettlement(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		fee_percent = flt(frappe.db.get_value("Office", self.office, "franchise_fee_percent"))
		self.platform_share = flt(self.gross_commission_collected) * fee_percent / 100
		self.franchise_share = flt(self.gross_commission_collected) - self.platform_share
