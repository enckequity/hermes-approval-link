#!/bin/sh
# Offline test run against the pinned Hermes v0.22.2 source. No Docker, no live provider calls.
# Usage: scripts/test-offline.sh [work-dir]   (default: ./.work, git-ignored)
# Optional: PHOTON_APPROVAL_GRPCURL and PHOTON_APPROVAL_PROTO_DIR enable the official proto-schema test.
set -eu
PIN=d923a5eb487a17c0a68801bba9ef0f56c81040a8
ROOT=$(cd "$(dirname "$0")/.." && pwd)
WORK=${1:-$ROOT/.work}
mkdir -p "$WORK"
if [ ! -d "$WORK/hermes/.git" ]; then
  git clone -q --depth 1 --branch v0.22.2 https://github.com/NousResearch/hermes-agent.git "$WORK/hermes"
fi
[ "$(git -C "$WORK/hermes" rev-parse HEAD)" = "$PIN" ] || { echo "Hermes checkout is not $PIN" >&2; exit 1; }
if [ ! -x "$WORK/venv/bin/python" ]; then
  uv venv -q --python 3.14 "$WORK/venv"
  uv pip install -q --python "$WORK/venv/bin/python" -e "$WORK/hermes[web]" httpx protobuf
fi
cd "$ROOT"
"$WORK/venv/bin/python" -m unittest discover -s tests -v
node --check dashboard/dist/index.js
node --test tests/frontend.test.cjs
