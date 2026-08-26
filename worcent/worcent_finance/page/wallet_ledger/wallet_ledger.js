frappe.pages["wallet-ledger"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Wallet Ledger"),
		single_column: true,
	});

	new WalletLedger(page);
};

class WalletLedger {
	constructor(page) {
		this.page = page;
		this.currency = "USD";
		this.render_shell();
		this.load();
	}

	render_shell() {
		this.currency_select = this.page.add_field({
			fieldtype: "Select",
			fieldname: "currency",
			label: __("Currency"),
			options: ["USD"],
			default: "USD",
			change: () => {
				this.currency = this.currency_select.get_value() || "USD";
				this.load();
			},
		});

		this.$summary = $(`
			<div class="wc-ledger-summary" style="display:flex; gap: 24px; margin: 16px 0; flex-wrap: wrap;">
				<div><div class="text-muted small">${__("Current Balance")}</div><div class="wc-ledger-balance" style="font-size: 22px; font-weight: 600;">--</div></div>
				<div><div class="text-muted small">${__("Total Earnings")}</div><div class="wc-ledger-earnings" style="font-size: 18px; color: var(--green-600, green);">--</div></div>
				<div><div class="text-muted small">${__("Total Deductions / Payments")}</div><div class="wc-ledger-deductions" style="font-size: 18px; color: var(--red-600, red);">--</div></div>
			</div>
		`).appendTo(this.page.body);

		this.$table_wrapper = $('<div class="wc-ledger-table-wrapper" style="overflow-x:auto;"></div>').appendTo(this.page.body);
	}

	load() {
		frappe.call({
			method: "worcent.worcent_finance.wallet_ledger_api.get_wallet_ledger",
			args: { currency: this.currency },
			freeze: true,
		}).then((r) => {
			const data = r.message;
			if (!data) return;

			if (data.currencies && this.currency_select.df.options.length <= 1) {
				this.currency_select.df.options = data.currencies;
				this.currency_select.refresh();
			}

			this.$summary.find(".wc-ledger-balance").text(data.current_balance_fmt || format_currency(data.current_balance, data.currency));
			this.$summary.find(".wc-ledger-earnings").text(format_currency(data.total_earnings, data.currency));
			this.$summary.find(".wc-ledger-deductions").text(format_currency(data.total_deductions, data.currency));

			this.render_table(data);
		});
	}

	render_table(data) {
		if (!data.wallet) {
			this.$table_wrapper.html(`<div class="text-muted" style="padding: 24px 0;">${__("No wallet found for your account yet.")}</div>`);
			return;
		}
		if (!data.rows.length) {
			this.$table_wrapper.html(`<div class="text-muted" style="padding: 24px 0;">${__("No transactions yet.")}</div>`);
			return;
		}

		const rows = data.rows
			.map(
				(row) => `
			<tr>
				<td>${frappe.datetime.str_to_user(row.date)}</td>
				<td>${frappe.utils.escape_html(row.label)}${row.remarks ? `<div class="text-muted small">${frappe.utils.escape_html(row.remarks)}</div>` : ""}</td>
				<td style="text-align:right; color: var(--green-600, green);">${row.earnings ? format_currency(row.earnings, data.currency) : ""}</td>
				<td style="text-align:right; color: var(--red-600, red);">${row.deductions ? format_currency(row.deductions, data.currency) : ""}</td>
				<td style="text-align:right; font-weight: 500;">${format_currency(row.balance, data.currency)}</td>
			</tr>`
			)
			.join("");

		this.$table_wrapper.html(`
			<table class="table table-bordered">
				<thead>
					<tr>
						<th>${__("Date")}</th>
						<th>${__("Description")}</th>
						<th style="text-align:right;">${__("Earnings")}</th>
						<th style="text-align:right;">${__("Deductions / Payments")}</th>
						<th style="text-align:right;">${__("Balance")}</th>
					</tr>
				</thead>
				<tbody>${rows}</tbody>
			</table>
		`);
	}
}
