// Small shared helper for the "☆ Save" buttons on Gig/Job Posting/Freelancer
// Profile/Agency pages. Each button calls wcToggleSave(doctype, name, btnEl).
window.wcToggleSave = function (itemDoctype, itemName, btn) {
	if (!window.frappe || frappe.boot === undefined) {
		window.location.href = "/login";
		return;
	}
	btn.disabled = true;
	frappe
		.call({
			method: "worcent.worcent_marketplace.saved_item_api.toggle_saved_item",
			args: { item_doctype: itemDoctype, item_name: itemName },
		})
		.then(function (r) {
			btn.disabled = false;
			btn.textContent = r.message.saved ? "★ Saved" : "☆ Save";
		})
		.catch(function () {
			btn.disabled = false;
		});
};
