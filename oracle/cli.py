"""Command-line interface."""
from __future__ import annotations

import argparse
import json

from .models import ExperimentStatus, ResearchMode, ResearchRun
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
    parser.add_argument("--full-text", action="store_true",
                        help="Retrieve licence-eligible Europe PMC open-access full text for PMCID records")
    parser.add_argument("--discover-geo-files", action="store_true",
                        help="List supplementary files for GEO Series records; does not download them")
    parser.add_argument("--download-geo-files", action="store_true",
                        help="Discover and download GEO supplementary files within the configured size cap")
    parser.add_argument("--dataset-max-mb", type=int, default=50,
                        help="Maximum size of each GEO supplementary download in MB (1-1000)")
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
    parser.add_argument("--experiment-action", choices=["simulate", "perform", "evaluate"],
                        help="Record a simulation, a real performed experiment, or its evaluation")
    parser.add_argument("--experiment-run", help="Research run ID containing the experiment")
    parser.add_argument("--experiment-id", help="Experiment ID to update")
    parser.add_argument("--simulation-engine", default="", help="Name/version of the simulation engine")
    parser.add_argument("--simulation-limitations", default="", help="Limitations of the simulation")
    parser.add_argument("--execution-method", default="", help="Method/protocol used for the real experiment")
    parser.add_argument("--operator", default="", help="Person or lab recording the real experiment")
    parser.add_argument("--experiment-results", default="", help="Recorded experiment or simulation results")
    parser.add_argument("--evaluation-note", default="", help="Human evaluation note")
    portfolio_group = parser.add_mutually_exclusive_group()
    portfolio_group.add_argument("--portfolio", action="store_true",
                                 help="List saved research runs and their heuristic knowledge-gap scores")
    portfolio_group.add_argument("--assess-gaps", metavar="RUN_ID",
                                 help="Explain the knowledge gaps recorded for a saved run")
    portfolio_group.add_argument("--related-to", metavar="QUESTION",
                                 help="Find prior runs with lexically related research questions")
    portfolio_group.add_argument("--show-reviews", metavar="RUN_ID",
                                 help="Show pending and completed evidence-review candidates in a run")
    parser.add_argument("--review-candidate", metavar="CANDIDATE_ID",
                        help="Accept, reject, or defer one evidence-review candidate")
    parser.add_argument("--review-run", help="Research run containing the evidence-review candidate")
    parser.add_argument("--review-status", choices=["accepted", "rejected", "needs_context"])
    parser.add_argument("--review-note", default="", help="Human rationale for the review decision")
    parser.add_argument("--review-strength", type=float, default=1.0,
                        help="Evidence-link strength to apply on acceptance (0..1)")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    store = ResearchStore(args.db)
    if args.review_candidate:
        if not args.review_run or not args.review_status or not args.review_note.strip():
            raise SystemExit("--review-candidate requires --review-run, --review-status, and --review-note.")
        run = store.load_run(args.review_run)
        if run is None:
            raise SystemExit(f"Research run not found: {args.review_run}")
        from .knowledge import KnowledgeBase
        candidate = KnowledgeBase().review_evidence_candidate(
            run, args.review_candidate, args.review_status, args.review_note,
            strength=args.review_strength,
        )
        store.save_run(run)
        if args.json:
            print(json.dumps(candidate.__dict__, indent=2, ensure_ascii=False))
        else:
            print(f"Evidence review {candidate.candidate_id}: {candidate.status}")
            print(f"Proposed stance: {candidate.proposed_stance.value}")
            print(f"Reviewer note: {candidate.reviewer_note}")
        return
    if args.experiment_action:
        if not args.experiment_run or not args.experiment_id:
            raise SystemExit("--experiment-action requires --experiment-run and --experiment-id.")
        run = store.load_run(args.experiment_run)
        if run is None:
            raise SystemExit(f"Research run not found: {args.experiment_run}")
        from .experiment_manager import ExperimentManager
        manager = ExperimentManager()
        if args.experiment_action == "simulate":
            if not args.simulation_engine or not args.experiment_results or not args.simulation_limitations:
                raise SystemExit("simulate requires --simulation-engine, --experiment-results, and --simulation-limitations.")
            experiment = manager.record_simulation(
                run, args.experiment_id, args.simulation_engine,
                args.experiment_results, args.simulation_limitations,
            )
        elif args.experiment_action == "perform":
            if not args.execution_method or not args.operator or not args.experiment_results:
                raise SystemExit("perform requires --execution-method, --operator, and --experiment-results.")
            experiment = manager.record_performed(
                run, args.experiment_id, args.execution_method, args.operator,
                args.experiment_results,
            )
        else:
            if not args.evaluation_note:
                raise SystemExit("evaluate requires --evaluation-note.")
            experiment = manager.mark_evaluated(run, args.experiment_id, args.evaluation_note)
        store.save_run(run)
        payload = {"run_id": run.run_id, "experiment": experiment.__dict__}
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"Experiment {experiment.experiment_id}: {experiment.status.value} ({experiment.execution_kind})")
            print(experiment.limitations)
        return
    if args.portfolio or args.assess_gaps or args.related_to is not None or args.show_reviews:
        from dataclasses import asdict
        from .portfolio import ResearchPortfolio
        portfolio = ResearchPortfolio(store)
        if args.portfolio:
            entries = portfolio.list_entries(limit=args.limit)
            if args.json:
                print(json.dumps(entries, indent=2, ensure_ascii=False))
            else:
                print("Saved ORACLE research runs")
                for item in entries:
                    print(f"- {item['run_id']} | {item['status']} | gap score {item['knowledge_gap_score']}/100")
                    print(f"  {item['question']}")
                    print(f"  Sources: {item['sources']} | Evidence: {item['evidence']} | Claims: {item['claims']} | Hypotheses: {item['hypotheses']}")
            return
        if args.show_reviews:
            run = store.load_run(args.show_reviews)
            if run is None:
                raise SystemExit(f"Research run not found: {args.show_reviews}")
            claims = {item.claim_id: item for item in run.claims}
            evidence = {item.evidence_id: item for item in run.evidence}
            sources = {item.source_id: item for item in run.sources}
            items = []
            for candidate in run.evidence_review_candidates:
                claim = claims.get(candidate.claim_id)
                item = evidence.get(candidate.evidence_id)
                source = sources.get(item.source_id) if item else None
                items.append({
                    **candidate.__dict__,
                    "claim": claim.statement if claim else "[missing claim]",
                    "evidence": item.claim if item else "[missing evidence]",
                    "source_title": source.title if source else "[missing source]",
                    "source_url": source.url if source else "",
                })
            if args.json:
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                if not items:
                    print("No evidence-review candidates in this run.")
                for item in items:
                    print(f"- {item['candidate_id']} | {item['status']} | proposed: {item['proposed_stance']}")
                    print(f"  Claim: {item['claim']}")
                    print(f"  Source: {item['source_title']} | {item['source_url']}")
                    print(f"  Exact quote: {item['source_quote']}")
                    print(f"  Rationale: {item['rationale']}")
            return
        if args.assess_gaps:
            assessment = asdict(portfolio.assess(args.assess_gaps))
            if args.json:
                print(json.dumps(assessment, indent=2, ensure_ascii=False))
            else:
                print(f"Knowledge-gap score: {assessment['score']}/100 (heuristic, not scientific confidence)")
                print(f"Question: {assessment['question']}")
                for name, value in assessment["criteria"].items():
                    print(f"- {name}: {value:.2f}")
                for gap in assessment["gaps"]:
                    print(f"  GAP: {gap}")
            return
        related = portfolio.related_runs(args.related_to, limit=args.limit)
        if args.json:
            print(json.dumps(related, indent=2, ensure_ascii=False))
        else:
            print("Prior runs with lexically related questions (not semantic discovery):")
            for item in related:
                print(f"- {item['run_id']} | similarity {item['lexical_similarity']:.3f} | {item['status']}")
                print(f"  {item['question']}")
        return
    if args.research_literature and args.literature is not None:
        raise SystemExit("Use either --literature or --research-literature, not both.")
    if (args.full_text or args.discover_geo_files or args.download_geo_files) and args.literature is None and not args.research_literature:
        raise SystemExit("--full-text and GEO file options require --literature or --research-literature.")
    if not 1 <= args.dataset_max_mb <= 1000:
        raise SystemExit("--dataset-max-mb must be between 1 and 1000.")
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
        from .fulltext import OpenAccessFullTextClient
        full_text_report = OpenAccessFullTextClient().ingest(run) if args.full_text else None
        geo_discovery_report = None
        geo_download_report = None
        if args.discover_geo_files or args.download_geo_files:
            from .geo_data import GEOSupplementaryClient
            geo_client = GEOSupplementaryClient()
            geo_discovery_report = geo_client.discover(run)
            if args.download_geo_files:
                geo_download_report = geo_client.download(
                    run, max_file_bytes=args.dataset_max_mb * 1_000_000
                )
        extraction_report = GeminiClaimExtractor(model=args.gemini_model).extract(run) if args.extract_claims else None
        comparison_report = CrossPaperComparator(model=args.gemini_model).compare(run) if args.compare_papers else None
        from .evidence_review import GeminiEvidenceReviewer
        evidence_review_report = GeminiEvidenceReviewer(model=args.gemini_model).review(run) if args.review_evidence else None
        store.save_run(run)
        if args.json:
            print(json.dumps({"run": run.to_dict(), "literature_report": report.__dict__, "claim_extraction_report": (extraction_report.__dict__ if extraction_report else None), "comparison_report": (comparison_report.__dict__ if comparison_report else None), "evidence_review_report": (evidence_review_report.__dict__ if evidence_review_report else None), "full_text_report": (full_text_report.__dict__ if full_text_report else None), "geo_discovery_report": (geo_discovery_report.__dict__ if geo_discovery_report else None), "geo_download_report": (geo_download_report.__dict__ if geo_download_report else None)}, indent=2, ensure_ascii=False))
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
        if full_text_report:
            print(f"Open-access full text: {full_text_report.full_text_records} retrieved; {full_text_report.skipped_license} skipped by licence; {full_text_report.skipped_no_pmcid} without PMCID.")
        if geo_discovery_report:
            print(f"GEO files: {geo_discovery_report.files_discovered} supplementary file records discovered.")
        if geo_download_report:
            print(f"GEO downloads: {geo_download_report.files_downloaded} downloaded; {geo_download_report.files_skipped_size} skipped by size cap.")
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
        full_text_enabled=args.full_text,
        geo_files_enabled=args.discover_geo_files or args.download_geo_files,
        geo_download_enabled=args.download_geo_files,
        geo_max_file_bytes=args.dataset_max_mb * 1_000_000,
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
    experiment_counts = {status.value: sum(1 for item in run.experiments if item.status == status)
                         for status in ExperimentStatus}
    print("Experiments: " + " | ".join(f"{name}: {count}" for name, count in experiment_counts.items()))
    print("\nFindings and limitations:")
    for finding in run.findings:
        print(f"- {finding}")


if __name__ == "__main__":
    main()
