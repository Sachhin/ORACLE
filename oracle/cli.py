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
    parser.add_argument("--list-resources", action="store_true",
                        help="List registered scientific resources and connector implementation status")
    parser.add_argument("--resource-domain", default="all",
                        help="Filter --list-resources by domain (or all)")
    parser.add_argument("--domain", default="auto",
                        choices=["auto", "biology_medicine", "physics_astronomy",
                                 "chemistry_materials", "computer_science_ai",
                                 "earth_environment", "mathematics_statistics",
                                 "social_behavioral", "engineering", "general_science"],
                        help="Research domain specialist; auto uses transparent keyword routing")
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
                        help="Retrieve reference metadata for DOI-backed sources from Crossref")
    parser.add_argument("--reference-depth", type=int, default=1,
                        help="Crossref outgoing-reference expansion depth (1-5; default 1)")
    parser.add_argument("--reference-nodes", type=int, default=100,
                        help="Maximum metadata-only external reference nodes to add (1-250)")
    parser.add_argument("--incoming-citations", action="store_true",
                        help="Find works that cite DOI-backed sources using the OpenAlex API")
    parser.add_argument("--incoming-citation-depth", type=int, default=1,
                        help="OpenAlex incoming-citation expansion depth (1-5; default 1)")
    parser.add_argument("--incoming-citation-nodes", type=int, default=100,
                        help="Maximum metadata-only external citation nodes to add (1-250)")
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
    parser.add_argument("--normalize-geo-matrix", metavar="MATRIX_PATH",
                        help="Normalize a GEO matrix into a separate output file")
    parser.add_argument("--normalization-method", choices=["quantile", "quantile-row-median", "cpm", "log2-cpm", "tmm-cpm", "tmm-log2-cpm"], default="",
                        help="quantile for continuous microarray-like data; cpm/log2-cpm for raw integer counts")
    parser.add_argument("--normalization-output", default="",
                        help="Required output TSV path; raw input is never overwritten")
    parser.add_argument("--verify-normalization", action="store_true",
                        help="Repeat the normalization in the same runtime and compare output SHA-256")
    parser.add_argument("--normalization-prior-count", type=float, default=0.5,
                        help="Positive log2-CPM prior count (default 0.5)")
    parser.add_argument("--geo-affymetrix-rma", action="append", default=[], metavar="CEL_PATH",
                        help="Add one CEL file to an explicit Affymetrix RMA run; repeat per sample")
    parser.add_argument("--affy-backend", choices=["affy", "oligo"], default="",
                        help="Required explicit Bioconductor package family for CEL inputs")
    parser.add_argument("--affy-platform", default="",
                        help="Optional expected Bioconductor array-design/CDF package identifier; mismatch aborts RMA")
    parser.add_argument("--affy-output", default="", help="Required output TSV path for --geo-affymetrix-rma")
    parser.add_argument("--affy-timeout", type=int, default=1800, help="Maximum Affymetrix RMA runtime in seconds")
    parser.add_argument("--geo-voom", metavar="MATRIX_PATH",
                        help="Run optional edgeR TMM + limma-voom analysis on raw integer counts")
    parser.add_argument("--voom-timeout", type=int, default=900, help="Maximum limma-voom runtime in seconds")
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
    parser.add_argument("--geo-covariates", default="",
                        help="JSON file mapping categorical covariates to sample labels for DESeq2, e.g. {batch:{GSM1:batch1}}")
    parser.add_argument("--geo-scale", choices=["log2_continuous"], default="",
                        help="Required declaration of measurement scale; raw counts are not supported")
    parser.add_argument("--dataset-max-mb", type=int, default=50,
                        help="Maximum size of each GEO supplementary download in MB (1-1000)")
    parser.add_argument("--limit", type=int, default=10, help="Maximum literature records (1-50)")
    parser.add_argument("--provider", choices=["both", "all", "biology", "europepmc", "crossref", "geo", "arxiv", "pubchem"], default="both")
    parser.add_argument("--mailto", default="", help="Optional contact email for Crossref polite pool")
    parser.add_argument("--extract-claims", action="store_true", help="Extract quote-grounded candidates with Gemini")
    parser.add_argument("--gemini-model", default="gemini-2.5-flash", help="Gemini model for optional claim extraction, comparison, or research agents")
    parser.add_argument("--agent-provider", choices=["deterministic", "gemini", "auto"], default="deterministic",
                        help="Research-agent backend; auto enables configured provider failover")
    parser.add_argument("--compare-papers", action="store_true", help="Compare extracted claims across distinct papers")
    parser.add_argument("--review-evidence", action="store_true",
                        help="Ask Gemini for quote-grounded support/refute/contextual suggestions; requires human review")
    parser.add_argument("--propose-protocol", metavar="RUN_ID",
                        help="Add a domain-specific proposed experiment protocol to a saved run")
    parser.add_argument("--protocol-domain",
                        choices=["plant_biology", "molecular_biology", "cell_biology", "computational_biology"],
                        default="")
    parser.add_argument("--protocol-hypothesis-id", default="",
                        help="Optional hypothesis ID to target with the protocol")
    parser.add_argument("--experiment-action", choices=["simulate", "perform", "evaluate", "review"],
                        help="Record a simulation, a real performed experiment, or its evaluation")
    parser.add_argument("--experiment-run", help="Research run ID containing the experiment")
    parser.add_argument("--experiment-id", help="Experiment ID to update")
    parser.add_argument("--simulation-engine", default="", help="Name/version of the simulation engine")
    parser.add_argument("--simulation-limitations", default="", help="Limitations of the simulation")
    parser.add_argument("--execution-method", default="", help="Method/protocol used for the real experiment")
    parser.add_argument("--operator", default="", help="Person or lab recording the real experiment")
    parser.add_argument("--experiment-results", default="", help="Recorded experiment or simulation results")
    parser.add_argument("--evaluation-note", default="", help="Human evaluation note")
    parser.add_argument("--execution-review-status", choices=["accepted", "rejected", "needs_context"])
    parser.add_argument("--execution-reviewer", default="", help="Independent reviewer identity for a performed experiment")
    parser.add_argument("--execution-review-note", default="", help="Independent review rationale for performed execution")
    portfolio_group = parser.add_mutually_exclusive_group()
    portfolio_group.add_argument("--portfolio", action="store_true",
                                 help="List saved research runs and their heuristic knowledge-gap scores")
    portfolio_group.add_argument("--assess-gaps", metavar="RUN_ID",
                                 help="Explain the knowledge gaps recorded for a saved run")
    portfolio_group.add_argument("--related-to", metavar="QUESTION",
                                 help="Find prior runs with lexically related research questions")
    portfolio_group.add_argument("--cross-run-candidates", metavar="RUN_ID",
                                 help="Find source-backed claim pairs across runs for human review")
    portfolio_group.add_argument("--show-cross-run-links", nargs="?", const="",
                                 help="Show persisted cross-run claim links; optionally filter by run ID")
    portfolio_group.add_argument("--rank-citation-graph", metavar="RUN_ID",
                                 help="Rank source records in a DOI-resolved citation graph")
    portfolio_group.add_argument("--traverse-citation-graph", metavar="RUN_ID",
                                 help="Trace bounded multi-hop citation paths within a saved run")
    parser.add_argument("--citation-start-source", default="",
                        help="Source ID from which citation traversal starts")
    parser.add_argument("--citation-direction", choices=["outgoing", "incoming", "both"], default="both")
    parser.add_argument("--citation-depth", type=int, default=3)
    portfolio_group.add_argument("--show-answer-reviews", metavar="RUN_ID",
                                 help="Show human-scored answer reviews and rubric averages")
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
    portfolio_group.add_argument("--show-connections", metavar="RUN_ID",
                                 help="Show source-linked cross-domain connection proposals")
    parser.add_argument("--link-cross-run-claims", metavar="RUN_A_ID",
                        help="Create a pending link between source-backed claims from two runs")
    parser.add_argument("--other-run-id", default="", help="Second run for cross-run claim linking")
    parser.add_argument("--claim-a-id", default="", help="Claim ID in the first run")
    parser.add_argument("--claim-b-id", default="", help="Claim ID in the second run")
    parser.add_argument("--cross-run-relation", choices=["same_topic", "supports", "contradicts", "contextualizes"], default="same_topic")
    parser.add_argument("--cross-run-rationale", default="", help="Rationale for the proposed cross-run link")
    parser.add_argument("--review-cross-run-link", metavar="LINK_ID", help="Human-review a persisted cross-run claim link")
    parser.add_argument("--cross-run-status", choices=["accepted", "rejected", "needs_context"])
    parser.add_argument("--cross-run-note", default="", help="Human review rationale for a cross-run link")
    parser.add_argument("--review-connection", metavar="RUN_ID",
                        help="Record a human review decision for a cross-domain connection")
    parser.add_argument("--connection-id", default="", help="Cross-domain connection ID")
    parser.add_argument("--connection-status", choices=["accepted", "rejected", "needs_context"])
    parser.add_argument("--connection-note", default="", help="Human rationale for the connection review")
    parser.add_argument("--score-answer", metavar="RUN_ID", help="Record a human rubric review of an answer for a saved run")
    parser.add_argument("--answer-file", default="", help="UTF-8 file containing the answer text to score")
    parser.add_argument("--answer-reviewer", default="", help="Human answer reviewer identity")
    parser.add_argument("--answer-review-note", default="", help="Reviewer rationale and caveats")
    parser.add_argument("--answer-source-ids", default="", help="Comma-separated source IDs checked during review")
    parser.add_argument("--score-accuracy", type=int)
    parser.add_argument("--score-traceability", type=int)
    parser.add_argument("--score-uncertainty", type=int)
    parser.add_argument("--score-reasoning", type=int)
    parser.add_argument("--score-completeness", type=int)
    parser.add_argument("--review-claim", metavar="RUN_ID", help="Human-review a scientific claim in a saved run")
    parser.add_argument("--claim-id", default="", help="Claim ID to review")
    parser.add_argument("--claim-status", choices=["supported", "weakened", "rejected", "open"])
    parser.add_argument("--claim-impact-level", choices=["normal", "high", "critical"], default="normal")
    parser.add_argument("--claim-reviewer", default="", help="Human reviewer identity")
    parser.add_argument("--claim-note", default="", help="Human rationale for claim review")
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
    parser.add_argument("--compare-tmm-edger", default="", help="Compare ORACLE TMM factors with edgeR on the same raw-count matrix")
    parser.add_argument("--orthogonal-missingness-benchmark", action="store_true", help="Evaluate an imputed matrix against paired orthogonal-assay measurements at genuinely missing cells")
    parser.add_argument("--missingness-observed", default="", help="Original assay TSV containing real missing values")
    parser.add_argument("--missingness-orthogonal", default="", help="Paired orthogonal assay TSV, e.g. DIA")
    parser.add_argument("--missingness-imputed", default="", help="ORACLE-imputed matrix TSV")
    parser.add_argument("--missingness-labels", default="", help="Optional TSV with sample_id and independent outcome labels; omit for reconstruction-only scoring")
    parser.add_argument("--missingness-outcome-column", default="", help="Two-class biological outcome column in labels TSV")
    parser.add_argument("--missingness-top-k", type=int, default=20, help="Top absolute outcome effects to compare (default 20)")
    parser.add_argument("--imputation-benchmark", default="", help="Run a reproducible MCAR/MAR/MNAR row-median imputation stress test on a complete matrix")
    parser.add_argument("--imputation-holdout", default="", help="Compare row/column/global median methods on masked observed cells of a complete matrix")
    parser.add_argument("--imputation-de-bias", default="", help="Evaluate downstream Welch/BH differential-expression sensitivity to row-median imputation")
    parser.add_argument("--imputation-group-a", default="", help="Reference group for --imputation-de-bias")
    parser.add_argument("--imputation-group-b", default="", help="Comparison group for --imputation-de-bias")
    parser.add_argument("--imputation-mechanism", choices=["MCAR", "MAR", "MNAR"], default="MCAR")
    parser.add_argument("--imputation-missing-fraction", type=float, default=0.1)
    parser.add_argument("--imputation-replicates", type=int, default=20)
    parser.add_argument("--imputation-seed", type=int, default=1729)
    parser.add_argument("--scifact-benchmark", action="store_true", help="Score frozen model predictions against the external SciFact labelled benchmark")
    parser.add_argument("--scifact-claims", default="", help="SciFact claims_dev.jsonl or claims_train.jsonl")
    parser.add_argument("--scifact-corpus", default="", help="SciFact corpus.jsonl")
    parser.add_argument("--scifact-predictions", default="", help="Model predictions in official SciFact JSONL format")
    parser.add_argument("--scifact-split", choices=["train", "dev"], default="dev")
    parser.add_argument("--evidence-benchmark", default="", help="Score predictions against a human-adjudicated evidence benchmark JSON file")
    parser.add_argument("--paired-answer-benchmark", default="", help="Compare paired human rubric scores for a candidate model and deterministic baseline")
    parser.add_argument("--benchmark-results", default="", help="DESeq2 result JSON/TSV to score against a curated known-positive set")
    parser.add_argument("--benchmark-manifest", default="", help="JSON manifest with dataset_accession, HTTPS reference, and known_positive_features")
    parser.add_argument("--benchmark-fdr", type=float, default=0.05, help="Adjusted p-value threshold for benchmark hit selection")
    parser.add_argument("--benchmark-abs-log2fc", type=float, default=0.0, help="Minimum absolute log2 fold change for benchmark hit selection")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.list_resources:
        from .resource_manager import ResourceManager
        try:
            resources = ResourceManager.list_resources(args.resource_domain)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        if args.json:
            print(json.dumps(resources, indent=2, ensure_ascii=False))
        else:
            for item in resources:
                print(f"- {item['key']} | {item['status']} | {item['name']}")
                print(f"  API: {item['api_url']} | Auth: {item['authentication']}")
                print(f"  Capabilities: {', '.join(item['capabilities']) or 'metadata only'}")
        return
    if args.paired_answer_benchmark:
        from .model_comparison import run_paired_answer_benchmark
        try:
            report = run_paired_answer_benchmark(args.paired_answer_benchmark)
        except (OSError, ValueError, RuntimeError) as exc:
            raise SystemExit(f"Paired answer benchmark failed: {exc}") from exc
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if args.scifact_benchmark:
        required = [args.scifact_claims, args.scifact_corpus, args.scifact_predictions]
        if not all(required):
            raise SystemExit("--scifact-benchmark requires --scifact-claims, --scifact-corpus, and --scifact-predictions.")
        from .scifact_benchmark import evaluate_scifact
        try:
            report = evaluate_scifact(
                args.scifact_claims, args.scifact_corpus,
                args.scifact_predictions, split=args.scifact_split,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            raise SystemExit(f"SciFact benchmark failed: {exc}") from exc
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if args.evidence_benchmark:
        from .evidence_benchmark import run_evidence_benchmark
        try:
            report = run_evidence_benchmark(args.evidence_benchmark)
        except (OSError, ValueError, RuntimeError) as exc:
            raise SystemExit(f"Evidence benchmark failed: {exc}") from exc
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if args.compare_tmm_edger:
        from .geo_reference import compare_tmm_to_edger
        try:
            report = compare_tmm_to_edger(args.compare_tmm_edger, rscript=args.rscript)
        except (OSError, ValueError, RuntimeError) as exc:
            raise SystemExit(f"TMM/edgeR reference comparison failed: {exc}") from exc
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if args.orthogonal_missingness_benchmark:
        required = [args.missingness_observed, args.missingness_orthogonal,
                    args.missingness_imputed]
        if not all(required):
            raise SystemExit("--orthogonal-missingness-benchmark requires --missingness-observed, --missingness-orthogonal, and --missingness-imputed.")
        if bool(args.missingness_labels) != bool(args.missingness_outcome_column):
            raise SystemExit("--missingness-labels and --missingness-outcome-column must be supplied together; omit both for reconstruction-only scoring.")
        from .missingness_validation import evaluate_orthogonal_missingness
        try:
            report = evaluate_orthogonal_missingness(
                args.missingness_observed, args.missingness_orthogonal,
                args.missingness_imputed, args.missingness_labels or None,
                outcome_column=args.missingness_outcome_column or None,
                top_k=args.missingness_top_k,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            raise SystemExit(f"Orthogonal missingness benchmark failed: {exc}") from exc
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if args.imputation_benchmark:
        from .geo_reference import evaluate_row_median_imputation
        try:
            report = evaluate_row_median_imputation(
                args.imputation_benchmark,
                missing_fraction=args.imputation_missing_fraction,
                replicates=args.imputation_replicates, seed=args.imputation_seed,
                mechanism=args.imputation_mechanism,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            raise SystemExit(f"Imputation benchmark failed: {exc}") from exc
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    if args.imputation_holdout:
        from .geo_reference import evaluate_imputation_holdout
        try:
            report = evaluate_imputation_holdout(
                args.imputation_holdout,
                missing_fraction=args.imputation_missing_fraction,
                replicates=args.imputation_replicates, seed=args.imputation_seed,
                mechanism=args.imputation_mechanism,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            raise SystemExit(f"Imputation holdout comparison failed: {exc}") from exc
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if args.imputation_de_bias:
        from .geo_reference import evaluate_imputation_downstream_bias
        labels = {}
        for item in args.geo_group:
            if "=" not in item:
                raise SystemExit("--geo-group must use SAMPLE=GROUP.")
            sample, group = item.split("=", 1)
            if not sample or not group or sample in labels:
                raise SystemExit("--geo-group requires unique non-empty SAMPLE=GROUP entries.")
            labels[sample] = group
        if not args.imputation_group_a or not args.imputation_group_b:
            raise SystemExit("--imputation-de-bias requires --imputation-group-a and --imputation-group-b.")
        try:
            report = evaluate_imputation_downstream_bias(
                args.imputation_de_bias, labels, group_a=args.imputation_group_a,
                group_b=args.imputation_group_b, mechanism=args.imputation_mechanism,
                missing_fraction=args.imputation_missing_fraction,
                replicates=args.imputation_replicates, seed=args.imputation_seed,
                fdr_threshold=args.benchmark_fdr,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            raise SystemExit(f"Downstream imputation bias evaluation failed: {exc}") from exc
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if args.normalize_geo_matrix:
        if not args.normalization_method or not args.normalization_output:
            raise SystemExit("--normalize-geo-matrix requires --normalization-method and --normalization-output.")
        from .geo_normalization import normalize_geo_matrix, verify_geo_normalization_rerun
        try:
            if args.verify_normalization:
                report = verify_geo_normalization_rerun(
                    args.normalize_geo_matrix, args.normalization_output,
                    args.normalization_method, prior_count=args.normalization_prior_count,
                )
            else:
                report = normalize_geo_matrix(
                    args.normalize_geo_matrix, args.normalization_output,
                    args.normalization_method, prior_count=args.normalization_prior_count,
                )
        except (OSError, ValueError, RuntimeError) as exc:
            raise SystemExit(f"GEO matrix normalization failed: {exc}") from exc
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
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
    if args.geo_affymetrix_rma:
        if not args.affy_backend or not args.affy_output:
            raise SystemExit("--geo-affymetrix-rma requires --affy-backend and --affy-output.")
        from .geo_affymetrix import AffymetrixRMAAnalyzer
        try:
            report = AffymetrixRMAAnalyzer().analyze(
                args.geo_affymetrix_rma, args.affy_output, backend=args.affy_backend,
                expected_platform=args.affy_platform,
                rscript=args.rscript, timeout_seconds=args.affy_timeout,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            raise SystemExit(f"Affymetrix RMA failed: {exc}") from exc
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if args.geo_voom:
        if not args.geo_group_a or not args.geo_group_b or not args.geo_group:
            raise SystemExit("--geo-voom requires --geo-group for every sample, --geo-group-a, and --geo-group-b.")
        labels = {}
        for assignment in args.geo_group:
            sample, separator, group = assignment.partition("=")
            if not separator or not sample.strip() or not group.strip() or sample.strip() in labels:
                raise SystemExit(f"Invalid or duplicate --geo-group assignment: {assignment!r}")
            labels[sample.strip()] = group.strip()
        from .geo_voom import GEOVoomAnalyzer
        try:
            result = GEOVoomAnalyzer().analyze(
                args.geo_voom, labels, args.geo_group_a, args.geo_group_b,
                rscript=args.rscript, timeout_seconds=args.voom_timeout,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            raise SystemExit(f"limma-voom analysis failed: {exc}") from exc
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
                source_file=str(args.geo_voom),
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
            print(f"limma-voom: {result['features_returned']} features | {result['contrast']['direction']}")
            print(f"Software: R {result['software']['r']}, edgeR {result['software']['edgeR']}, limma {result['software']['limma']}")
            print("Interpretation: " + result["limitations"])
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
        covariates = {}
        if args.geo_covariates:
            try:
                with open(args.geo_covariates, "r", encoding="utf-8") as handle:
                    covariates = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                raise SystemExit(f"Cannot read --geo-covariates JSON: {exc}") from exc
            if not isinstance(covariates, dict):
                raise SystemExit("--geo-covariates must contain a JSON object.")
        from .geo_deseq2 import GEOCountAnalyzer
        try:
            result = GEOCountAnalyzer().analyze(
                args.geo_deseq2, labels, args.geo_group_a, args.geo_group_b,
                rscript=args.rscript, timeout_seconds=args.deseq2_timeout,
                covariates=covariates,
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
    if args.propose_protocol:
        if not args.protocol_domain:
            raise SystemExit("--propose-protocol requires --protocol-domain.")
        run = store.load_run(args.propose_protocol)
        if run is None:
            raise SystemExit(f"Research run not found: {args.propose_protocol}")
        from .protocols import ExperimentProtocolBuilder
        experiment = ExperimentProtocolBuilder().build(
            run, args.protocol_domain, args.protocol_hypothesis_id,
        )
        store.save_run(run)
        store.log_event(
            run.run_id, "domain_protocol_proposed",
            {"experiment_id": experiment.experiment_id, "domain": args.protocol_domain,
             "hypothesis_id": args.protocol_hypothesis_id},
            event_key=f"domain-protocol:{experiment.experiment_id}",
        )
        print(json.dumps(experiment.__dict__, indent=2, ensure_ascii=False) if args.json
              else f"Proposed {args.protocol_domain} protocol {experiment.experiment_id}; status remains PROPOSED.")
        return
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
    if args.link_cross_run_claims:
        if not (args.other_run_id and args.claim_a_id and args.claim_b_id and args.cross_run_rationale.strip()):
            raise SystemExit("--link-cross-run-claims requires --other-run-id, --claim-a-id, --claim-b-id, and --cross-run-rationale.")
        link = store.create_cross_run_claim_link(
            args.link_cross_run_claims, args.claim_a_id, args.other_run_id,
            args.claim_b_id, args.cross_run_relation, args.cross_run_rationale,
        )
        for run_id in (link.run_a_id, link.run_b_id):
            store.log_event(run_id, "cross_run_claim_link_created", link.__dict__,
                            event_key=f"cross-run-link:{link.link_id}")
        print(json.dumps(link.__dict__, indent=2, ensure_ascii=False) if args.json
              else f"Created pending cross-run link {link.link_id}; no relationship was accepted.")
        return
    if args.review_cross_run_link:
        if not args.cross_run_status or not args.cross_run_note.strip():
            raise SystemExit("--review-cross-run-link requires --cross-run-status and --cross-run-note.")
        link = store.review_cross_run_claim_link(
            args.review_cross_run_link, args.cross_run_status, args.cross_run_note,
        )
        for run_id in (link.run_a_id, link.run_b_id):
            store.log_event(run_id, "cross_run_claim_link_reviewed", link.__dict__,
                            event_key=f"cross-run-review:{link.link_id}")
        print(json.dumps(link.__dict__, indent=2, ensure_ascii=False) if args.json
              else f"Cross-run link {link.link_id}: {link.status} (human-reviewed).")
        return
    if args.score_answer:
        if not (args.answer_file and args.answer_reviewer.strip() and args.answer_review_note.strip()):
            raise SystemExit("--score-answer requires --answer-file, --answer-reviewer, and --answer-review-note.")
        score_values = {
            "factual_accuracy": args.score_accuracy,
            "evidence_traceability": args.score_traceability,
            "uncertainty_calibration": args.score_uncertainty,
            "reasoning_quality": args.score_reasoning,
            "completeness": args.score_completeness,
        }
        if any(value is None for value in score_values.values()):
            raise SystemExit("All five scores are required: --score-accuracy, --score-traceability, --score-uncertainty, --score-reasoning, --score-completeness.")
        try:
            with open(args.answer_file, "r", encoding="utf-8") as handle:
                answer_text = handle.read()
        except OSError as exc:
            raise SystemExit(f"Cannot read answer file: {exc}") from exc
        review = store.record_answer_quality_review(
            args.score_answer, answer_text, args.answer_reviewer, score_values,
            args.answer_review_note,
            [item.strip() for item in args.answer_source_ids.split(",") if item.strip()],
        )
        print(json.dumps(review, indent=2, ensure_ascii=False) if args.json
              else f"Human answer review saved: {review['review_id']} | reviewer {review['reviewer']}")
        return
    if args.review_claim:
        if not args.claim_id or not args.claim_status or not args.claim_reviewer.strip() or not args.claim_note.strip():
            raise SystemExit("--review-claim requires --claim-id, --claim-status, --claim-reviewer, and --claim-note.")
        run = store.load_run(args.review_claim)
        if run is None:
            raise SystemExit(f"Research run not found: {args.review_claim}")
        from .knowledge import KnowledgeBase
        claim = KnowledgeBase().review_claim(
            run, args.claim_id, args.claim_status, args.claim_reviewer,
            args.claim_note, args.claim_impact_level,
        )
        store.save_run(run)
        store.log_event(run.run_id, "claim_human_reviewed", {
            "claim_id": claim.claim_id, "status": claim.status,
            "impact_level": claim.impact_level, "reviewed_by": claim.reviewed_by,
        }, event_key=f"claim-review:{claim.claim_id}:{claim.reviewed_at}")
        print(json.dumps(claim.__dict__, indent=2, ensure_ascii=False) if args.json
              else f"Claim {claim.claim_id}: {claim.status} | impact {claim.impact_level} | reviewed by {claim.reviewed_by}")
        return
    if args.review_connection:
        if not args.connection_id or not args.connection_status or not args.connection_note.strip():
            raise SystemExit("--review-connection requires --connection-id, --connection-status, and --connection-note.")
        run = store.load_run(args.review_connection)
        if run is None:
            raise SystemExit(f"Research run not found: {args.review_connection}")
        from .knowledge import KnowledgeBase
        connection = KnowledgeBase().review_cross_domain_connection(
            run, args.connection_id, args.connection_status, args.connection_note,
        )
        store.save_run(run)
        if args.json:
            print(json.dumps(connection.__dict__, indent=2, ensure_ascii=False))
        else:
            print(f"Connection {connection.connection_id}: {connection.status}")
            print(f"Human review: {connection.reviewer_note}")
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
        elif args.experiment_action == "review":
            if not args.execution_review_status or not args.execution_reviewer.strip() or not args.execution_review_note.strip():
                raise SystemExit("review requires --execution-review-status, --execution-reviewer, and --execution-review-note.")
            experiment = manager.review_performed_execution(
                run, args.experiment_id, args.execution_review_status,
                args.execution_reviewer, args.execution_review_note,
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
            or args.show_tasks or args.show_hypotheses or args.show_sources or args.show_connections
            or args.cross_run_candidates or args.show_cross_run_links is not None
            or args.rank_citation_graph or args.traverse_citation_graph or args.show_answer_reviews):
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
        if args.show_answer_reviews:
            reviews = store.list_answer_quality_reviews(args.show_answer_reviews)
            from .answer_benchmark import summarize_answer_reviews
            report = {"reviews": reviews, "summary": summarize_answer_reviews(reviews)}
            if args.json:
                print(json.dumps(report, indent=2, ensure_ascii=False))
            else:
                if not reviews:
                    print("No human-scored answer reviews are stored for this run.")
                for item in reviews:
                    print(f"- {item['review_id']} | {item['reviewer']} | {item['created_at']}")
                    print("  Scores: " + ", ".join(f"{key}={value}" for key, value in item["scores"].items()))
                    print(f"  Note: {item['reviewer_note']}")
                print("Average scores: " + json.dumps(report["summary"]["dimension_averages"]))
                print("Limitations: " + report["summary"]["limitations"])
            return
        if args.traverse_citation_graph:
            if not args.citation_start_source:
                raise SystemExit("--traverse-citation-graph requires --citation-start-source.")
            run = store.load_run(args.traverse_citation_graph)
            if run is None:
                raise SystemExit(f"Research run not found: {args.traverse_citation_graph}")
            from .citation_graph import traverse_citation_graph
            report = traverse_citation_graph(
                run, args.citation_start_source, direction=args.citation_direction,
                max_depth=args.citation_depth, limit=args.limit,
            )
            if args.json:
                print(json.dumps(report, indent=2, ensure_ascii=False))
            else:
                print(f"Citation traversal from {report['start_title']} ({report['start_source_id']})")
                print(f"Direction: {report['direction']} | Depth limit: {report['max_depth']} | "
                      f"Reached: {report['nodes_reached']}")
                for item in report["results"]:
                    print(f"- depth {item['depth']} | {item['source_id']} | {item['title']} | DOI {item['doi'] or 'unknown'}")
                    print("  Path: " + " -> ".join(item["path_source_ids"]))
                print(f"Unresolved citation records: {report['unresolved_citation_records']}")
                print("Limitations: " + report["limitations"])
            return
        if args.rank_citation_graph:
            run = store.load_run(args.rank_citation_graph)
            if run is None:
                raise SystemExit(f"Research run not found: {args.rank_citation_graph}")
            from .citation_graph import rank_citation_graph
            report = rank_citation_graph(run, limit=args.limit)
            if args.json:
                print(json.dumps(report, indent=2, ensure_ascii=False))
            else:
                print(f"Citation graph: {report['nodes']} source nodes | {report['resolved_edges']} resolved edges")
                print(f"Unresolved citation records: {report['unresolved_citation_records']}")
                for item in report["ranked_sources"]:
                    print(f"- {item['source_id']} | PageRank {item['pagerank']:.6f} | "
                          f"in {item['incoming_edges']} | out {item['outgoing_edges']}")
                    print(f"  {item['title']} | DOI {item['doi'] or 'unknown'}")
                print("Limitations: " + report["limitations"])
            return
        if args.cross_run_candidates:
            items = portfolio.cross_run_claim_candidates(args.cross_run_candidates, limit=args.limit)
            if args.json:
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                if not items:
                    print("No source-backed cross-run claim candidates met the lexical threshold.")
                for item in items:
                    print(f"- similarity {item['lexical_similarity']:.3f} | {item['run_a_id']} ↔ {item['run_b_id']}")
                    print(f"  A [{item['claim_a_id']}]: {item['claim_a']}")
                    print(f"  B [{item['claim_b_id']}]: {item['claim_b']}")
                    print(f"  Evidence: {', '.join(item['evidence_a_ids'])} ↔ {', '.join(item['evidence_b_ids'])}")
                    print("  Candidate only; inspect before persisting with --link-cross-run-claims.")
            return
        if args.show_cross_run_links is not None:
            items = store.list_cross_run_claim_links(args.show_cross_run_links or None)
            if args.json:
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                if not items:
                    print("No cross-run claim links are stored.")
                for item in items:
                    print(f"- {item['link_id']} | {item['status']} | {item['relation']}")
                    print(f"  {item['run_a_id']}:{item['claim_a_id']} ↔ {item['run_b_id']}:{item['claim_b_id']}")
                    print(f"  Evidence: {', '.join(item['evidence_a_ids'])} ↔ {', '.join(item['evidence_b_ids'])}")
                    print(f"  Rationale: {item['rationale']}")
                    if item['reviewer_note']:
                        print(f"  Human review: {item['reviewer_note']}")
            return
        if args.show_connections:
            run = store.load_run(args.show_connections)
            if run is None:
                raise SystemExit(f"Research run not found: {args.show_connections}")
            sources = {item.source_id: item for item in run.sources}
            items = []
            for connection in run.cross_domain_connections:
                items.append({
                    **connection.__dict__,
                    "source_titles": [sources[source_id].title for source_id in connection.source_ids
                                      if source_id in sources],
                })
            if args.json:
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                if not items:
                    print("No cross-domain connection proposals in this run.")
                for item in items:
                    print(f"- {item['connection_id']} | {item['status']} | {item['domain_a']} ↔ {item['domain_b']}")
                    print(f"  {item['statement']}")
                    print(f"  Rationale: {item['rationale']}")
                    print(f"  Sources: {', '.join(item['source_titles']) or 'unavailable'}")
                    print(f"  Testable prediction: {item['testable_prediction']}")
                    if item['reviewer_note']:
                        print(f"  Human review: {item['reviewer_note']}")
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
    if (args.full_text or args.discover_geo_files or args.download_geo_files or args.analyze_geo_files
            or args.citation_network or args.incoming_citations) and args.literature is None and not args.research_literature:
        raise SystemExit("--full-text and GEO file options require --literature or --research-literature.")
    if not 1 <= args.dataset_max_mb <= 1000:
        raise SystemExit("--dataset-max-mb must be between 1 and 1000.")
    if (args.extract_claims or args.compare_papers) and args.literature is None and not args.research_literature:
        raise SystemExit("--extract-claims and --compare-papers require --literature or --research-literature.")
    if (args.compare_papers or args.review_evidence) and not args.extract_claims:
        raise SystemExit("--compare-papers and --review-evidence require --extract-claims.")
    if args.literature is not None:
        run = ResearchRun(question=args.literature)
        providers = {"both": ("europepmc", "crossref"), "biology": ("europepmc", "crossref", "geo"), "all": ("europepmc", "crossref", "geo", "arxiv", "pubchem"), "arxiv": ("arxiv",), "pubchem": ("pubchem",), "europepmc": ("europepmc",), "crossref": ("crossref",), "geo": ("geo",)}[args.provider]
        client = LiteratureClient(mailto=args.mailto)
        report = client.search(args.literature, limit=args.limit, providers=providers)
        client.ingest(run, report)
        from .fulltext import OpenAccessFullTextClient
        full_text_report = OpenAccessFullTextClient().ingest(run) if args.full_text else None
        citation_report = None
        if args.citation_network:
            from .citation_network import CrossrefCitationClient
            citation_report = CrossrefCitationClient(
                mailto=args.mailto, max_depth=args.reference_depth,
                max_nodes=args.reference_nodes).discover(run)
        incoming_citation_report = None
        if args.incoming_citations:
            from .incoming_citations import OpenAlexIncomingCitationClient
            incoming_citation_report = OpenAlexIncomingCitationClient(
                mailto=args.mailto, max_depth=args.incoming_citation_depth,
                max_nodes=args.incoming_citation_nodes).discover(run)
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
            print(json.dumps({"run": run.to_dict(), "literature_report": report.__dict__, "claim_extraction_report": (extraction_report.__dict__ if extraction_report else None), "comparison_report": (comparison_report.__dict__ if comparison_report else None), "evidence_review_report": (evidence_review_report.__dict__ if evidence_review_report else None), "full_text_report": (full_text_report.__dict__ if full_text_report else None), "geo_discovery_report": (geo_discovery_report.__dict__ if geo_discovery_report else None), "geo_download_report": (geo_download_report.__dict__ if geo_download_report else None), "geo_analysis_report": (geo_analysis_report.__dict__ if geo_analysis_report else None), "citation_report": (citation_report.__dict__ if citation_report else None), "incoming_citation_report": (incoming_citation_report.__dict__ if incoming_citation_report else None)}, indent=2, ensure_ascii=False))
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
        if incoming_citation_report:
            print(f"Incoming citations: {incoming_citation_report.links_created} citing works discovered.")
        return
    agent_suite = None
    if args.agent_provider in {"gemini", "auto"}:
        from .model_agents import GeminiAgentSuite
        agent_suite = GeminiAgentSuite(
            model=args.gemini_model,
            routing="fallback" if args.agent_provider == "auto" else "single",
        )
    providers = {"both": ("europepmc", "crossref"), "all": ("europepmc", "crossref", "geo", "arxiv", "pubchem"), "arxiv": ("arxiv",), "pubchem": ("pubchem",), "europepmc": ("europepmc",), "crossref": ("crossref",), "geo": ("geo",)}[args.provider]
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
        incoming_citation_network_enabled=args.incoming_citations,
        gemini_model=args.gemini_model,
        research_domain=args.domain,
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
