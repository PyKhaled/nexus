"""Evaluate Nexus blueprint policies and print the machine-readable report."""

# Allow direct execution from an uninstalled source checkout.
import sys as _sys
from pathlib import Path as _Path
_SRC = _Path(__file__).resolve().parent / "nexus_assembler"
if str(_SRC) not in _sys.path:
    _sys.path.insert(0, str(_SRC))
import argparse, json
from nexus_assembler import evaluate_policies

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("blueprint")
p.add_argument("--root")
a = p.parse_args()
report = evaluate_policies(a.blueprint, root=a.root)
print(json.dumps(report, indent=2))
raise SystemExit(0 if report.get("status") == "passed" else 3)
