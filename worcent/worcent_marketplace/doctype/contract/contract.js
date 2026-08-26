frappe.ui.form.on("Contract", {
	refresh(frm) {
		if (frm.is_new()) return;
		render_milestone_status_panel(frm);
	},
});

function render_milestone_status_panel(frm) {
	if (frm.__wc_milestone_panel) frm.__wc_milestone_panel.remove();

	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Milestone",
			filters: { contract: frm.doc.name },
			fields: ["name", "title", "amount", "status"],
			order_by: "creation asc",
			limit_page_length: 0,
		},
	}).then((r) => {
		const milestones = r.message || [];
		if (!milestones.length) return;

		const unfunded = milestones.filter((m) => m.status === "Pending");
		const color = unfunded.length ? "red" : "green";
		const headline = unfunded.length
			? __("⚠ {0} milestone(s) not yet funded — do not start work on those until they show Funded.", [unfunded.length])
			: __("✅ All milestones are funded or further along — you're clear to work.");

		const rows = milestones
			.map(
				(m) => `
			<div style="display:flex; justify-content:space-between; padding: 4px 0; border-bottom: 1px solid var(--border-color);">
				<a href="/app/milestone/${m.name}">${frappe.utils.escape_html(m.title || m.name)}</a>
				<span>${format_currency(m.amount, "USD")} — <b>${m.status}</b></span>
			</div>`
			)
			.join("");

		frm.__wc_milestone_panel = $(`
			<div class="wc-milestone-status-panel" style="border-left: 4px solid var(--${color}-600, ${color}); background: var(--${color}-50, transparent); padding: 10px 14px; margin-bottom: 16px; border-radius: 4px;">
				<div style="font-weight: 500; margin-bottom: 6px;">${headline}</div>
				${rows}
			</div>
		`);
		frm.__wc_milestone_panel.prependTo(frm.layout.wrapper || frm.$wrapper.find(".form-layout"));
	});
}
