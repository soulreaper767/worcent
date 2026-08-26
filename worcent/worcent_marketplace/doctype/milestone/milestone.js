frappe.ui.form.on("Milestone", {
	refresh(frm) {
		if (frm.is_new()) return;

		render_start_work_banner(frm);

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

function render_start_work_banner(frm) {
	if (frm.__wc_start_banner) frm.__wc_start_banner.remove();

	let color, text;
	if (frm.doc.status === "Pending") {
		color = "red";
		text = __("⚠ Awaiting Payment — do not start work. The employer hasn't funded this milestone yet.");
	} else if (["Funded", "Submitted", "Approved"].includes(frm.doc.status)) {
		color = "green";
		text = __("✅ Funded — payment is secured in escrow, you're clear to start (or continue) work.");
	} else if (frm.doc.status === "Released") {
		color = "blue";
		text = __("This milestone has been paid out and closed.");
	} else if (frm.doc.status === "Disputed") {
		color = "orange";
		text = __("This milestone is under dispute — check the Dispute Case before doing anything else.");
	} else {
		return;
	}

	frm.__wc_start_banner = $(`
		<div class="wc-start-work-banner" style="border-left: 4px solid var(--${color}-600, ${color}); background: var(--${color}-50, transparent); padding: 10px 14px; margin-bottom: 16px; border-radius: 4px; font-weight: 500;">
			${text}
		</div>
	`);
	frm.__wc_start_banner.prependTo(frm.layout.wrapper || frm.$wrapper.find(".form-layout"));
}
