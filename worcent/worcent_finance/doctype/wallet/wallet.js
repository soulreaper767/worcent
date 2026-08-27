frappe.ui.form.on("Wallet", {
	refresh(frm) {
		if (frm.is_new()) return;

		// For a Freelancer, this balance is money Worcent owes them --
		// their receivable (mirrored on Worcent's own books as a payable
		// against their linked Supplier). For an Employer it's their own
		// prepaid balance, not a receivable, so only relabel one side.
		if (frm.doc.party_type === "Freelancer Profile") {
			frm.set_df_property("balance", "label", __("Receivable (USD)"));
		}

		frm.add_custom_button(__("View Full Ledger"), () => {
			frappe.route_options = { wallet: frm.doc.name };
			frappe.set_route("wallet-ledger");
		}).addClass("btn-primary");
	},
});
