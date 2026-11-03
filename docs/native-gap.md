# What native Hermes already does, and the gap

Checked against unchanged Hermes v0.22.2 (`d923a5eb487a17c0a68801bba9ef0f56c81040a8`), the pinned version. Native covers the approval decision but not a request-bound approval over Messages, so this plugin is still needed. It stays a bounded exception to the native-only policy.

## Typed text, on every messaging path

- **Direct platforms.** An adapter without approval buttons gets the plain-text prompt from `_format_exec_approval_fallback` (`gateway/run.py`): the command, the reason, and instructions to type `/approve`, `/approve session`, `/approve always` or `/deny`. The Photon adapter has no buttons.
- **Relay (the Linq front door).** The relay adapter tries a native-button prompt (`_send_exec_approval_prompt`, `gateway/relay/adapter.py`) only if the connector advertises the `prompt` op. The front door advertises `supported_ops: ['send','typing']` (`deploy/imessage-front-door/front-door.mjs`), and Linq has no iMessage buttons, so the prompt is unavailable and Hermes falls back to the same typed text, delivered as an ordinary text.
- **Typed `/approve` is not request-bound.** `_handle_approve_command` (`gateway/slash_commands.py`) ignores any ID and resolves the oldest pending approval for the session, or all of them with `all`. The text prompt also offers session and permanent grants.
- **Buttons would not fix it.** Even where a connector does support buttons, the relay's `_resolve_exec_approval` calls `resolve_gateway_approval(session_key, choice)` without a request ID, so a press also resolves the oldest pending approval.
- **Who may answer.** Whoever the front door has bound to that workspace (a `/link`ed iMessage sender). There is no separate approver identity or dashboard login.
- **Native dashboard approvals** work for a session you are attached to, but push nothing to the phone.
- **The seam exists.** `register_approval_transport` (`hermes_cli/plugins.py`, `hermes_cli/approval_transport.py`): a selected transport replaces all built-in prompt surfaces, and the host validates request ID, digest, allowed choices and timeout, failing closed (`tools/approval_prompt.py`).

## The exact gap

1. A text per request with a link to a tappable Approve once / Deny page, instead of typing a command.
2. A decision bound to the exact request ID and digest, with one winner, so a stale text can never approve a later command.
3. A named approver: only the configured verified dashboard identity can answer.
4. No session or permanent grant from the phone.

## Where the text comes from

The plugin calls Hermes' own `send_message` tool function with the configured `platform:chat_id`. That reaches the live adapter (the relay adapter in a front-door workspace), passes Hermes' relay egress check (the chat must be one the gateway has seen) and the front door's own check (an instance may only text chats of users bound to it). No change to the front door is required, and the plugin has no provider code, so nothing depends on Photon or Linq specifically.

Linq sandbox limits apply: it only texts people who texted first, and a first message in a new chat cannot contain a link (error 1005). The owner already has a chat, so the link goes through. If a chat is ever recreated, the send fails and the approval is denied until the owner texts again.
