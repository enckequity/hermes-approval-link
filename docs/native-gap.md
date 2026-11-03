# What native Hermes already does, and the gap

Checked against unchanged Hermes v0.22.2 (`d923a5eb487a17c0a68801bba9ef0f56c81040a8`), the version TeamShift pins in `upstream-context.json`. Conclusion: native covers the approval decision itself but not a tappable, request-bound approval inside Messages, so this plugin is still needed. It stays a bounded exception to TeamShift's native-only policy.

## What native offers over Messages

- **Photon adapter has no approval buttons.** `plugins/platforms/photon/adapter.py` never overrides `_send_exec_approval_prompt`, so `supports_exec_approval_buttons()` is false (`gateway/platforms/base.py`). The gateway sends the plain-text fallback from `_format_exec_approval_fallback` (`gateway/run.py`): the command, the reason, and instructions to type `/approve`, `/approve session`, `/approve always` or `/deny`.
- **Typed `/approve` is not bound to a request.** `_handle_approve_command` (`gateway/slash_commands.py`) ignores any ID. It resolves the oldest pending approval for the session (first in, first out), or every pending one with `all`. `resolve_gateway_approval` can match a `request_id`, but nothing in the typed path supplies one. A late `/approve` can answer a different command than the one the person was looking at.
- **Wider choices than a person may intend.** The text prompt offers session and permanent grants next to once.
- **Telegram and Slack do have buttons.** Their adapters render inline buttons that call `resolve_gateway_approval`. The Photon adapter does not, and its sidecar exposes polls but no card or mini-app send route. The upstream attempt to add one (NousResearch/hermes-agent#59672) was closed unmerged, so there is no stock Photon button path to configure.
- **Polls are not an approval answer.** Photon renders native polls for clarification questions. Turning approval options into a poll would still resolve through the same unbound path.
- **The native dashboard has approval UI.** It works for a session you are attached to. It does not push anything to the phone, so on its own it cannot tell you a command is waiting.
- **Who may answer.** For typed approvals, anyone the Photon platform admits (`PHOTON_ALLOWED_USERS`) can answer in the conversation. There is no separate approver identity.
- **Native plugin seam exists.** v0.22.2 provides `register_approval_transport` (`hermes_cli/plugins.py`, `hermes_cli/approval_transport.py`). A selected transport replaces every built-in prompt surface, and the host validates the request ID, digest, allowed choices and timeout, failing closed (`tools/approval_prompt.py`). This plugin uses that seam, so no Hermes source changes.

## The exact gap this fills

1. A push to the phone that arrives as one card per request, with Approve once and Deny, instead of text the person must type.
2. A decision bound to the exact request ID and digest, with one winner, so a stale card can never approve a later command.
3. A named approver: the card page only accepts the one verified dashboard identity (provider, user, organization) configured for the tenant, not whoever can text the gateway.
4. No session or permanent grant from the phone. Only `once` and `deny`.

## What this is not

It does not change which actions need approval, does not execute anything, and does not replace native approvals elsewhere. With `security.approval.transport: builtin` everything is stock again.

## Messaging stack constraints

- **Photon 2 transport (`deploy/photon2-transport`).** That is the purchased-line Beta receiver. The Beta API has no mini-app card variant, and the plugin does not use it. Cards go through the Spectrum project the owner's native Photon channel already uses (project token exchange plus gRPC), as qualified in teamshift#56. The plugin shares no state with the photon2 outbox, so its STOP and audience rules do not apply to cards. Cards go to one fixed owner DM, never a group.
- **iMessage front door (`deploy/imessage-front-door`).** When `GATEWAY_RELAY_URL` is set, Hermes turns off every directly connected messaging platform in that workspace, Photon included. The approval plugin does not depend on the Hermes Photon platform (it calls Spectrum itself), so it would still load. It is still not supported there: front-door workspaces have no Spectrum project or confirmed DM for the plugin to use. Approvals in those workspaces stay native.
- **Customers.** teamshift#56 holds customer activation until a customer has their own Photon project, DM-only (or verified-recipient) delivery, and an authenticated page that works inside Messages. Owner first.
