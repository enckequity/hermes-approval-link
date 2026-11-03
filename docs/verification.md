# Verification

Tested 2026-10-17 on an isolated test host, using unchanged official Hermes v0.22.2, revision `d923a5eb487a17c0a68801bba9ef0f56c81040a8`. Development source and temporary databases were isolated from the active gateway. No local runtime was installed, no gateway settings changed and no service restarted.

## Passing evidence

- 26 Python unittest tests: real host transport request binding, approval and denial; native manifest validation, real plugin-manager registration, wrong-home transport invisibility and native dashboard API mounting; verified-session identity/provider/org and expiry; CSRF origin/header/content type; atomic concurrency, duplicate/stale/digest/tenant rejection; private file permissions and symlinks; host interruption and late response; failed card preview updates; secret-safe RPC arguments and failure messages.
- Two Node UI tests: exactly two buttons, no multi-select control, command passed as text, request-bound decision payload, disabled buttons after a decision and no submission from an expired card. These use an SDK/React test harness, not a real browser or iPhone.
- `node --check dashboard/dist/index.js` passed.
- A wheel built successfully in the same environment using setuptools. Installation still requires the full directory checkout for the native dashboard assets and plugin manifest.
- Fresh independent review found no blocking security issue. Its test-coverage requests were added. Its packaging finding was fixed: the root-only `/dist/` ignore preserves the dashboard assets in the Git release.

## Not established

Photon network calls are mocked in this suite. The earlier separate operator qualification demonstrated Spectrum card send/update and in-Messages opening; it does not prove this plugin's live authenticated approval flow. No live approval card was sent by these tests and no command executed. Native route mounting is tested separately from the real login/device flow.

The private owner runtime currently has no qualified authenticated public dashboard origin or configured approver identity. Activation remains disabled until an operator supplies and qualifies those existing prerequisites. No private dashboard has been exposed. Customer activation also needs the architecture owner's exact runtime/identity handoff and live tenant-denial/lifecycle checks.

Before production, verify login inside Spectrum, the exact configured approver, one harmless command approval and denial, exclusive taps, concurrent requests, expired/replayed/wrong-tenant cards, logout/revocation, restart and device rendering. Keep execution results distinct from a recorded decision. Inline transcript rendering remains device-dependent. Other Hermes releases, dedicated Photon lines and Photon 2 beta projects are unqualified.

## Live-button probe and corrective release

On 2026-10-17, an operator received a harmless static demo sent through Spectrum with `live: true` and explicitly confirmed both that Approve/Deny buttons were visible in the message bubble and that they worked without opening a panel. The demo changes local display only, resets on reload, and has no command authority, storage or server callback. This qualifies inline rendering on that tested device, not the authenticated approval flow. Demo source is in `demo/` (PR #5).

The probe exposed two v0.1.0 defects hidden by mocked network tests: `MiniAppLayout.summaryText` was not a valid proto field, and the default urllib user agent received Cloudflare HTTP403. v0.1.1 uses the actual `summary` field and a descriptive connector user agent; a live token-only check with that user agent returned HTTP200 and a shared-line token. All 28 Python tests and four Node tests (including the demo) passed for this fix. A regression test now parses both send and update payloads against descriptors generated from the installed official 2.3.0 proto schemas. It reproduced the invalid-field failure before the fix. No automatic resend followed an uncertain delivery; the invalid field was confirmed as a local pre-transmission parsing failure before the corrected send.

## Managed customer qualification and preview deadline fix

Historical evidence from the retired customer-worker setup (Hermes v0.21.3). It does not describe the current TeamShift deployment.

On 2026-10-17, the managed customer worker ran unchanged Hermes v0.21.3 (`345cd2b057a452236de401d3534b8502a7465e8d`). The native plugin installer and validator accepted v0.1.1. The full Photon chat channel remains explicitly disabled; only the approval transport is enabled.

A real native terminal approval removed an owned empty test directory after an authenticated QA user selected Approve once through the dashboard API. Deny left the second directory intact. Missing CSRF headers and a foreign Origin returned 403; a wrong request digest and replayed decisions returned 409. These checks used the actual customer login and transport, without changing Hermes source. They establish server-side execution behavior, not iPhone acceptance.

Both cards reached the designated operator conversation after the operator initiated the new shared-line conversation. The one-second preview update budget timed out. Updating the same existing card with a ten-second budget succeeded in 2.14 seconds. v0.1.2 gives preview updates the existing send budget, capped at half the remaining approval deadline. No uncertain send was retried. The regression test failed at both tested deadlines before the fix and passed afterward.

All 29 Python tests passed on that managed worker, including the official 2.3.0 proto checks. Four Node interface tests, JavaScript syntax validation and the v0.1.2 wheel build also passed. The route-mounting test now uses the native outer mount function shared with v0.21.3 rather than a newer private helper.

The authenticated Spectrum sign-in and request page still need iPhone acceptance. Live concurrent requests, expiry, restart and logout/revocation remain separate release checks; unit coverage is not proof of those live flows. The static demo's earlier device acceptance does not close these checks.

## Revival check, 2026-11-03

Offline, against the pinned Hermes v0.22.2 source (`d923a5eb487a17c0a68801bba9ef0f56c81040a8`), Python 3.14 virtualenv, no provider calls and no message sent. Command: `scripts/test-offline.sh`. The result summary is in the pull request. Changes covered by new tests: closing never overwrites a recorded decision, dashboard path prefix handling, the copied plugin directory loading without a `pip install`, and the manifest matching the runtime files. The live authenticated phone flow is still unproven; use [the acceptance checklist](live-acceptance.md).
