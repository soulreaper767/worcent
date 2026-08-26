frappe.ui.form.on("Proposal", {
	refresh(frm) {
		if (frm.is_new()) return;

		const open = ["Submitted", "Shortlisted"].includes(frm.doc.status);

		if (open) {
			frm.add_custom_button(__("Accept (Create Contract)"), () => {
				frappe.confirm(
					__("This creates a live Contract with the freelancer and a first Milestone for the bid amount. Continue?"),
					() =>
						frm.call("accept_proposal").then((r) => {
							if (r.message) {
								frappe.msgprint(__("Contract created: {0}", [r.message]));
							}
							frm.reload_doc();
						})
				);
			}).addClass("btn-primary");

			if (frm.doc.status === "Submitted") {
				frm.add_custom_button(__("Shortlist"), () => {
					frm.call("shortlist_proposal").then(() => frm.reload_doc());
				});
			}

			frm.add_custom_button(__("Reject"), () => {
				frm.call("reject_proposal").then(() => frm.reload_doc());
			});

			frm.add_custom_button(__("Withdraw"), () => {
				frappe.confirm(__("Withdraw this proposal?"), () =>
					frm.call("withdraw_proposal").then(() => frm.reload_doc())
				);
			});
		}
	},
});
