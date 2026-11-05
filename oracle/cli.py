"""Command-line interface."""
from __future__ import annotations

import argparse
import json

from .models import ResearchMode
from .orchestrator import OracleOrchestrator
from .storage import ResearchStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oracle", description="Offline scientific research scaffold")
    parser.add_argument("question", help="Scientific research question")
    parser.add_argument("--mode", choices=[m.value for m in ResearchMode],
                        default=ResearchMode.BOTH.value)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--db", default="data/oracle.sqlite3")
    parser.add_argument("--json", action="store_true", help="Print machine-readable run output")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run = OracleOrchestrator(ResearchStore(args.db)).run(
        args.question, ResearchMode(args.mode), args.cycles
    )
    if args.json:
        print(json.dumps(run.to_dict(), indent=2, ensure_ascii=False))
        return
    print(f"ORACLE run: {run.run_id}")
    print(f"Status: {run.status.value} | Mode: {run.mode.value} | Cycles: {run.current_cycle}/{run.max_cycles}")
    print(f"Question: {run.question}")
    print(f"Evidence records: {len(run.evidence)} (planning inference only in offline baseline)")
    print(f"Hypotheses: {len(run.hypotheses)}")
    print(f"Experiment designs: {len(run.experiments)} (proposed, not performed)")
    print("\nFindings and limitations:")
    for finding in run.findings:
        print(f"- {finding}")
    print("\nNext-step decisions:")
    for decision in run.decisions:
        print(f"- {decision}")


if __name__ == "__main__":
    main()
