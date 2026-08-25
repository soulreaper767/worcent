frappe.ui.form.on("Rank Application", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (["Pending", "Appeal Pending"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Approve"), () => {
				frappe.prompt(
					{ fieldname: "review_notes", fieldtype: "Small Text", label: __("Review Notes") },
					(values) => frm.call("approve", { review_notes: values.review_notes }).then(() => frm.reload_doc()),
					__("Approve Rank Application")
				);
			}).addClass("btn-primary");

			frm.add_custom_button(__("Reject"), () => {
				frappe.prompt(
					{ fieldname: "review_notes", fieldtype: "Small Text", label: __("Review Notes") },
					(values) => frm.call("reject", { review_notes: values.review_notes }).then(() => frm.reload_doc()),
					__("Reject Rank Application")
				);
			});
		}

		if (frm.doc.status === "Rejected" && !frm.doc.appeal_used) {
			frm.add_custom_button(__("Appeal (costs $5)"), () => {
				frappe.confirm(
					__("Appealing this decision costs $5, debited from your wallet immediately, and can only be done once. Continue?"),
					() => frm.call("appeal").then(() => frm.reload_doc())
				);
			});
		}
	},
});
