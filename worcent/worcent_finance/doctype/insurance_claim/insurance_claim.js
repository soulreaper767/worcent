const CLAIM_PROCESSING_ROLES = ["Finance Manager", "Accounts Manager", "Worcent Admin", "System Manager"];

frappe.ui.form.on("Insurance Claim", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (!CLAIM_PROCESSING_ROLES.some((r) => frappe.user_roles.includes(r))) return;

		if (frm.doc.status === "Submitted") {
			frm.add_custom_button(__("Mark Under Review"), () => {
				frm.call("mark_under_review").then(() => frm.reload_doc());
			});
		}

		if (["Submitted", "Under Review"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Approve & Pay"), () => {
				frappe.confirm(
					__("This credits ${0} to the freelancer's wallet now. Continue?", [frm.doc.amount_claimed]),
					() => frm.call("approve_and_pay").then(() => frm.reload_doc())
				);
			}).addClass("btn-primary");

			frm.add_custom_button(__("Reject"), () => {
				frappe.prompt(
					{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason") },
					(values) => frm.call("reject", { reason: values.reason }).then(() => frm.reload_doc()),
					__("Reject Claim")
				);
			});
		}
	},
});
