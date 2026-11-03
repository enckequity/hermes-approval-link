"""Hermes directory-plugin entry point. The package ships beside this file, so copying the
plugin directory is a complete install; an already installed copy of the package wins."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from hermes_photon_approvals import register  # noqa: E402
