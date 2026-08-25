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

		var navbar = document.querySelector(".navbar");
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
