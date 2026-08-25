frappe.ui.form.on("Withdrawal Request", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.status === "Pending") {
			frm.add_custom_button(__("Approve"), () => {
				frm.call("approve_request").then(() => frm.reload_doc());
			}).addClass("btn-primary");

			frm.add_custom_button(__("Reject"), () => {
				frappe.prompt(
					{ fieldname: "reason", fieldtype: "Small Text", label: __("Rejection Reason") },
					(values) => frm.call("reject_request", { reason: values.reason }).then(() => frm.reload_doc()),
					__("Reject Withdrawal Request")
				);
			});
		}

		if (frm.doc.status === "Approved") {
			frm.add_custom_button(__("Mark Paid"), () => {
				frappe.confirm(
					__("Confirm the transfer has actually been sent to the payout account before marking this Paid — this debits the wallet immediately."),
					() => frm.call("mark_paid").then(() => frm.reload_doc())
				);
			}).addClass("btn-primary");

			frm.add_custom_button(__("Reject"), () => {
				frappe.prompt(
					{ fieldname: "reason", fieldtype: "Small Text", label: __("Rejection Reason") },
					(values) => frm.call("reject_request", { reason: values.reason }).then(() => frm.reload_doc()),
					__("Reject Withdrawal Request")
				);
			});
		}
	},
});
