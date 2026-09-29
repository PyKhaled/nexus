"""Reject missing/malformed SARIF before the tolerant report importer runs."""
import json
import sys
from pathlib import Path


def validate(path):
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict) or data.get("version") != "2.1.0":
        raise ValueError("Expected SARIF 2.1.0")
    runs = data.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("Expected at least one scanner run")
    for run in runs:
        if not isinstance(run, dict) or not isinstance(run.get("results"), list):
            raise ValueError("Scanner run must contain a results list")
        if not run.get("tool", {}).get("driver", {}).get("name"):
            raise ValueError("Scanner identity is missing")
        for result in run["results"]:
            if not isinstance(result, dict) or not isinstance(result.get("message"), dict):
                raise ValueError("Malformed scanner result")
        for invocation in run.get("invocations", []):
            if invocation.get("executionSuccessful") is False:
                raise ValueError("Scanner execution failed")
    return data


if __name__ == "__main__":
    validate(sys.argv[1])
