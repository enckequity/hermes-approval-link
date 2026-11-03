# Security review of the decision path

Reviewed 2026-11-03 against Hermes v0.22.2 (`d923a5e`), then again after the move from Photon cards to a texted link. Scope: from `register_approval_transport` to a recorded decision.

## Findings

**Request binding. Sound.** The host builds the request with a random ID and a SHA-256 digest over the redacted command, description, scopes and session key. `Store.resolve` accepts a decision only when ID, digest, tenant and identity all match a pending row. The host re-checks ID, digest and allowed choice (`_validate_decision`). The digest reaches only the authenticated approver, in the page's read response, never the text.

**Replay. Sound.** A decision is one compare-and-set from `pending`. A second tap, a later request opened from an old text, or a restart cannot reuse it. Request IDs are fresh per approval.

**Timeout. One bug, fixed.** `Store.close` could relabel a recorded decision as expired. It now changes only a pending row to a failure or expiry state, and only a decided row to `recorded` (`test_closing_never_overwrites_a_recorded_decision`). The waiter takes its expiry before its deadline and reads once more at the deadline, so no answer is accepted after the final read. The plugin gives up one second (or half the window, if shorter) before the host, so the page cannot record an answer after Hermes timed out. A host interrupt (`/stop`) gives the plugin no signal, so an answer recorded after an interrupt is discarded by Hermes and the page says only that the answer was sent.

**Restart. Fixed.** A gateway restart used to leave a pending row answerable until expiry, with nobody waiting. The waiter now touches its row every quarter second; a pending row untouched for 15 seconds reads as expired and cannot be answered (`test_pending_row_nobody_is_waiting_on_cannot_be_answered`).

**CSRF. Sound.** POST needs the exact configured Origin, `Content-Type: application/json` and a custom `X-Approval-Link` header (forcing a preflight from any other origin), on top of the verified dashboard session. Bodies are capped at 2 KB and parsed strictly. Dashboard session cookies are `SameSite=Lax`. GET has no side effects.

**Who can approve. One configured person.** The API requires `app.state.auth_required`, a verified unexpired interactive session, and an exact match on provider, user ID and organization from operator config. Service-token callers get 401. A selected transport replaces every built-in prompt surface, so every approval in that gateway goes to this one person. That fits a single-owner runtime. Do not enable it for a workspace with several members. The text does not say which session asked; the authenticated page shows the redacted command and reason.

**Credential in the link. None.** The text holds the dashboard URL plus `?request=<random id>`, no command text and no digest. The link grants nothing without the dashboard login. A spoofed text with a look-alike domain is the phishing case: the text arrives from the owner's own chat, and the page only works on the configured origin.

**Delivery.** The text goes through Hermes' `send_message` path with the configured `platform:chat_id`, which applies Hermes' relay egress check and the front door's bound-chat check. Any failure denies and nothing is resent. The plugin holds no messaging credentials. The sent text is mirrored into the session transcript by Hermes; it contains only the link.

**Deployment fix.** `APPROVAL_LINK_PUBLIC_URL` now takes a plain path prefix (no query, dot segments or odd characters). The Origin check uses scheme and host, normalized as browsers send them (lowercase, default port dropped).

## Open item: framing (clickjacking)

I found no `frame-ancestors` or `X-Frame-Options` anywhere in the dashboard server code (`hermes_cli`). `SameSite=Lax` session cookies are not sent in cross-site frames, which blocks framing in practice, but the headers would make it explicit. The page itself now renders no buttons when `window.top !== window.self`, so it is safe without the proxy. Since the link opens in the browser, nothing needs framing, and the proxy header is the second layer. Smallest fix, and it belongs in our route, not in Hermes: set `Content-Security-Policy: frame-ancestors 'none'` on the dashboard path at the reverse proxy. Not done here; it is a deployment step.

## Limits to accept or test live

- If an authenticating proxy sits in front of the dashboard, whether login completes from a link opened out of Messages is unproven (see the acceptance checklist).
- State is local SQLite. Anything that can already edit the tenant's database or Hermes config can bypass the plugin.
- Delivery is best effort; Linq or Apple may delay the text. A late text for an expired request shows "expired".
