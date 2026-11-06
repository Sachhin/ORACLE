"""Command-line interface."""
from __future__ import annotations

import argparse
import json

from .models import ResearchMode, ResearchRun
from .literature import LiteratureClient
from .llm import GeminiClaimExtractor
from .comparison import CrossPaperComparator
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
    parser.add_argument("--literature", metavar="QUERY", help="Search scholarly APIs and ingest abstracts")
    parser.add_argument("--limit", type=int, default=10, help="Maximum literature records (1-50)")
    parser.add_argument("--provider", choices=["both", "all", "europepmc", "crossref", "geo"], default="both")
    parser.add_argument("--mailto", default="", help="Optional contact email for Crossref polite pool")
    parser.add_argument("--extract-claims", action="store_true", help="Extract quote-grounded candidates with Gemini")
    parser.add_argument("--gemini-model", default="gemini-2.5-flash", help="Gemini model for claim extraction and comparison")
    parser.add_argument("--compare-papers", action="store_true", help="Compare extracted claims across distinct papers")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    store = ResearchStore(args.db)
    if args.extract_claims and args.literature is None:
        raise SystemExit("--extract-claims requires --literature.")
    if args.literature is not None:
        run = ResearchRun(question=args.literature)
        providers = {"both": ("europepmc", "crossref"), "all": ("europepmc", "crossref", "geo"), "europepmc": ("europepmc",), "crossref": ("crossref",), "geo": ("geo",)}[args.provider]
        client = LiteratureClient(mailto=args.mailto)
        report = client.search(args.literature, limit=args.limit, providers=providers)
        client.ingest(run, report)
        extraction_report = GeminiClaimExtractor(model=args.gemini_model).extract(run) if args.extract_claims else None
        store.save_run(run)
        if args.json:
            print(json.dumps({"run": run.to_dict(), "literature_report": report.__dict__, "claim_extraction_report": (extraction_report.__dict__ if extraction_report else None)}, indent=2, ensure_ascii=False))
            return
        print(f"ORACLE literature run: {run.run_id}")
        print(f"Retrieved: {report.retrieved} | Sources: {report.ingested_sources} | Abstracts: {report.evidence_records} | Candidate statements: {report.candidate_statements}")
        for item in report.records:
            print(f"- {item['title']} ({item.get('year') or 'date unknown'}) — {item.get('provider')}")
            print(f"  DOI: {item.get('doi') or 'not supplied'} | PMID: {item.get('pmid') or 'not supplied'}")
            print(f"  {item.get('url') or 'No landing-page URL'}")
        for warning in report.warnings:
            print(f"WARNING: {warning}")
        print("Extracted sentences are unreviewed candidates, not validated claims.")
        if extraction_report:
            print(f"Gemini: {extraction_report.candidates_created} quote-validated candidates; {extraction_report.candidates_rejected} rejected.")
            print("Gemini candidates remain contextual, zero-weight, and unreviewed.")
        return
    orchestrator = OracleOrchestrator(store)
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
