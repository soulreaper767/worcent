frappe.ui.form.on("Verification Request", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status !== "Pending") return;

		frm.add_custom_button(__("Approve"), () => {
			frm.call("approve_request").then(() => frm.reload_doc());
		}).addClass("btn-primary");

		frm.add_custom_button(__("Reject"), () => {
			frappe.prompt(
				{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason") },
				(values) => frm.call("reject_request", { reason: values.reason }).then(() => frm.reload_doc()),
				__("Reject Verification Request")
			);
		});
	},
});
