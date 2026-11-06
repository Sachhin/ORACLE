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
    parser.add_argument("--citation-network", action="store_true",
                        help="Retrieve first-degree reference metadata for DOI-backed sources from Crossref")
    parser.add_argument("--download-geo-series-archive", metavar="GSE_ACCESSION", help="Download the official GSE *_RAW.tar archive")
    parser.add_argument("--extract-geo-archive", metavar="TAR_PATH", help="Safely extract GSM-prefixed regular files from a downloaded GEO tar archive")
    parser.add_argument("--download-geo-samples", action="store_true", help="Download supplementary count files for explicitly selected GSM accessions")
    parser.add_argument("--gsm", action="append", default=[], metavar="GSM_ACCESSION", help="GEO Sample accession for --download-geo-samples; repeat per sample")
    parser.add_argument("--discover-geo-files", action="store_true",
                        help="List supplementary files for GEO Series records; does not download them")
    parser.add_argument("--download-geo-files", action="store_true",
                        help="Discover and download GEO supplementary files within the configured size cap")
    parser.add_argument("--analyze-geo-files", action="store_true",
                        help="Download and parse supported GEO TSV/CSV expression matrices (descriptive only)")
    parser.add_argument("--geo-deseq2", metavar="MATRIX_PATH",
                        help="Run optional DESeq2 negative-binomial analysis on raw integer RNA-seq counts")
    parser.add_argument("--geo-run-id", default="", help="Persist this DESeq2 result into an existing ORACLE research run")
    parser.add_argument("--geo-accession", default="", help="GEO accession for the analyzed count matrix (e.g. GSE12345)")
    parser.add_argument("--rscript", default="Rscript", help="Rscript executable for the optional DESeq2 backend")
    parser.add_argument("--deseq2-timeout", type=int, default=900, help="Maximum DESeq2 runtime in seconds")
    parser.add_argument("--deseq2-fdr", type=float, default=0.05, help="Adjusted p-value threshold for provisional candidate findings")
    parser.add_argument("--geo-contrast", metavar="MATRIX_PATH",
                        help="Run an explicit two-group Welch contrast on declared log2-continuous GEO matrix data")
    parser.add_argument("--geo-group", action="append", default=[], metavar="SAMPLE=GROUP",
                        help="Explicit sample-to-group assignment; repeat once per matrix sample")
    parser.add_argument("--geo-group-a", default="", help="Reference group in the GEO contrast")
    parser.add_argument("--geo-group-b", default="", help="Comparison group in the GEO contrast")
    parser.add_argument("--geo-scale", choices=["log2_continuous"], default="",
                        help="Required declaration of measurement scale; raw counts are not supported")
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
    portfolio_group.add_argument("--show-deseq2", metavar="RUN_ID",
                                 help="Show persisted DESeq2 analyses and provisional candidate findings")
    portfolio_group.add_argument("--show-reviews", metavar="RUN_ID",
                                 help="Show pending and completed evidence-review candidates in a run")
    portfolio_group.add_argument("--show-tasks", metavar="RUN_ID",
                                 help="Show task status, criteria, and evidence links for a run")
    portfolio_group.add_argument("--show-hypotheses", metavar="RUN_ID",
                                 help="Show competing hypotheses and their reviewed evidence links")
    portfolio_group.add_argument("--show-sources", metavar="RUN_ID",
                                 help="Show source provenance and human quality assessments")
    parser.add_argument("--source-action", choices=["review"],
                        help="Record a human reliability assessment for a source")
    parser.add_argument("--source-run", help="Research run containing the source")
    parser.add_argument("--source-id", help="Source ID to review")
    parser.add_argument("--source-score", type=float, help="Human-assessed source reliability (0..1)")
    parser.add_argument("--source-note", default="", help="Rationale for source-quality assessment")
    parser.add_argument("--hypothesis-action", choices=["link", "review"],
                        help="Link source evidence to a hypothesis or record a human status judgement")
    parser.add_argument("--hypothesis-run", help="Research run containing the hypothesis")
    parser.add_argument("--hypothesis-id", help="Hypothesis ID to update")
    parser.add_argument("--hypothesis-evidence-id", help="Source-backed evidence ID to link")
    parser.add_argument("--hypothesis-stance", choices=["supports", "refutes"])
    parser.add_argument("--hypothesis-status", choices=["supported", "weakened", "rejected", "open"])
    parser.add_argument("--hypothesis-note", default="", help="Human review rationale")
    parser.add_argument("--task-action", choices=["start", "complete", "block", "retry"],
                        help="Update a research task lifecycle state")
    parser.add_argument("--task-run", help="Research run containing the task")
    parser.add_argument("--task-id", help="Research task ID to update")
    parser.add_argument("--task-note", default="", help="Completion note or blocked reason")
    parser.add_argument("--task-evidence-ids", default="",
                        help="Comma-separated source-backed evidence IDs required to complete a task")
    parser.add_argument("--review-candidate", metavar="CANDIDATE_ID",
                        help="Accept, reject, or defer one evidence-review candidate")
    parser.add_argument("--review-run", help="Research run containing the evidence-review candidate")
    parser.add_argument("--review-status", choices=["accepted", "rejected", "needs_context"])
    parser.add_argument("--review-note", default="", help="Human rationale for the review decision")
    parser.add_argument("--review-strength", type=float, default=1.0,
                        help="Evidence-link strength to apply on acceptance (0..1)")
    parser.add_argument("--review-deseq2", metavar="RUN_ID", help="Human-review a provisional DESeq2 candidate in a research run")
    parser.add_argument("--deseq2-analysis-id", default="", help="Persisted DESeq2 analysis ID")
    parser.add_argument("--deseq2-feature", default="", help="Exact feature/gene identifier to review")
    parser.add_argument("--deseq2-review-status", choices=["accepted", "rejected", "needs_context"])
    parser.add_argument("--deseq2-review-note", default="", help="Human rationale required for candidate review")
    parser.add_argument("--screen-replication", metavar="RUN_ID", help="Screen a DESeq2 feature across distinct GEO datasets")
    parser.add_argument("--replication-analysis-id", default="", help="Source DESeq2 analysis ID")
    parser.add_argument("--replication-feature", default="", help="Exact gene/feature identifier to compare")
    parser.add_argument("--replication-fdr", type=float, default=0.05, help="Adjusted p-value threshold for the directional consistency screen")
    parser.add_argument("--merge-geo-counts", action="store_true", help="Merge explicitly mapped per-sample GEO raw-count files into one DESeq2 matrix")
    parser.add_argument("--geo-sample-file", action="append", default=[], metavar="SAMPLE=PATH", help="Explicit sample accession/name and local count-file path; repeat per sample")
    parser.add_argument("--count-feature-column", type=int, default=0, help="Zero-based feature identifier column in each sample count file")
    parser.add_argument("--count-value-column", type=int, default=-1, help="Zero-based raw-count column; -1 means last column")
    parser.add_argument("--count-no-header", action="store_true", help="Treat each sample count file as headerless")
    parser.add_argument("--count-delimiter", choices=["auto", "tab", "comma"], default="auto", help="Delimiter used by per-sample count files")
    parser.add_argument("--count-output", default="data/geo/merged_counts.tsv", help="Output matrix path for --merge-geo-counts")
    parser.add_argument("--benchmark-results", default="", help="DESeq2 result JSON/TSV to score against a curated known-positive set")
    parser.add_argument("--benchmark-manifest", default="", help="JSON manifest with dataset_accession, HTTPS reference, and known_positive_features")
    parser.add_argument("--benchmark-fdr", type=float, default=0.05, help="Adjusted p-value threshold for benchmark hit selection")
    parser.add_argument("--benchmark-abs-log2fc", type=float, default=0.0, help="Minimum absolute log2 fold change for benchmark hit selection")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.download_geo_series_archive:
        from .geo_data import GEOSupplementaryClient
        try:
            report = GEOSupplementaryClient().download_series_raw_archive(
                args.download_geo_series_archive,
                max_file_bytes=args.dataset_max_mb * 1_000_000,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            raise SystemExit(f"GEO Series archive download failed: {exc}") from exc
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if args.extract_geo_archive:
        from .geo_data import GEOSupplementaryClient
        try:
            report = GEOSupplementaryClient.extract_raw_archive(args.extract_geo_archive)
        except (OSError, ValueError, RuntimeError) as exc:
            raise SystemExit(f"GEO archive extraction failed: {exc}") from exc
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if args.download_geo_samples:
        from .geo_data import GEOSupplementaryClient
        try:
            report = GEOSupplementaryClient().download_sample_files(
                args.gsm, max_file_bytes=args.dataset_max_mb * 1_000_000
            )
        except (OSError, ValueError, RuntimeError) as exc:
            raise SystemExit(f"GEO sample download failed: {exc}") from exc
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"GSM samples examined: {report['samples_examined']} | "
                  f"files discovered: {report['files_discovered']} | "
                  f"downloaded: {report['files_downloaded']} | "
                  f"skipped by size: {report['files_skipped_size']}")
            for item in report["files"]:
                print(f"{item['accession']} {item['filename']}: {item['status']} "
                      f"{item.get('sha256', '')}")
            for warning in report["warnings"]:
                print("WARNING: " + warning)
        return
    if args.merge_geo_counts:
        sample_files = {}
        for assignment in args.geo_sample_file:
            sample, separator, path = assignment.partition("=")
            if not separator or not sample.strip() or not path.strip() or sample.strip() in sample_files:
                raise SystemExit(f"Invalid or duplicate --geo-sample-file assignment: {assignment!r}")
            sample_files[sample.strip()] = path.strip()
        from .geo_matrix import merge_sample_count_files
        try:
            report = merge_sample_count_files(
                sample_files, args.count_output,
                feature_column=args.count_feature_column,
                count_column=args.count_value_column,
                has_header=not args.count_no_header,
                delimiter=args.count_delimiter,
            )
        except (OSError, ValueError) as exc:
            raise SystemExit(f"GEO count matrix merge failed: {exc}") from exc
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"Created {report['output_path']}: {report['feature_count']} features x "
                  f"{report['sample_count']} samples")
            print(f"Matrix SHA-256: {report['matrix_sha256']}")
            print("Sample groups were not inferred; provide them explicitly to --geo-deseq2.")
            print("Limitations: " + report["limitations"])
        return
    if args.benchmark_results or args.benchmark_manifest:
        if not args.benchmark_results or not args.benchmark_manifest:
            raise SystemExit("--benchmark-results and --benchmark-manifest must be supplied together.")
        from .benchmark import run_benchmark
        try:
            report = run_benchmark(
                args.benchmark_results, args.benchmark_manifest,
                fdr_threshold=args.benchmark_fdr,
                absolute_log2fc_threshold=args.benchmark_abs_log2fc,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Benchmark failed: {exc}") from exc
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"Benchmark: {report['benchmark_type']} | Dataset: {report['dataset_accession']}")
            print(f"Known-positive recovery: {report['recovered_count']}/{report['truth_set_size']} "
                  f"(recall={report['known_positive_recall']})")
            print(f"Curated-set overlap precision: {report['curated_set_overlap_precision']}")
            print(f"Missed tested positives: {report['missed_count']} | Unmatched hits: {report['unmatched_hit_count']} "
                  f"| Untested positives: {report['untested_truth_count']}")
            print("Interpretation: " + report["interpretation"])
        return
    if args.geo_deseq2:
        if not args.geo_group_a or not args.geo_group_b or not args.geo_group:
            raise SystemExit("--geo-deseq2 requires --geo-group for every sample, --geo-group-a, and --geo-group-b.")
        labels = {}
        for assignment in args.geo_group:
            sample, separator, group = assignment.partition("=")
            if not separator or not sample.strip() or not group.strip() or sample.strip() in labels:
                raise SystemExit(f"Invalid or duplicate --geo-group assignment: {assignment!r}")
            labels[sample.strip()] = group.strip()
        from .geo_deseq2 import GEOCountAnalyzer
        try:
            result = GEOCountAnalyzer().analyze(
                args.geo_deseq2, labels, args.geo_group_a, args.geo_group_b,
                rscript=args.rscript, timeout_seconds=args.deseq2_timeout,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            raise SystemExit(f"DESeq2 analysis failed: {exc}") from exc
        if not 0 < args.deseq2_fdr < 1:
            raise SystemExit("--deseq2-fdr must be strictly between 0 and 1.")
        if args.geo_run_id:
            from .models import DifferentialExpressionAnalysisRecord
            store = ResearchStore(args.db)
            run = store.load_run(args.geo_run_id)
            if run is None:
                raise SystemExit(f"Research run not found: {args.geo_run_id}")
            record = DifferentialExpressionAnalysisRecord(
                dataset_accession=args.geo_accession.strip() or "unspecified",
                source_file=str(args.geo_deseq2),
                matrix_sha256=result["matrix_sha256"],
                method=result["method"],
                contrast=result["contrast"],
                sample_groups=result["sample_groups"],
                sample_count=result["sample_count"],
                features_input=result["features_input"],
                software=result["software"],
                results=result["results"],
                limitations=result["limitations"],
                features_returned=result["features_returned"],
                features_with_adjusted_p_value=result["features_with_adjusted_p_value"],
                candidate_findings=[
                    {"feature": item["feature"],
                     "log2_fold_change": item["log2_fold_change"],
                     "p_value": item["p_value"],
                     "p_value_adjusted_bh": item["p_value_adjusted_bh"],
                     "status": "pending_review", "reviewer_note": "", "reviewed_at": ""}
                    for item in result["results"]
                    if item["p_value_adjusted_bh"] is not None
                    and item["p_value_adjusted_bh"] <= args.deseq2_fdr
                    and item["log2_fold_change"] is not None
                ],
            )
            run.differential_expression_analyses.append(record)
            store.save_run(run)
            store.log_event(
                run.run_id, "differential_expression_analysis_saved",
                {"analysis_id": record.analysis_id, "dataset_accession": record.dataset_accession,
                 "matrix_sha256": record.matrix_sha256, "method": record.method},
                event_key=f"differential-expression:{record.analysis_id}",
            )
            result["analysis_id"] = record.analysis_id
            result["persisted_to_run"] = run.run_id
            result["candidate_findings"] = record.candidate_findings
            result["candidate_fdr_threshold"] = args.deseq2_fdr
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Method: {result['method']}")
            print(f"Contrast: {args.geo_group_b} vs {args.geo_group_a}; "
                  f"{result['features_returned']} result rows from {result['features_input']} input features")
            print(f"R {result['software']['r']} | DESeq2 {result['software']['deseq2']}")
            if result.get("analysis_id"):
                print(f"Persisted analysis: {result['analysis_id']} in run {result['persisted_to_run']}")
            else:
                print("Not persisted: pass --geo-run-id to attach this result to an ORACLE run.")
            for item in result["results"][:20]:
                print(f"{item['feature']}: log2FC={item['log2_fold_change']}, "
                      f"p={item['p_value']}, BH-FDR={item['p_value_adjusted_bh']}")
            print("Limitations: " + result["limitations"])
        return
    if args.geo_contrast:
        if not args.geo_scale or not args.geo_group_a or not args.geo_group_b or not args.geo_group:
            raise SystemExit("--geo-contrast requires --geo-scale log2_continuous, --geo-group (for every sample), --geo-group-a, and --geo-group-b.")
        labels = {}
        for assignment in args.geo_group:
            sample, separator, group = assignment.partition("=")
            if not separator or not sample.strip() or not group.strip() or sample.strip() in labels:
                raise SystemExit(f"Invalid or duplicate --geo-group assignment: {assignment!r}")
            labels[sample.strip()] = group.strip()
        from .geo_statistics import GEOContrastAnalyzer
        try:
            result = GEOContrastAnalyzer().analyze(
                args.geo_contrast, labels, args.geo_group_a, args.geo_group_b, args.geo_scale,
            )
        except (OSError, ValueError) as exc:
            raise SystemExit(f"GEO contrast failed: {exc}") from exc
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Method: {result['method']}")
            print(f"Contrast: {args.geo_group_b} minus {args.geo_group_a}; "
                  f"{result['features_tested']} features tested, {result['features_skipped']} skipped")
            for item in result["results"][:20]:
                print(f"{item['feature']}: difference={item['log2_mean_difference_b_minus_a']:.4g}, "
                      f"p={item['p_value']:.4g}, BH-FDR={item['p_value_adjusted_bh']:.4g}")
            print("Limitations: " + result["limitations"])
        return
    store = ResearchStore(args.db)
    if args.screen_replication:
        if not args.replication_analysis_id or not args.replication_feature:
            raise SystemExit("--screen-replication requires --replication-analysis-id and --replication-feature.")
        run = store.load_run(args.screen_replication)
        if run is None:
            raise SystemExit(f"Research run not found: {args.screen_replication}")
        from .replication import screen_independent_datasets
        try:
            report = screen_independent_datasets(
                run.differential_expression_analyses,
                args.replication_analysis_id,
                args.replication_feature,
                args.replication_fdr,
            )
        except ValueError as exc:
            raise SystemExit(f"Replication screen failed: {exc}") from exc
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"Feature: {report['feature']} | Screen: {report['summary']}")
            print(f"Source: {report['source_dataset_accession']} | Direction: {report['source_direction']}")
            if not report["independent_dataset_comparisons"]:
                print("No eligible independent dataset comparisons were available.")
            for item in report["independent_dataset_comparisons"]:
                print(f"- {item['dataset_accession']} | {item['classification']} | "
                      f"log2FC={item['log2_fold_change']} | BH-FDR={item['adjusted_p_value']}")
            print("Interpretation: " + report["interpretation"])
        return
    if args.show_deseq2:
        run = store.load_run(args.show_deseq2)
        if run is None:
            raise SystemExit(f"Research run not found: {args.show_deseq2}")
        analyses = [item.__dict__ for item in run.differential_expression_analyses]
        if args.json:
            print(json.dumps(analyses, indent=2, ensure_ascii=False))
        else:
            if not analyses:
                print("No persisted DESeq2 analyses in this run.")
            for analysis in analyses:
                print(f"Analysis {analysis['analysis_id']} | {analysis['dataset_accession']} | "
                      f"{analysis['contrast'].get('direction', 'contrast')} | {analysis['review_status']}")
                print(f"  Matrix SHA-256: {analysis['matrix_sha256']}")
                print(f"  Software: R {analysis['software'].get('r')} / DESeq2 {analysis['software'].get('deseq2')}")
                if not analysis.get("candidate_findings"):
                    print("  No rows met the configured FDR threshold.")
                for candidate in analysis.get("candidate_findings", []):
                    print(f"  {candidate['feature']}: log2FC={candidate['log2_fold_change']}, "
                          f"BH-FDR={candidate['p_value_adjusted_bh']} | {candidate['status']}")
        return
    if args.review_deseq2:
        if (not args.deseq2_analysis_id or not args.deseq2_feature
                or not args.deseq2_review_status or not args.deseq2_review_note.strip()):
            raise SystemExit("--review-deseq2 requires --deseq2-analysis-id, --deseq2-feature, "
                             "--deseq2-review-status, and --deseq2-review-note.")
        run = store.load_run(args.review_deseq2)
        if run is None:
            raise SystemExit(f"Research run not found: {args.review_deseq2}")
        analysis = next((item for item in run.differential_expression_analyses
                         if item.analysis_id == args.deseq2_analysis_id), None)
        if analysis is None:
            raise SystemExit(f"DESeq2 analysis not found: {args.deseq2_analysis_id}")
        candidate = next((item for item in analysis.candidate_findings
                          if item["feature"] == args.deseq2_feature), None)
        if candidate is None:
            raise SystemExit(f"Candidate feature not found: {args.deseq2_feature}")
        if candidate["status"] != "pending_review":
            raise SystemExit(f"Candidate already reviewed with status {candidate['status']}; no overwrite allowed.")
        from .models import utc_now
        candidate["status"] = args.deseq2_review_status
        candidate["reviewer_note"] = args.deseq2_review_note.strip()
        candidate["reviewed_at"] = utc_now()
        store.save_run(run)
        store.log_event(
            run.run_id, "deseq2_candidate_reviewed",
            {"analysis_id": analysis.analysis_id, "feature": candidate["feature"],
             "status": candidate["status"], "reviewer_note": candidate["reviewer_note"]},
            event_key=f"deseq2-review:{analysis.analysis_id}:{candidate['feature']}",
        )
        if args.json:
            print(json.dumps(candidate, indent=2, ensure_ascii=False))
        else:
            print(f"Candidate {candidate['feature']} marked {candidate['status']}.")
            print("This review does not automatically create or promote a scientific claim.")
        return
    if args.source_action:
        if (not args.source_run or not args.source_id or args.source_score is None
                or not args.source_note.strip()):
            raise SystemExit("--source-action review requires --source-run, --source-id, --source-score, and --source-note.")
        run = store.load_run(args.source_run)
        if run is None:
            raise SystemExit(f"Research run not found: {args.source_run}")
        from .knowledge import KnowledgeBase
        source = KnowledgeBase().review_source_quality(
            run, args.source_id, args.source_score, args.source_note,
        )
        store.save_run(run)
        if args.json:
            print(json.dumps(source.__dict__, indent=2, ensure_ascii=False))
        else:
            print(f"Source {source.source_id}: reliability {source.reliability_score:.2f}")
            print(f"Rationale: {source.reliability_rationale}")
        return
    if args.hypothesis_action:
        if not args.hypothesis_run or not args.hypothesis_id or not args.hypothesis_note.strip():
            raise SystemExit("--hypothesis-action requires --hypothesis-run, --hypothesis-id, and --hypothesis-note.")
        run = store.load_run(args.hypothesis_run)
        if run is None:
            raise SystemExit(f"Research run not found: {args.hypothesis_run}")
        from .knowledge import KnowledgeBase
        from .models import EvidenceStance
        kb = KnowledgeBase()
        if args.hypothesis_action == "link":
            if not args.hypothesis_evidence_id or not args.hypothesis_stance:
                raise SystemExit("hypothesis link requires --hypothesis-evidence-id and --hypothesis-stance.")
            hypothesis = kb.link_hypothesis_evidence(
                run, args.hypothesis_id, args.hypothesis_evidence_id,
                EvidenceStance(args.hypothesis_stance), args.hypothesis_note,
            )
        else:
            if not args.hypothesis_status:
                raise SystemExit("hypothesis review requires --hypothesis-status.")
            hypothesis = kb.review_hypothesis(
                run, args.hypothesis_id, args.hypothesis_status, args.hypothesis_note,
            )
        store.save_run(run)
        if args.json:
            print(json.dumps(hypothesis.__dict__, indent=2, ensure_ascii=False))
        else:
            print(f"Hypothesis {hypothesis.hypothesis_id}: {hypothesis.status.value}")
            print(f"Supporting evidence: {', '.join(hypothesis.supporting_evidence_ids) or 'none'}")
            print(f"Opposing evidence: {', '.join(hypothesis.opposing_evidence_ids) or 'none'}")
            print(f"Review note: {hypothesis.reviewer_note}")
        return
    if args.task_action:
        if not args.task_run or not args.task_id:
            raise SystemExit("--task-action requires --task-run and --task-id.")
        run = store.load_run(args.task_run)
        if run is None:
            raise SystemExit(f"Research run not found: {args.task_run}")
        from .task_manager import TaskManager
        manager = TaskManager()
        if args.task_action == "start":
            task = manager.start(run, args.task_id)
        elif args.task_action == "complete":
            evidence_ids = [item.strip() for item in args.task_evidence_ids.split(",") if item.strip()]
            task = manager.complete(run, args.task_id, evidence_ids, args.task_note)
        elif args.task_action == "block":
            task = manager.block(run, args.task_id, args.task_note)
        else:
            task = manager.retry(run, args.task_id)
        store.save_run(run)
        if args.json:
            print(json.dumps({"run_id": run.run_id, "task": task.__dict__}, indent=2, ensure_ascii=False))
        else:
            print(f"Task {task.task_id}: {task.status} | attempts {task.attempts}")
            if task.blocked_reason:
                print(f"Blocked: {task.blocked_reason}")
            if task.completion_note:
                print(f"Completion: {task.completion_note}")
        return
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
    if (args.portfolio or args.assess_gaps or args.related_to is not None or args.show_reviews
            or args.show_tasks or args.show_hypotheses or args.show_sources):
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
        if args.show_sources:
            run = store.load_run(args.show_sources)
            if run is None:
                raise SystemExit(f"Research run not found: {args.show_sources}")
            items = [source.__dict__ for source in run.sources]
            if args.json:
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                if not items:
                    print("No sources in this run.")
                for item in items:
                    print(f"- {item['source_id']} | reliability {item['reliability_score']:.2f}")
                    print(f"  {item['title']}")
                    print(f"  DOI/PMID/PMCID: {item['doi'] or '-'} / {item['pmid'] or '-'} / {item['pmcid'] or '-'}")
                    print(f"  URL: {item['url']}")
                    print(f"  Assessment: {item['reliability_rationale']}")
            return
        if args.show_hypotheses:
            run = store.load_run(args.show_hypotheses)
            if run is None:
                raise SystemExit(f"Research run not found: {args.show_hypotheses}")
            items = [item.__dict__ for item in run.hypotheses]
            if args.json:
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                if not items:
                    print("No hypotheses in this run.")
                for item in items:
                    status = item["status"].value if hasattr(item["status"], "value") else item["status"]
                    print(f"- {item['hypothesis_id']} | {status}")
                    print(f"  {item['statement']}")
                    print(f"  Supporting evidence: {', '.join(item['supporting_evidence_ids']) or 'none'}")
                    print(f"  Opposing evidence: {', '.join(item['opposing_evidence_ids']) or 'none'}")
                    print(f"  Predictions: {'; '.join(item['predictions'])}")
                    if item['reviewer_note']:
                        print(f"  Review: {item['reviewer_note']}")
            return
        if args.show_tasks:
            run = store.load_run(args.show_tasks)
            if run is None:
                raise SystemExit(f"Research run not found: {args.show_tasks}")
            items = [task.__dict__ for task in run.tasks]
            if args.json:
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                if not items:
                    print("No research tasks in this run.")
                for task in items:
                    print(f"- {task['task_id']} | {task['status']} | {task['name']} | attempts {task['attempts']}")
                    print(f"  Acceptance: {'; '.join(task['acceptance_criteria'])}")
                    print(f"  Evidence IDs: {', '.join(task['evidence_ids']) or 'none'}")
                    if task['blocked_reason']:
                        print(f"  Blocked: {task['blocked_reason']}")
                    if task['completion_note']:
                        print(f"  Completed: {task['completion_note']}")
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
    if (args.full_text or args.discover_geo_files or args.download_geo_files or args.analyze_geo_files or args.citation_network) and args.literature is None and not args.research_literature:
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
        citation_report = None
        if args.citation_network:
            from .citation_network import CrossrefCitationClient
            citation_report = CrossrefCitationClient(mailto=args.mailto).discover(run)
        geo_discovery_report = None
        geo_download_report = None
        geo_analysis_report = None
        if args.discover_geo_files or args.download_geo_files or args.analyze_geo_files:
            from .geo_data import GEOSupplementaryClient
            geo_client = GEOSupplementaryClient()
            geo_discovery_report = geo_client.discover(run)
            if args.download_geo_files or args.analyze_geo_files:
                geo_download_report = geo_client.download(
                    run, max_file_bytes=args.dataset_max_mb * 1_000_000
                )
            if args.analyze_geo_files:
                from .geo_analysis import GEOExpressionAnalyzer
                geo_analysis_report = GEOExpressionAnalyzer().analyze(run)
        extraction_report = GeminiClaimExtractor(model=args.gemini_model).extract(run) if args.extract_claims else None
        comparison_report = CrossPaperComparator(model=args.gemini_model).compare(run) if args.compare_papers else None
        from .evidence_review import GeminiEvidenceReviewer
        evidence_review_report = GeminiEvidenceReviewer(model=args.gemini_model).review(run) if args.review_evidence else None
        store.save_run(run)
        if args.json:
            print(json.dumps({"run": run.to_dict(), "literature_report": report.__dict__, "claim_extraction_report": (extraction_report.__dict__ if extraction_report else None), "comparison_report": (comparison_report.__dict__ if comparison_report else None), "evidence_review_report": (evidence_review_report.__dict__ if evidence_review_report else None), "full_text_report": (full_text_report.__dict__ if full_text_report else None), "geo_discovery_report": (geo_discovery_report.__dict__ if geo_discovery_report else None), "geo_download_report": (geo_download_report.__dict__ if geo_download_report else None), "geo_analysis_report": (geo_analysis_report.__dict__ if geo_analysis_report else None), "citation_report": (citation_report.__dict__ if citation_report else None)}, indent=2, ensure_ascii=False))
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
        if geo_analysis_report:
            print(f"GEO matrix analysis: {geo_analysis_report.files_analyzed} parsed; {geo_analysis_report.files_skipped} skipped; {geo_analysis_report.samples_flagged} sample columns flagged by QC (none automatically removed).")
            for warning in geo_analysis_report.warnings:
                print(f"WARNING: {warning}")
        if citation_report:
            print(f"Citation network: {citation_report.links_created} first-degree references discovered.")
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
        geo_files_enabled=args.discover_geo_files or args.download_geo_files or args.analyze_geo_files,
        geo_download_enabled=args.download_geo_files or args.analyze_geo_files,
        geo_analysis_enabled=args.analyze_geo_files,
        geo_max_file_bytes=args.dataset_max_mb * 1_000_000,
        citation_network_enabled=args.citation_network,
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
