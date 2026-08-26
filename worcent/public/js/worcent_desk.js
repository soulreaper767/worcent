// Desk-only (loaded via app_include_js, never on the public website — see
// hooks.py). Adds a "Switch to Employer/Freelancer View" button in the
// navbar for users who have both a Freelancer Profile and an Employer
// Profile, since Role.home_page can only send a dual-role user to one of
// the two on login and there's otherwise no obvious way back to the other.
(function () {
	var lastPath = null;

	function renderSwitchButton() {
		var dual = frappe.boot && frappe.boot.worcent_dual_role;
		if (!dual || !dual.is_freelancer || !dual.is_employer) return;

		var onBusiness = window.location.pathname.indexOf("my-business") !== -1;
		var target = onBusiness ? "/desk/my-freelance" : "/desk/my-business";
		var label = onBusiness ? "Switch to Freelancer View" : "Switch to Employer View";

		var $existing = $("#wc-role-switch-btn");
		if ($existing.length) {
			$existing.attr("href", target).text(label);
			return;
		}

		var $btn = $(
			'<li class="nav-item">' +
				'<a id="wc-role-switch-btn" class="btn btn-sm btn-default" href="' +
				target +
				'" style="margin: 6px 8px; white-space: nowrap;">' +
				label +
				"</a></li>"
		);

		var $target = $(".navbar-nav.ml-auto").first();
		if (!$target.length) $target = $("#navbar-right").first();
		if ($target.length) $target.prepend($btn);
	}

	function checkPathAndRender() {
		if (window.location.pathname !== lastPath) {
			lastPath = window.location.pathname;
			renderSwitchButton();
		}
	}

	frappe.after_ajax(function () {
		checkPathAndRender();
		// Desk is an SPA using pushState; polling the path is the most
		// version-agnostic way to catch in-app navigation between the two
		// workspaces without depending on a specific router event API.
		setInterval(checkPathAndRender, 800);
	});
})();
