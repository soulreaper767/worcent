frappe.ui.form.on("Mentorship Request", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.status === "Requested") {
			frm.add_custom_button(__("Accept"), () => {
				frappe.confirm(
					__("Accepting will immediately charge the mentee's wallet the session fee and pay you (minus platform commission). Continue?"),
					() => frm.call("accept").then(() => frm.reload_doc())
				);
			}).addClass("btn-primary");

			frm.add_custom_button(__("Reject"), () => {
				frm.call("reject").then(() => frm.reload_doc());
			});
		}

		if (frm.doc.status === "Accepted") {
			frm.add_custom_button(__("Mark Completed"), () => {
				frm.call("complete").then(() => frm.reload_doc());
			}).addClass("btn-primary");
		}
	},
});
