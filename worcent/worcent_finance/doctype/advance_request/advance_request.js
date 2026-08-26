const ADVANCE_PROCESSING_ROLES = ["Finance Manager", "Worcent Admin", "System Manager"];

frappe.ui.form.on("Advance Request", {
	refresh(frm) {
		if (frm.is_new()) return;

		const is_finance = ADVANCE_PROCESSING_ROLES.some((r) => frappe.user_roles.includes(r));

		if (is_finance && frm.doc.status === "Requested") {
			frm.add_custom_button(__("Approve & Disburse"), () => {
				frappe.confirm(
					__("This credits the freelancer's wallet with ${0} now and builds a repayment schedule. Continue?", [frm.doc.amount_requested]),
					() => frm.call("approve_and_disburse").then(() => frm.reload_doc())
				);
			}).addClass("btn-primary");

			frm.add_custom_button(__("Reject"), () => {
				frm.call("reject").then(() => frm.reload_doc());
			});
		}

		if (frm.doc.status === "Repaying" && (frm.doc.repayment_schedule || []).some((r) => r.status === "Pending")) {
			frm.add_custom_button(__("Pay Next Installment"), () => {
				const next = frm.doc.repayment_schedule.find((r) => r.status === "Pending");
				frappe.confirm(
					__("This debits ${0} from the freelancer's wallet toward this advance. Continue?", [next.amount]),
					() => frm.call("pay_installment", { row_name: next.name }).then(() => frm.reload_doc())
				);
			}).addClass("btn-primary");
		}
	},
});
