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
    parser.add_argument("--literature", metavar="QUERY", help="Run a standalone scholarly literature search")
    parser.add_argument("--research-literature", action="store_true",
                        help="Retrieve scholarly literature as the evidence input to a full research cycle")
    parser.add_argument("--limit", type=int, default=10, help="Maximum literature records (1-50)")
    parser.add_argument("--provider", choices=["both", "all", "europepmc", "crossref", "geo"], default="both")
    parser.add_argument("--mailto", default="", help="Optional contact email for Crossref polite pool")
    parser.add_argument("--extract-claims", action="store_true", help="Extract quote-grounded candidates with Gemini")
    parser.add_argument("--gemini-model", default="gemini-2.5-flash", help="Gemini model for optional claim extraction, comparison, or research agents")
    parser.add_argument("--agent-provider", choices=["deterministic", "gemini"], default="deterministic",
                        help="Research-agent backend; deterministic remains the safe default")
    parser.add_argument("--compare-papers", action="store_true", help="Compare extracted claims across distinct papers")
    parser.add_argument("--review-evidence", action="store_true",
                        help="Ask Gemini for quote-grounded support/refute/contextual suggestions; requires human review")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    store = ResearchStore(args.db)
    if args.research_literature and args.literature is not None:
        raise SystemExit("Use either --literature or --research-literature, not both.")
    if (args.extract_claims or args.compare_papers) and args.literature is None and not args.research_literature:
        raise SystemExit("--extract-claims and --compare-papers require --literature or --research-literature.")
    if (args.compare_papers or args.review_evidence) and not args.extract_claims:
        raise SystemExit("--compare-papers and --review-evidence require --extract-claims.")
    if args.literature is not None:
        run = ResearchRun(question=args.literature)
        providers = {"both": ("europepmc", "crossref"), "all": ("europepmc", "crossref", "geo"), "europepmc": ("europepmc",), "crossref": ("crossref",), "geo": ("geo",)}[args.provider]
        client = LiteratureClient(mailto=args.mailto)
        report = client.search(args.literature, limit=args.limit, providers=providers)
        client.ingest(run, report)
        extraction_report = GeminiClaimExtractor(model=args.gemini_model).extract(run) if args.extract_claims else None
        comparison_report = CrossPaperComparator(model=args.gemini_model).compare(run) if args.compare_papers else None
        from .evidence_review import GeminiEvidenceReviewer
        evidence_review_report = GeminiEvidenceReviewer(model=args.gemini_model).review(run) if args.review_evidence else None
        store.save_run(run)
        if args.json:
            print(json.dumps({"run": run.to_dict(), "literature_report": report.__dict__, "claim_extraction_report": (extraction_report.__dict__ if extraction_report else None), "comparison_report": (comparison_report.__dict__ if comparison_report else None), "evidence_review_report": (evidence_review_report.__dict__ if evidence_review_report else None)}, indent=2, ensure_ascii=False))
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
        if comparison_report:
            print(f"Cross-paper comparison: {comparison_report.comparisons_created} review candidates from {comparison_report.pairs_submitted} pairs; {comparison_report.comparisons_rejected} rejected.")
            print("Comparisons are pending review; no claim status or evidence stance was changed.")
        if evidence_review_report:
            print(f"Evidence review: {evidence_review_report.candidates_created} quote-grounded suggestions; {evidence_review_report.candidates_rejected} rejected.")
            print("Evidence review suggestions are pending human review; no evidence stance or weight was changed.")
        return
    agent_suite = None
    if args.agent_provider == "gemini":
        from .model_agents import GeminiAgentSuite
        agent_suite = GeminiAgentSuite(model=args.gemini_model)
    providers = {"both": ("europepmc", "crossref"), "all": ("europepmc", "crossref", "geo"), "europepmc": ("europepmc",), "crossref": ("crossref",), "geo": ("geo",)}[args.provider]
    orchestrator = OracleOrchestrator(
        store, agent_suite=agent_suite,
        literature_enabled=args.research_literature,
        literature_providers=providers,
        literature_limit=args.limit,
        literature_mailto=args.mailto,
        extract_literature_claims=args.extract_claims,
        compare_literature_papers=args.compare_papers,
        review_literature_evidence=args.review_evidence,
        gemini_model=args.gemini_model,
    )
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
