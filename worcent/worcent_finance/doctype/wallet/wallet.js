frappe.ui.form.on("Wallet", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("View Full Ledger"), () => {
			frappe.set_route("List", "Wallet Transaction", { wallet: frm.doc.name });
		}).addClass("btn-primary");
	},
});
