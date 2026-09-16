// Floating chat widget: a launcher button (badge = total unread), a
// conversation-list view, and a message view with 5s short-polling instead
// of realtime sockets — simpler to reason about and to test headlessly.
(function () {
	if (!window.frappe) window.frappe = {};

	var state = {
		conversations: [],
		activeConversation: null,
		pollTimer: null,
		lastMessageAt: null,
	};

	function el(id) {
		return document.getElementById(id);
	}

	function call(method, args) {
		return frappe.call({ method: method, args: args || {} }).then(function (r) {
			return r.message;
		});
	}

	function escapeHtml(s) {
		var d = document.createElement("div");
		d.textContent = s || "";
		return d.innerHTML;
	}

	function refreshUnreadBadge() {
		call("worcent.worcent_marketplace.conversation_api.list_my_conversations").then(function (conversations) {
			state.conversations = conversations || [];
			var total = state.conversations.reduce(function (sum, c) {
				return sum + (c.my_unread || 0);
			}, 0);
			var dot = el("wc-chat-unread-dot");
			if (!dot) return;
			if (total > 0) {
				dot.textContent = total > 9 ? "9+" : String(total);
				dot.style.display = "flex";
			} else {
				dot.style.display = "none";
			}
		});
	}

	function renderConversationList() {
		var body = el("wc-chat-list");
		if (!state.conversations.length) {
			body.innerHTML = '<div class="wc-chat-empty">No conversations yet.</div>';
			return;
		}
		body.innerHTML = state.conversations
			.map(function (c) {
				var badge = c.my_unread ? '<span class="wc-chat-item-badge">' + c.my_unread + "</span>" : "";
				return (
					'<div class="wc-chat-list-item" data-conversation="' +
					c.name +
					'" data-name="' +
					escapeHtml(c.other_party_name || "") +
					'"><span class="wc-chat-item-name">' +
					escapeHtml(c.other_party_name || "Conversation") +
					"</span>" +
					badge +
					"</div>"
				);
			})
			.join("");
		Array.prototype.forEach.call(body.querySelectorAll(".wc-chat-list-item"), function (row) {
			row.addEventListener("click", function () {
				openConversation(row.getAttribute("data-conversation"), row.getAttribute("data-name"));
			});
		});
	}

	function renderMessages(messages) {
		var body = el("wc-chat-body");
		if (!messages.length) {
			body.innerHTML = '<div class="wc-chat-empty">Say hello 👋</div>';
			return;
		}
		body.innerHTML = messages
			.map(function (m) {
				var mine = m.is_mine;
				return (
					'<div class="wc-chat-bubble ' +
					(mine ? "wc-chat-bubble-mine" : "wc-chat-bubble-theirs") +
					'">' +
					escapeHtml(m.body) +
					"</div>"
				);
			})
			.join("");
		body.scrollTop = body.scrollHeight;
	}

	function stopPolling() {
		if (state.pollTimer) {
			clearInterval(state.pollTimer);
			state.pollTimer = null;
		}
	}

	function poll() {
		if (!state.activeConversation) return;
		call("worcent.worcent_marketplace.conversation_api.get_messages", {
			conversation: state.activeConversation,
			after: state.lastMessageAt,
		}).then(function (messages) {
			if (!messages.length) return;
			state.lastMessageAt = messages[messages.length - 1].sent_at;
			call("worcent.worcent_marketplace.conversation_api.get_messages", { conversation: state.activeConversation }).then(
				function (all) {
					renderMessages(all);
				}
			);
		});
	}

	function openConversation(name, otherPartyName) {
		state.activeConversation = name;
		state.lastMessageAt = null;
		el("wc-chat-list-view").style.display = "none";
		el("wc-chat-thread-view").style.display = "flex";
		el("wc-chat-thread-title").textContent = otherPartyName || "Conversation";

		call("worcent.worcent_marketplace.conversation_api.get_messages", { conversation: name }).then(function (messages) {
			renderMessages(messages);
			if (messages.length) state.lastMessageAt = messages[messages.length - 1].sent_at;
		});
		call("worcent.worcent_marketplace.conversation_api.mark_read", { conversation: name }).then(refreshUnreadBadge);

		stopPolling();
		state.pollTimer = setInterval(poll, 5000);
	}

	function backToList() {
		state.activeConversation = null;
		stopPolling();
		el("wc-chat-thread-view").style.display = "none";
		el("wc-chat-list-view").style.display = "block";
		refreshUnreadBadge();
		call("worcent.worcent_marketplace.conversation_api.list_my_conversations").then(function (conversations) {
			state.conversations = conversations || [];
			renderConversationList();
		});
	}

	function sendCurrentMessage() {
		var input = el("wc-chat-input");
		var body = (input.value || "").trim();
		if (!body || !state.activeConversation) return;
		input.value = "";
		call("worcent.worcent_marketplace.conversation_api.send_message", {
			conversation: state.activeConversation,
			body: body,
		}).then(function () {
			state.lastMessageAt = null;
			return call("worcent.worcent_marketplace.conversation_api.get_messages", { conversation: state.activeConversation });
		}).then(function (all) {
			renderMessages(all);
			if (all.length) state.lastMessageAt = all[all.length - 1].sent_at;
		});
	}

	function openPanel() {
		el("wc-chat-panel").classList.add("wc-chat-open");
		backToList();
	}

	function closePanel() {
		el("wc-chat-panel").classList.remove("wc-chat-open");
		stopPolling();
	}

	// Public API: called from "Contact Seller"/"Message Employer" buttons on
	// Gig/Job Posting pages to jump straight into (or start) that conversation.
	window.wcOpenConversationFor = function (relatedDoctype, relatedName) {
		call("worcent.worcent_marketplace.conversation_api.start_conversation", {
			related_doctype: relatedDoctype,
			related_name: relatedName,
		}).then(function (conversationName) {
			el("wc-chat-panel").classList.add("wc-chat-open");
			el("wc-chat-list-view").style.display = "none";
			el("wc-chat-thread-view").style.display = "flex";
			openConversation(conversationName, null);
		}).catch(function () {
			frappe.msgprint && frappe.msgprint("Couldn't start that conversation. Make sure your profile is complete.");
		});
	};

	function init() {
		var launcher = el("wc-chat-launcher");
		if (!launcher) return; // widget not rendered (e.g. guest)

		launcher.addEventListener("click", function () {
			var panel = el("wc-chat-panel");
			if (panel.classList.contains("wc-chat-open")) {
				closePanel();
			} else {
				openPanel();
			}
		});
		el("wc-chat-close").addEventListener("click", closePanel);
		el("wc-chat-back").addEventListener("click", backToList);
		el("wc-chat-send").addEventListener("click", sendCurrentMessage);
		el("wc-chat-input").addEventListener("keydown", function (e) {
			if (e.key === "Enter" && !e.shiftKey) {
				e.preventDefault();
				sendCurrentMessage();
			}
		});

		refreshUnreadBadge();
		setInterval(refreshUnreadBadge, 20000);
	}

	if (window.frappe && frappe.ready) {
		frappe.ready(init);
	} else {
		document.addEventListener("DOMContentLoaded", init);
	}
})();
