"""Validate Nexus Compose structure. Read-only; suitable for CI and agents."""

# Allow direct execution from an uninstalled source checkout.
import sys as _sys
from pathlib import Path as _Path
_SRC = _Path(__file__).resolve().parent / "nexus_assembler"
if str(_SRC) not in _sys.path:
    _sys.path.insert(0, str(_SRC))
import argparse, json
from nexus_assembler import validate_compose

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("compose")
p.add_argument("--root")
a = p.parse_args()
print(json.dumps(validate_compose(a.compose, root=a.root), indent=2))
