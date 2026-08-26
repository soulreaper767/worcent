const REVIEW_ROLES = ["Payment Officer", "Finance Manager", "Worcent Admin", "System Manager"];
const PAYMENT_ROLES = ["Accounts Manager", "Finance Manager", "Worcent Admin", "System Manager"];

frappe.ui.form.on("Withdrawal Request", {
	onload(frm) {
		if (!frm.is_new()) return;
		frappe.call({
			method: "worcent.worcent_finance.doctype.withdrawal_request.withdrawal_request.get_my_withdrawal_context",
		}).then((r) => {
			const ctx = r.message;
			if (!ctx) return;
			frm.__withdrawal_ctx = ctx;
			render_balance_panel(frm, ctx);
			if (ctx.wallet) {
				frm.set_value("wallet", ctx.wallet);
			}
			frm.set_query("payout_account", () => ({
				filters: { party_type: ctx.party_type, party: ctx.party, status: "Active" },
			}));
		});
	},

	refresh(frm) {
		if (frm.is_new()) return;

		if (["Requested", "In Review"].includes(frm.doc.status) && REVIEW_ROLES.some((r) => frappe.user_roles.includes(r))) {
			if (frm.doc.status === "Requested") {
				frm.add_custom_button(__("Start Review"), () => {
					frm.call("start_review").then(() => frm.reload_doc());
				});
			}
			frm.add_custom_button(__("Approve"), () => {
				frappe.confirm(
					__("This forwards the request to Accounts for payment. Continue?"),
					() => frm.call("approve_request").then(() => frm.reload_doc())
				);
			}).addClass("btn-primary");

			frm.add_custom_button(__("Reject"), () => {
				frappe.prompt(
					{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 },
					(values) => frm.call("reject_request", { reason: values.reason }).then(() => frm.reload_doc()),
					__("Reject Withdrawal Request")
				);
			});
		}

		if (frm.doc.status === "Approved" && PAYMENT_ROLES.some((r) => frappe.user_roles.includes(r))) {
			frm.add_custom_button(__("Mark Paid"), () => {
				frappe.confirm(
					__("This debits ${0} from the wallet and records the payout as complete. Continue?", [frm.doc.amount]),
					() => frm.call("mark_paid").then(() => frm.reload_doc())
				);
			}).addClass("btn-primary");
		}
	},
});

function render_balance_panel(frm, ctx) {
	if (!frm.fields_dict.wallet) return;
	if (frm.__balance_panel) frm.__balance_panel.remove();

	const fmt = (v, c) => format_currency(v, c);
	const eligible = ctx.eligible;
	const color = eligible ? "green" : "red";
	const message = eligible
		? __("You can withdraw. Minimum is {0} ({1}).", [
				fmt(ctx.min_withdrawal, ctx.base_currency),
				fmt(ctx.min_withdrawal_in_display_currency, ctx.display_currency),
		  ])
		: __("Your balance is below the {0} ({1}) minimum withdrawal amount.", [
				fmt(ctx.min_withdrawal, ctx.base_currency),
				fmt(ctx.min_withdrawal_in_display_currency, ctx.display_currency),
		  ]);

	frm.__balance_panel = $(`
		<div class="wc-withdrawal-balance-panel" style="border: 1px solid var(--border-color); border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;">
			<div style="font-size: 13px; color: var(--text-muted);">${__("Available Balance")}</div>
			<div style="font-size: 22px; font-weight: 600;">
				${fmt(ctx.balance, ctx.base_currency)}
				${ctx.display_currency !== ctx.base_currency ? `<span style="font-size: 14px; color: var(--text-muted);"> (~${fmt(ctx.balance_in_display_currency, ctx.display_currency)})</span>` : ""}
			</div>
			<div style="color: var(--${color}-600, ${color}); margin-top: 4px; font-size: 13px;">${message}</div>
		</div>
	`);
	frm.__balance_panel.insertBefore(frm.fields_dict.wallet.$wrapper);

	if (!eligible) {
		frm.disable_save();
		frm.set_df_property("amount", "read_only", 1);
	}
}
