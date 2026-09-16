frappe.pages["worcent-admin-tools"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Worcent Admin Tools"),
		single_column: true,
	});

	$(page.body).html(`
		<div style="max-width: 640px; padding: 8px 0;">
			<div class="frappe-card" style="padding: 20px; margin-bottom: 16px;">
				<h4>${__("Reseed Demo Data")}</h4>
				<p class="text-muted">${__("Tops up demo users, gigs, jobs, contracts, and every other demo workflow. Safe to run repeatedly -- every step is idempotent.")}</p>
				<button class="btn btn-default" id="wc-reseed-btn">${__("Reseed Demo Data")}</button>
			</div>
			<div class="frappe-card" style="padding: 20px; border: 1px solid var(--red-300);">
				<h4>${__("Remove All Demo Data")}</h4>
				<p class="text-muted">${__("Permanently deletes every demo user (*.demo@worcent.test) and everything linked to them -- gigs, jobs, contracts, wallets, disputes, the lot. Master data (categories, plans, badges, referral programs) is never touched. This cannot be undone.")}</p>
				<button class="btn btn-danger" id="wc-remove-demo-btn">${__("Remove All Demo Data")}</button>
			</div>
			<div id="wc-admin-tools-result" style="margin-top: 16px;"></div>
		</div>
	`);

	page.body.find("#wc-reseed-btn").on("click", function () {
		const btn = $(this);
		btn.prop("disabled", true).text(__("Reseeding..."));
		frappe.call({ method: "worcent.install.reseed_demo_data" }).then(() => {
			btn.prop("disabled", false).text(__("Reseed Demo Data"));
			frappe.show_alert({ message: __("Demo data reseeded."), indicator: "green" });
		}).catch(() => {
			btn.prop("disabled", false).text(__("Reseed Demo Data"));
		});
	});

	page.body.find("#wc-remove-demo-btn").on("click", function () {
		const btn = $(this);
		frappe.confirm(
			__("This permanently deletes every demo user and everything linked to them. This cannot be undone. Continue?"),
			() => {
				btn.prop("disabled", true).text(__("Removing..."));
				frappe.call({ method: "worcent.demo_cleanup.remove_demo_data" }).then((r) => {
					btn.prop("disabled", false).text(__("Remove All Demo Data"));
					const result = r.message || {};
					frappe.show_alert({ message: __("Removed {0} demo records.", [result.deleted || 0]), indicator: "green" });
					$("#wc-admin-tools-result").html(
						result.deleted
							? `<pre>${JSON.stringify(result.breakdown, null, 2)}</pre>`
							: `<p>${result.message || ""}</p>`
					);
				}).catch(() => {
					btn.prop("disabled", false).text(__("Remove All Demo Data"));
				});
			}
		);
	});
};
