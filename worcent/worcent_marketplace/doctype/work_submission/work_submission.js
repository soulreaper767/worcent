frappe.ui.form.on("Work Submission", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.status === "Submitted") {
			frm.add_custom_button(__("Approve"), () => {
				frappe.confirm(
					__("This marks the work approved. To actually release the escrowed funds, use \"Approve & Release\" on the Milestone itself."),
					() => frm.call("approve").then(() => frm.reload_doc())
				);
			}).addClass("btn-primary");

			frm.add_custom_button(__("Reject"), () => {
				frappe.prompt(
					{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason") },
					(values) => frm.call("reject", { reason: values.reason }).then(() => frm.reload_doc()),
					__("Reject Submission")
				);
			});
		}
	},
});
