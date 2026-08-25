frappe.ui.form.on("Milestone", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.status === "Pending") {
			frm.add_custom_button(__("Fund Escrow"), () => {
				frappe.confirm(
					__("This will charge the employer's wallet (milestone amount + platform fee) and move the funds into escrow. Continue?"),
					() => frm.call("fund").then(() => frm.reload_doc())
				);
			}).addClass("btn-primary");
		}

		if (["Funded", "Submitted"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Approve & Release"), () => {
				frappe.confirm(
					__("This releases the escrowed amount to the freelancer (net of commission) and closes this milestone. Continue?"),
					() => frm.call("approve_and_release").then((r) => {
						if (r.message) {
							frappe.msgprint(
								__("Released. Freelancer commission: {0}% (${1}), net paid: ${2}", [
									r.message.freelancer_rate,
									flt(r.message.commission_amount).toFixed(2),
									flt(r.message.net_amount).toFixed(2),
								])
							);
						}
						frm.reload_doc();
					})
				);
			}).addClass("btn-primary");

			frm.add_custom_button(__("Refund to Employer"), () => {
				frappe.confirm(
					__("This refunds the escrowed milestone amount back to the employer. The platform fee already charged at funding time is NOT refunded. Continue?"),
					() => frm.call("refund").then(() => frm.reload_doc())
				);
			});
		}
	},
});
