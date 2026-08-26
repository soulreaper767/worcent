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
		this.$toolbar = $(`
			<div class="wc-ledger-toolbar" style="display:flex; align-items:center; gap: 8px; margin: 8px 0 16px;">
				<label style="margin:0; font-weight: 500;">${__("Currency")}:</label>
				<select class="form-control wc-ledger-currency" style="width: auto; display:inline-block;">
					<option value="USD">USD</option>
				</select>
			</div>
		`).appendTo(this.page.body);

		this.$currency_select = this.$toolbar.find(".wc-ledger-currency");
		this.$currency_select.on("change", () => {
			this.currency = this.$currency_select.val();
			this.load();
		});

		this.$summary = $(`
			<div class="wc-ledger-summary" style="display:flex; gap: 24px; margin: 0 0 16px; flex-wrap: wrap;">
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

			this.populate_currency_options(data.currencies, data.currency);

			this.$summary.find(".wc-ledger-balance").text(data.current_balance_fmt);
			this.$summary.find(".wc-ledger-earnings").text(data.total_earnings_fmt);
			this.$summary.find(".wc-ledger-deductions").text(data.total_deductions_fmt);

			this.render_table(data);
		});
	}

	populate_currency_options(currencies, selected) {
		if (!currencies || !currencies.length) return;
		const current_options = this.$currency_select.find("option").map((_, o) => o.value).get();
		const same = current_options.length === currencies.length && current_options.every((c, i) => c === currencies[i]);
		if (!same) {
			this.$currency_select.empty();
			currencies.forEach((c) => this.$currency_select.append(`<option value="${c}">${c}</option>`));
		}
		this.$currency_select.val(selected);
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
				<td>${frappe.utils.escape_html(row.date)}</td>
				<td>${frappe.utils.escape_html(row.label)}${row.remarks ? `<div class="text-muted small">${frappe.utils.escape_html(row.remarks)}</div>` : ""}</td>
				<td style="text-align:right; color: var(--green-600, green);">${frappe.utils.escape_html(row.earnings_fmt)}</td>
				<td style="text-align:right; color: var(--red-600, red);">${frappe.utils.escape_html(row.deductions_fmt)}</td>
				<td style="text-align:right; font-weight: 500;">${frappe.utils.escape_html(row.balance_fmt)}</td>
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
