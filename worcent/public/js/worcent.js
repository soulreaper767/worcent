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

		var navbar = document.getElementById("wc-navbar");
		var backToTop = document.getElementById("wc-back-to-top");
		function onScroll() {
			var scrolled = window.scrollY > 12;
			if (navbar) navbar.classList.toggle("wc-navbar-scrolled", scrolled);
			if (backToTop) backToTop.classList.toggle("wc-visible", window.scrollY > 500);
		}
		window.addEventListener("scroll", onScroll, { passive: true });
		onScroll();

		if (backToTop) {
			backToTop.addEventListener("click", function () {
				window.scrollTo({ top: 0, behavior: "smooth" });
			});
		}

		var navToggle = document.getElementById("wc-navbar-toggle");
		var navLinks = document.getElementById("wc-navbar-links");
		if (navToggle && navLinks) {
			navToggle.addEventListener("click", function () {
				navLinks.classList.toggle("wc-open");
			});
		}

		// Touch-friendly dropdowns: tap toggles open state instead of relying on hover.
		document.querySelectorAll(".wc-nav-dropdown-toggle").forEach(function (toggle) {
			toggle.addEventListener("click", function (e) {
				if (window.matchMedia("(hover: none)").matches) {
					e.preventDefault();
					toggle.closest(".wc-nav-dropdown").classList.toggle("wc-open");
				}
			});
		});

		// Fade-up reveal for anything marked .wc-reveal as it enters the viewport.
		var revealEls = document.querySelectorAll(".wc-reveal");
		if (revealEls.length && "IntersectionObserver" in window) {
			var observer = new IntersectionObserver(
				function (entries) {
					entries.forEach(function (entry) {
						if (entry.isIntersecting) {
							entry.target.classList.add("wc-visible");
							observer.unobserve(entry.target);
						}
					});
				},
				{ threshold: 0.12 }
			);
			revealEls.forEach(function (el) { observer.observe(el); });
		} else {
			revealEls.forEach(function (el) { el.classList.add("wc-visible"); });
		}
	}

	if (window.frappe && frappe.ready) {
		frappe.ready(init);
	} else {
		document.addEventListener("DOMContentLoaded", init);
	}
})();

// Shared helper for the /tools/* growth-tool pages: calls the tool API and
// hands the result to a page-supplied render function, then (if the run was
// saved, i.e. the visitor is logged in) renders the comparison + a "see your
// history" link; otherwise shows a "register to save this" prompt.
function wcRunTool(toolName, inputs, renderResult) {
	return frappe.call({
		method: "worcent.worcent_growth.api.use_tool",
		args: { tool_name: toolName, inputs: JSON.stringify(inputs) },
	}).then((r) => {
		const data = r.message;
		renderResult(data.output);

		const footer = document.getElementById("wc-tool-footer");
		if (!footer) return data;

		if (data.saved) {
			footer.innerHTML =
				'<div class="wc-tool-saved">' +
				'<strong>' + (data.comparison || "") + '</strong>' +
				'<span> · ' + data.history_count + ' run(s) saved</span>' +
				"</div>";
		} else {
			footer.innerHTML =
				'<div class="wc-tool-register-cta">' +
				"Register free (no verification needed) to save this result and track your progress over time. " +
				'<a class="wc-btn wc-btn-primary wc-btn-sm" href="/join?type=freelancer">Register Free</a>' +
				"</div>";
		}
		return data;
	});
}
