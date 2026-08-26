frappe.ui.form.on("Assisted Request", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.status === "New") {
			frm.add_custom_button(__("Mark In Progress"), () => {
				frm.call("mark_in_progress").then(() => frm.reload_doc());
			});
		}

		if (["New", "In Progress"].includes(frm.doc.status)) {
			const label =
				frm.doc.request_type === "Post Job"
					? __("Convert to Job Posting")
					: frm.doc.request_type === "Apply to Job"
					? __("Convert to Proposal")
					: __("Convert to Freelancer Profile");

			frm.add_custom_button(__(label), () => {
				if (frm.doc.request_type === "Apply to Job" && !frm.doc.related_job_posting) {
					frappe.msgprint(__("Set the Related Job Posting first."));
					return;
				}
				frappe.confirm(
					__("This creates a real account and record on the requester's behalf. Continue?"),
					() =>
						frm.call("convert").then((r) => {
							if (r.message) {
								frappe.msgprint(__("Converted to {0}: {1}", [r.message.doctype, r.message.name]));
							}
							frm.reload_doc();
						})
				);
			}).addClass("btn-primary");

			frm.add_custom_button(__("Close"), () => {
				frm.call("close").then(() => frm.reload_doc());
			});
		}

		if (frm.doc.status === "Converted" && frm.doc.converted_to_doctype && frm.doc.converted_to_name) {
			frm.add_custom_button(__("View {0}", [frm.doc.converted_to_doctype]), () => {
				frappe.set_route("Form", frm.doc.converted_to_doctype, frm.doc.converted_to_name);
			});
		}
	},
});
