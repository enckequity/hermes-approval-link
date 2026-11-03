# Guardrails

Keep Hermes source unchanged. No auto-approval, command execution, permanent grants or fallback allow. No messaging-provider code, secrets or private identifiers in files, tests or logs. Test with `scripts/test-offline.sh` (no Docker, no live calls). No GitHub Actions. Security rules: [docs/security-review.md](docs/security-review.md).
