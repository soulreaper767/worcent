frappe.ui.form.on("Support Ticket", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frappe.user_roles.includes("Support Agent") || frappe.user_roles.includes("Worcent Admin") || frappe.user_roles.includes("System Manager")) {
			frm.add_custom_button(__("Reassign"), () => {
				frappe.prompt(
					{
						fieldname: "to_user",
						fieldtype: "Link",
						options: "User",
						label: __("Reassign To (leave blank for auto-pick)"),
						get_query: () => ({
							query: "frappe.core.doctype.user.user.user_query",
							filters: { role: "Support Agent" },
						}),
					},
					(values) => frm.call("reassign", { to_user: values.to_user }).then(() => frm.reload_doc()),
					__("Reassign Ticket")
				);
			});
		}
	},
});
