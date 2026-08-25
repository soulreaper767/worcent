frappe.ui.form.on("Dispute Case", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (["Resolved-Freelancer", "Resolved-Employer", "Resolved-Split"].includes(frm.doc.status)) return;

		frm.add_custom_button(__("Resolve Dispute"), () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Resolve Dispute"),
				fields: [
					{
						fieldname: "resolution",
						fieldtype: "Select",
						label: __("Resolution"),
						options: "Resolved-Freelancer\nResolved-Employer\nResolved-Split",
						reqd: 1,
					},
					{
						fieldname: "split_freelancer_percent",
						fieldtype: "Percent",
						label: __("Freelancer Share %"),
						depends_on: "eval:doc.resolution=='Resolved-Split'",
					},
					{
						fieldname: "resolution_notes",
						fieldtype: "Small Text",
						label: __("Resolution Notes"),
					},
				],
				primary_action_label: __("Resolve"),
				primary_action: (values) => {
					frm.call("resolve_case", values).then(() => {
						dialog.hide();
						frm.reload_doc();
					});
				},
			});
			dialog.show();
		}).addClass("btn-primary");
	},
});
