"""Command-line interface."""
from __future__ import annotations

import argparse
import json

from .models import ResearchMode
from .orchestrator import OracleOrchestrator
from .storage import ResearchStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oracle", description="Offline scientific research foundation")
    parser.add_argument("question", nargs="?", help="Scientific research question")
    parser.add_argument("--mode", choices=[m.value for m in ResearchMode], default=ResearchMode.BOTH.value)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--resume", dest="resume_id", help="Resume an existing run by ID")
    parser.add_argument("--db", default="data/oracle.sqlite3")
    parser.add_argument("--json", action="store_true", help="Print machine-readable run output")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    orchestrator = OracleOrchestrator(ResearchStore(args.db))
    if args.resume_id:
        run = orchestrator.resume(args.resume_id, additional_cycles=args.cycles)
    else:
        if not args.question:
            raise SystemExit("A question is required unless --resume is supplied.")
        run = orchestrator.run(args.question, ResearchMode(args.mode), args.cycles)
    if args.json:
        print(json.dumps(run.to_dict(), indent=2, ensure_ascii=False))
        return
    print(f"ORACLE run: {run.run_id}")
    print(f"Status: {run.status.value} | Mode: {run.mode.value} | Cycles: {run.current_cycle}/{run.max_cycles}")
    print(f"Claims: {len(run.claims)} | Evidence: {len(run.evidence)} | Links: {len(run.evidence_claim_links)}")
    print(f"Hypothesis groups: {len(run.hypothesis_groups)} | Hypotheses: {len(run.hypotheses)}")
    print(f"Experiments: {len(run.experiments)} (proposed, not performed)")
    print("\nFindings and limitations:")
    for finding in run.findings:
        print(f"- {finding}")


if __name__ == "__main__":
    main()
