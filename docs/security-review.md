# Security review of the decision path

Reviewed 2026-11-03 against Hermes v0.22.2 (`d923a5e`). Scope: the path from `register_approval_transport` to a recorded decision. One blocking-class issue found and fixed, one deployment fix made, the rest are documented limits.

## Findings

**Request binding. Sound.** The host builds the request (`ApprovalRequest.create`) with a random ID and a SHA-256 digest over the redacted command, description, scopes and session key. `Store.resolve` accepts a decision only when ID, digest, tenant and identity all match a pending row. The host then re-checks ID, digest and allowed choice (`_validate_decision`). The digest is shown only to the authenticated approver in the page's read response, and never appears in the card URL.

**Replay. Sound.** A decision is one compare-and-set from `pending`. A second click, a later request with the same card, or a restart cannot reuse it. Request IDs are fresh per approval. A restart leaves any old `pending` row visible until its expiry. It can be answered, but no waiter exists, so nothing runs. The page can briefly still offer buttons for it. Documented limit, not a bypass.

**Timeout. One bug, fixed.** `Store.close` overwrote status unconditionally. A decision landing between the waiter's last read and its closing write could be relabelled `expired` while still holding a choice, so the page and the audit row disagreed with what Hermes did (Hermes denies on timeout either way, so this could never approve). `close` now changes only a `pending` row to a failure or expiry state, and only a decided row to `recorded`. Regression test: `test_closing_never_overwrites_a_recorded_decision`. The host deadline is still authoritative: a late answer is discarded by Hermes.

**CSRF. Sound.** POST needs the exact configured Origin, `Content-Type: application/json` and a custom `X-Photon-Approval` header (forcing a preflight from any other origin), on top of the verified dashboard session. The body is capped at 2 KB and parsed strictly. Dashboard session cookies are `SameSite=Lax`, so a cross-site frame or form cannot ride them. GET has no side effects.

**Who can approve. Owner-only by design.** The API requires `app.state.auth_required`, a verified, unexpired interactive session, and an exact match on provider, user ID and organization from operator config. Service-token callers have no `request.state.session` and get 401. Consequences:
- One approver per tenant. Selecting this transport routes every approval in that gateway profile to that one person, because a selected transport replaces all built-in prompt surfaces. That is right for the owner runtime. For a customer workspace with several members, only the configured approver can answer, and requests from other members' sessions go to them too. Do not enable it for multi-member workspaces.
- The card does not say which session asked. Only the redacted command and reason appear on the authenticated page.

**Credential in the card URL. None.** The URL is the dashboard URL plus `?request=<random id>`. The Photon project token travels only in memory and in the `grpcurl` child's environment (`-expand-headers`), never in argv, logs or SQLite. Token exchange refuses redirects. The Messages bubble shows only a generic caption.

**Deployment fix.** The owner dashboard is served at `https://owner.teamshift.io/native`, but config accepted only a bare origin, so the card link would have missed the dashboard. `PHOTON_APPROVAL_PUBLIC_URL` may now carry a plain path prefix (no query, fragment, dot segments or odd characters). The Origin check still uses scheme and host only. Tests cover both.

## Limits to accept or test live

- Hermes' dashboard sends no `frame-ancestors`/`X-Frame-Options`. `SameSite=Lax` cookies block cross-site framing in practice. Verify inside Messages.
- Pomerium sits in front of the owner dashboard. Whether its login and Hermes OIDC complete inside the Messages webview is unproven (teamshift#56).
- State is local SQLite. Anything that can already edit the tenant's database or Hermes config can bypass the plugin. It is not a defense against a compromised runtime.
- Uncertain sends are never retried. A failed send denies the request.
- Sending the card is a Spectrum/Photon API call. Delivery is best effort and may be delayed by Apple.
