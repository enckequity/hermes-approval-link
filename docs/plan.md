# Photon approval cards implementation plan

Goal: deliver request-bound Photon approval cards as an installable plugin, without modifying Hermes.
Architecture: supported transport + native authenticated dashboard plugin + private SQLite decisions + official Photon card RPCs.
Spec: design.md. Execute in this session with a fresh reviewer before release.

- [x] Write failing store tests for identity/tenant/digest, expiry, concurrency, replay and restart. Implement atomic create/read/resolve/close with private file permissions.
- [x] Write failing API tests for verified interactive sessions, configured origin, content type and malicious inputs. Implement native FastAPI router; plain SDK React UI with exclusive buttons, accessible status and no build dependency.
- [x] Write failing transport/Photon tests for host-bound decisions, fail-closed exceptions, fixed DM, no retries and secret handling. Implement bounded token exchange and grpcurl using official schemas.
- [x] Offline against the pinned Hermes source, prove native registration, dashboard route mounting and host invoke_approval_transport with isolated temporary state, without enabling or restarting the owner service. Run all tests and fresh security/contract review.
- [x] Package documentation, MIT license and pinned installation/recovery instructions.
- [x] PR, verify, merge and publish the repository. PR #2 merged; public experimental release v0.1.0 is published.
- [ ] Enable live only with a qualified authenticated origin, exact approver and device evidence. Missing prerequisites are recorded in verification.md.

Review focus: real in-process approval context versus dashboard process; hostile forwarded origins; stale or simultaneous clicks; ambiguous sends and delayed callbacks; expiry, logout/revocation and private-store permissions.
