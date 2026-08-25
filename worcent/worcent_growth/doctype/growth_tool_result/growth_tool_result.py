import frappe
from frappe.model.document import Document

from worcent.worcent_growth.tools_engine import TOOL_REGISTRY


class GrowthToolResult(Document):
	def before_insert(self):
		self.user = frappe.session.user
		self.previous_result = frappe.db.get_value(
			"Growth Tool Result",
			{"user": self.user, "tool_name": self.tool_name},
			"name",
			order_by="creation desc",
		)
		self.comparison = self.build_comparison()

	def build_comparison(self):
		if not self.previous_result:
			return "First time using this tool — nothing to compare yet."

		config = TOOL_REGISTRY.get(self.tool_name, {})
		direction = config.get("direction")
		if direction not in ("higher_better", "lower_better") or self.metric is None:
			return "Compared to your previous run — see details above."

		previous_metric = frappe.db.get_value("Growth Tool Result", self.previous_result, "metric")
		if previous_metric is None:
			return "Compared to your previous run — see details above."

		delta = round((self.metric or 0) - previous_metric, 2)
		if delta == 0:
			return "Same as your last run."

		improved = (delta > 0) if direction == "higher_better" else (delta < 0)
		trend = "Improved" if improved else "Down"
		return f"{trend} {abs(delta)} vs your last run ({previous_metric} -> {self.metric})."
