import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import add_months, flt, today

PROCESSING_ROLES = {"Finance Manager", "Worcent Admin", "System Manager"}
INSTALLMENTS = 3


class AdvanceRequest(Document):
	def autoname(self):
		set_name_by_naming_series(self)

	def validate(self):
		if self.is_new() and frappe.session.user != "Administrator" and not PROCESSING_ROLES.intersection(frappe.get_roles()):
			owner = frappe.db.get_value("Freelancer Profile", self.freelancer, "user")
			if owner != frappe.session.user:
				frappe.throw(_("You can only request an advance for yourself."))

	def _require_processing_role(self):
		if not PROCESSING_ROLES.intersection(frappe.get_roles()):
			frappe.throw(_("Only Finance can process advance requests."))

	@frappe.whitelist()
	def approve_and_disburse(self):
		if self.status != "Requested":
			frappe.throw(_("Only a Requested advance can be approved."))
		self._require_processing_role()

		self.status = "Disbursed"
		self.build_repayment_schedule()
		self.save(ignore_permissions=True)
		self.disburse()

	@frappe.whitelist()
	def reject(self, reason=None):
		if self.status != "Requested":
			frappe.throw(_("Only a Requested advance can be rejected."))
		self._require_processing_role()
		self.status = "Rejected"
		self.save(ignore_permissions=True)

	def build_repayment_schedule(self):
		total_due = flt(self.amount_requested) * (1 + flt(self.interest_rate) / 100)
		installment = round(total_due / INSTALLMENTS, 2)
		self.repayment_schedule = []
		remaining = total_due
		for i in range(1, INSTALLMENTS + 1):
			amount = installment if i < INSTALLMENTS else round(remaining, 2)
			remaining -= amount
			self.append(
				"repayment_schedule",
				{"due_date": add_months(today(), i), "amount": amount, "status": "Pending"},
			)

	def disburse(self):
		from worcent.worcent_core.wallet_utils import ensure_wallet

		wallet_name = ensure_wallet("Freelancer Profile", self.freelancer)
		wallet = frappe.get_doc("Wallet", wallet_name)
		wallet.balance = flt(wallet.balance) + flt(self.amount_requested)
		wallet.save(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "Wallet Transaction",
				"wallet": wallet.name,
				"transaction_type": "Advance",
				"direction": "Credit",
				"amount": self.amount_requested,
				"balance_after": wallet.balance,
				"reference_doctype": "Advance Request",
				"reference_name": self.name,
			}
		).insert(ignore_permissions=True)
		self.db_set("status", "Repaying")

	@frappe.whitelist()
	def pay_installment(self, row_name):
		if self.status != "Repaying":
			frappe.throw(_("This advance isn't in a repayable state."))
		if frappe.session.user != "Administrator" and not PROCESSING_ROLES.intersection(frappe.get_roles()):
			owner = frappe.db.get_value("Freelancer Profile", self.freelancer, "user")
			if owner != frappe.session.user:
				frappe.throw(_("Only the freelancer who took this advance can repay it."))

		row = next((r for r in self.repayment_schedule if r.name == row_name), None)
		if not row:
			frappe.throw(_("That installment doesn't exist on this advance."))
		if row.status == "Paid":
			frappe.throw(_("That installment is already paid."))

		from worcent.worcent_core.wallet_utils import ensure_wallet

		wallet_name = ensure_wallet("Freelancer Profile", self.freelancer)
		wallet = frappe.get_doc("Wallet", wallet_name)
		if flt(wallet.balance) < flt(row.amount):
			frappe.throw(_("Insufficient wallet balance to pay this installment."))

		wallet.balance = flt(wallet.balance) - flt(row.amount)
		wallet.save(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "Wallet Transaction",
				"wallet": wallet.name,
				"transaction_type": "Advance Repayment",
				"direction": "Debit",
				"amount": row.amount,
				"balance_after": wallet.balance,
				"reference_doctype": "Advance Request",
				"reference_name": self.name,
			}
		).insert(ignore_permissions=True)

		row.status = "Paid"
		self.save(ignore_permissions=True)

		if all(r.status == "Paid" for r in self.repayment_schedule):
			self.db_set("status", "Closed")
