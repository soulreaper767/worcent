// Worcent storefront interactivity — kept minimal, server-rendered pages
// handle most of the UX so no client-side data fetching is required here.
(function () {
	function init() {
		document.querySelectorAll("[data-wc-toggle]").forEach(function (el) {
			el.addEventListener("click", function () {
				var target = document.querySelector(el.getAttribute("data-wc-toggle"));
				if (target) target.classList.toggle("hidden");
			});
		});
	}

	if (window.frappe && frappe.ready) {
		frappe.ready(init);
	} else {
		document.addEventListener("DOMContentLoaded", init);
	}
})();
