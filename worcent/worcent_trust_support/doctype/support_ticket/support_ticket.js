const SUPPORT_ROLES = ["Support Agent", "Worcent Admin", "System Manager"];

frappe.ui.form.on("Support Ticket", {
	setup(frm) {
		// Job Posting / Gig are the two related_doctype options that are
		// otherwise public-readable everywhere (marketplace listings), so
		// without this the "Select Record" search shows every listing on
		// the platform instead of just the ones this user actually owns --
		// every other related_doctype option is already scoped by its own
		// doctype-level permission_query_conditions.
		frm.set_query("related_record", () => {
			if (["Job Posting", "Gig"].includes(frm.doc.related_doctype)) {
				return {
					query: "worcent.worcent_trust_support.doctype.support_ticket.support_ticket.related_record_query",
				};
			}
			return {};
		});
	},

	refresh(frm) {
		if (frm.is_new()) return;

		const is_support = SUPPORT_ROLES.some((r) => frappe.user_roles.includes(r));

		// --- Status workflow buttons ---
		if (is_support && ["Open", "In Progress"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Mark Resolved"), () => {
				frm.call("mark_resolved").then(() => frm.reload_doc());
			}).addClass("btn-primary");
		}
		if (is_support && frm.doc.status !== "Closed") {
			frm.add_custom_button(__("Close Ticket"), () => {
				frm.call("close_ticket").then(() => frm.reload_doc());
			});
		}
		if (["Resolved", "Closed"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Reopen"), () => {
				frm.call("reopen_ticket").then(() => frm.reload_doc());
			});
		}
		if (is_support) {
			frm.add_custom_button(__("Reassign"), () => {
				frappe.prompt(
					{
						fieldname: "to_user", fieldtype: "Link", options: "User",
						label: __("Reassign To (leave blank for auto-pick)"),
						get_query: () => ({ query: "frappe.core.doctype.user.user.user_query", filters: { role: "Support Agent" } }),
					},
					(values) => frm.call("reassign", { to_user: values.to_user }).then(() => frm.reload_doc()),
					__("Reassign Ticket")
				);
			});
		}

		render_conversation(frm, is_support);
	},
});

function render_conversation(frm, is_support) {
	if (!frm.fields_dict.description) return;

	if (!frm.wc_conversation_wrapper) {
		frm.wc_conversation_wrapper = $('<div class="wc-ticket-conversation" style="margin-top: 20px;"></div>');
		frm.fields_dict.description.$wrapper.after(frm.wc_conversation_wrapper);
	}

	frm.call("get_replies").then((r) => {
		const replies = r.message || [];
		const wrapper = frm.wc_conversation_wrapper;
		wrapper.empty();

		wrapper.append(`<h5>${__("Conversation")}</h5>`);
		const $thread = $('<div class="wc-ticket-thread"></div>').appendTo(wrapper);

		if (!replies.length) {
			$thread.append(`<div class="text-muted" style="padding: 8px 0;">${__("No replies yet.")}</div>`);
		}

		replies.forEach((reply) => {
			const is_support_reply = reply.sender_role === "Support";
			const badge = reply.is_internal_note
				? `<span class="indicator-pill orange">${__("Internal Note")}</span>`
				: is_support_reply
				? `<span class="indicator-pill blue">${__("Support")}</span>`
				: `<span class="indicator-pill green">${__("Requester")}</span>`;

			$(`
				<div class="wc-ticket-reply" style="border: 1px solid var(--border-color); border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; ${reply.is_internal_note ? "background: var(--bg-orange, #fff7ed);" : ""}">
					<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
						<strong>${frappe.utils.escape_html(reply.sender)}</strong> ${badge}
						<span class="text-muted small">${frappe.datetime.comment_when(reply.creation)}</span>
					</div>
					<div>${reply.message}</div>
				</div>
			`).appendTo($thread);
		});

		const $composer = $(`
			<div class="wc-ticket-composer" style="margin-top: 10px;">
				<textarea class="form-control wc-reply-text" rows="3" placeholder="${__("Write a reply...")}"></textarea>
				<div style="margin-top: 6px; display:flex; gap: 8px; align-items:center;">
					<button class="btn btn-primary btn-sm wc-send-reply">${__("Send Reply")}</button>
					${is_support ? `<label style="margin:0;"><input type="checkbox" class="wc-internal-note"> ${__("Internal note (not visible to requester)")}</label>` : ""}
				</div>
			</div>
		`).appendTo(wrapper);

		$composer.find(".wc-send-reply").on("click", () => {
			const message = $composer.find(".wc-reply-text").val();
			if (!message) return;
			const is_internal = $composer.find(".wc-internal-note").is(":checked") ? 1 : 0;
			frm.call("add_reply", { message, is_internal_note: is_internal }).then(() => {
				frm.reload_doc();
			});
		});
	});
}
