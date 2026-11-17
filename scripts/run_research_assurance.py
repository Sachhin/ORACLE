#!/usr/bin/env python3
"""Run ORACLE's five model-free research-assurance modules on a JSON bundle."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from oracle.research_assurance import run_research_assurance


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="ORACLE run/artifact JSON")
    parser.add_argument("--output", default="artifacts/research_assurance/report.json")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = run_research_assurance(payload)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(target),
                      "modules": {key: value["status"] for key, value in report["modules"].items()}},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
