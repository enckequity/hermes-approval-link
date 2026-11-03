"""Mounted by Hermes behind its existing dashboard authentication middleware."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from hermes_photon_approvals.api import make_router  # noqa: E402

router = make_router()
