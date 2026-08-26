const TOP_UP_FINANCE_ROLES = ["Finance Manager", "Worcent Admin", "System Manager"];

frappe.ui.form.on("Wallet Top Up", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status !== "Pending") return;
		if (!TOP_UP_FINANCE_ROLES.some((r) => frappe.user_roles.includes(r))) return;

		frm.add_custom_button(__("Approve"), () => {
			frappe.confirm(
				__("This credits ${0} to the wallet now. Continue?", [frm.doc.amount]),
				() => {
					frm.set_value("status", "Approved");
					frm.save();
				}
			);
		}).addClass("btn-primary");

		frm.add_custom_button(__("Reject"), () => {
			frm.set_value("status", "Rejected");
			frm.save();
		});
	},
});
