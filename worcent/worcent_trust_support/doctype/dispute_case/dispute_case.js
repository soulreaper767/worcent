const RESOLVED_STATUSES = ["Resolved-Freelancer", "Resolved-Employer", "Resolved-Split"];

frappe.ui.form.on("Dispute Case", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (!RESOLVED_STATUSES.includes(frm.doc.status)) {
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
			return;
		}

		if (frm.doc.appeal_status === "Not Appealed") {
			frm.add_custom_button(__("Appeal This Resolution"), () => {
				frappe.prompt(
					{ fieldname: "appeal_notes", fieldtype: "Small Text", label: __("Why are you appealing?"), reqd: 1 },
					(values) => frm.call("appeal", { appeal_notes: values.appeal_notes }).then(() => frm.reload_doc()),
					__("Appeal Resolution")
				);
			});
		} else if (frm.doc.appeal_status === "Appeal Pending") {
			frm.add_custom_button(__("Uphold Appeal"), () => {
				frappe.prompt(
					{ fieldname: "notes", fieldtype: "Small Text", label: __("Notes") },
					(values) => frm.call("resolve_appeal", { upheld: 1, notes: values.notes }).then(() => frm.reload_doc()),
					__("Uphold Appeal")
				);
			}).addClass("btn-primary");
			frm.add_custom_button(__("Reject Appeal"), () => {
				frappe.prompt(
					{ fieldname: "notes", fieldtype: "Small Text", label: __("Notes") },
					(values) => frm.call("resolve_appeal", { upheld: 0, notes: values.notes }).then(() => frm.reload_doc()),
					__("Reject Appeal")
				);
			});
		}
	},
});
