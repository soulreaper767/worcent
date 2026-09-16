from frappe.utils.nestedset import NestedSet


class SkillCategory(NestedSet):
	nsm_parent_field = "parent_skill_category"
