frappe.ui.form.on("Physical Verification Appointment", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status !== "Scheduled") return;

		frm.add_custom_button(__("Mark Completed"), () => {
			frappe.prompt(
				{ fieldname: "result_notes", fieldtype: "Small Text", label: __("Result Notes") },
				(values) => frm.call("mark_completed", { result_notes: values.result_notes }).then(() => frm.reload_doc()),
				__("Complete Verification")
			);
		}).addClass("btn-primary");

		frm.add_custom_button(__("Mark Failed"), () => {
			frm.set_value("status", "Failed");
			frm.save();
		});
	},
});
