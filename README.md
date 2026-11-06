# ORACLE 2.0

**An autonomous scientific research and discovery system.**

ORACLE combines Deep Research and Autonomous Discovery under a balanced operating policy: evidence quality and intellectual honesty constrain exploration, while the system actively searches for knowledge gaps, alternative explanations, and testable hypotheses.

## Current build status

The offline research foundation remains usable without credentials. Optional network literature retrieval uses public scholarly APIs; optional Gemini extraction and cross-paper comparison use a real model only when explicitly enabled. The baseline agents remain deterministic scaffolding. The orchestrator now measures whether unique research information was added, suppresses repeated scaffold records, checks core graph invariants, and stops after repeated no-progress cycles. This is safer lifecycle control, not proof of autonomous scientific reasoning.

## Quick start

Requires Python 3.10+ and no third-party dependencies. CI verifies Python 3.10–3.14, including the Python 3.14 runtime used in some Termux setups.

```bash
python -m oracle "How does a fertilized egg develop into a whole organism?"
python -m unittest discover -s tests -v
```

### Optional Gemini research agents

The normal run remains deterministic and offline. To explicitly opt in to Gemini-backed planning, research synthesis, exploration, competing hypothesis generation, skeptic review, and experiment proposal:

    export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    python -m oracle "How does a fertilized egg develop?" --agent-provider gemini --gemini-model gemini-2.5-flash --cycles 3

The Gemini agent suite uses the same `run(context) -> result` contract as the deterministic agents. Model-generated research statements are stored only as INFERENCE, never as source evidence. Hypotheses remain provisional and experiment designs remain PROPOSED. The structural auditor and novelty assessor remain conservative deterministic components. The default provider is still `deterministic`; Gemini is never called unless explicitly selected. Transient Gemini HTTP/network failures receive a small bounded retry; explicit quota-exhaustion responses stop immediately. Other provider errors fail and checkpoint the run rather than silently pretending that deterministic output came from Gemini.

## Modes

- `deep_research`: prioritize structured investigation and evidence assessment.
- `autonomous_discovery`: prioritize gaps, competing hypotheses, and new research directions.
- `both`: integrate both modes (default).

## Scientific integrity

ORACLE distinguishes source-backed evidence, inference, hypotheses, proposed experiments, simulated experiments, and experiments actually performed. A simulation is never represented as a real-world experiment. Experiment records have explicit lifecycle operations: proposed → simulated OR performed → evaluated. Execution kind and provenance remain stored even after evaluation. Unknowns and conflicting evidence remain explicit.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) and [docs/ROADMAP.md](docs/ROADMAP.md).

## Literature search (network opt-in)

ORACLE can search Europe PMC and Crossref public REST APIs without API keys or third-party Python packages. Network access occurs only when --literature or --research-literature is supplied.

    python -m oracle --literature "embryonic development cell fate signaling" --limit 10
    python -m oracle "How does a fertilized egg develop?" --research-literature --agent-provider gemini --cycles 3
    python -m oracle "How does a fertilized egg develop?" --research-literature --extract-claims --review-evidence --agent-provider gemini --cycles 3
    python -m oracle --literature "plant nonsense-mediated mRNA decay" --provider europepmc --limit 15 --json
    python -m oracle --literature "Arabidopsis heat stress" --provider geo --limit 10
    python -m oracle --literature "embryo development" --provider all --limit 15 --citation-network
    python -m oracle "Arabidopsis heat stress" --research-literature --provider geo --discover-geo-files
    python -m oracle "Arabidopsis heat stress" --research-literature --provider geo --download-geo-files --dataset-max-mb 50
    python -m oracle "Arabidopsis heat stress" --research-literature --provider geo --analyze-geo-files --dataset-max-mb 50
    python -m oracle "How does a fertilized egg develop?" --research-literature --full-text --agent-provider gemini --cycles 3

Use --literature for a standalone retrieval run, or --research-literature to ingest retrieved sources into the full QUESTION → PLAN → RESEARCH → DISCOVER → HYPOTHESIZE → CHALLENGE → EXPERIMENT DESIGN → DECIDE cycle. The latter makes retrieved abstracts and GEO summaries available to the selected research agents. Each work is stored with DOI/PMID/PMCID when available, authors, journal, date, provider, landing URL, licence/open-access metadata, and abstract text. The opt-in --full-text path retrieves article bodies only when Europe PMC reports open access, a PMCID exists, and the licence passes a strict reuse gate (CC BY, CC BY-SA, or CC0; non-commercial and no-derivatives variants are skipped). Retrieved text is bounded by size limits and retains its source and licence provenance. GEO Series records can have supplementary files listed with --discover-geo-files; --download-geo-files downloads them only when explicitly requested, with a default 50 MB per-file cap and SHA-256 checksums. --analyze-geo-files also discovers and downloads files, then parses supported TSV/CSV text expression matrices (including gzip-compressed GEO series_matrix files) under uncompressed-byte, row, sample, and cell limits. It verifies the recorded SHA-256 and stores per-sample descriptive summaries plus a source-linked DATASET record. It also preserves GEO sample accessions, titles, and per-sample characteristics (such as treatment/genotype) as annotations; ORACLE does not infer or silently assign experimental groups from those labels. It calculates per-sample numeric/missing counts, missing fraction, sample variance, and conservative QC flags (high missingness, constant values, or no numeric values). QC flags never remove samples automatically. It does not normalize data, perform differential-expression statistics, or infer biological effects; unsupported archives and binary formats are reported as skipped. Abstracts are source evidence with the exact "Abstract" locator. Sentence splitting produces unreviewed statement candidates only: it does not prove a claim or decide whether a paper supports/refutes it. Initial evidence links are contextual with zero weight until reviewed.

Optional Gemini claim extraction is available with --extract-claims. It creates source-quoted, unreviewed candidates only; it does not determine truth, entailment, contradiction, or whether a paper supports a hypothesis. Other dataset repositories, automatic GEO matrix normalization/statistical testing, incoming citation discovery and graph ranking, and calibrated evidence evaluation are not yet included. First-degree outgoing reference discovery is implemented. Optional full-text retrieval is limited to Europe PMC records with PMCID and a recognized reuse-friendly Creative Commons licence. Gemini can now propose quote-grounded support/refute/contextual evidence-review candidates through --review-evidence, but every suggestion remains pending human review and never changes evidence weights automatically. The opt-in Gemini suite covers planner, researcher, explorer, hypothesis generator, skeptic, and experiment designer; auditor and novelty assessment remain deterministic and conservative. Publisher copyright may apply to abstract text.

### Optional Gemini claim extraction

Set GEMINI_API_KEY in your shell (do not put the key in source files or commit it), then run:

    export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    python -m oracle --literature "embryonic development cell fate signaling" --provider both --limit 10 --extract-claims --review-evidence
    python -m oracle --literature "Arabidopsis heat stress" --provider geo --limit 10 --extract-claims --gemini-model gemini-2.5-flash --json

Gemini output is accepted only when its evidence_quote is an exact substring of the retrieved abstract, GEO summary, or licence-eligible full-text passage. Each candidate stores that quote, model name, source/evidence link, and an unreviewed status. Its evidence link remains CONTEXTUAL with zero weight. The feature is opt-in; normal offline runs never call Gemini.

### Cross-paper evidence comparison

Add --compare-papers together with --extract-claims to compare candidate statements across distinct papers:

    python -m oracle --literature "embryonic development cell fate signaling" --provider both --limit 10 --extract-claims --compare-papers
    python -m oracle --literature "Arabidopsis heat stress" --provider all --limit 12 --extract-claims --compare-papers --json

Gemini can propose one of four cross-paper relations: corroborates, contrasts, contextual, or not_comparable. Separately, --review-evidence asks Gemini to propose supports, refutes, or contextual for a candidate claim against an independent source passage. Both workflows require exact source quotations and preserve pending human review; model suggestions never change evidence stance or weight automatically. Inspect candidates with `python -m oracle --show-reviews RUN_ID`, then explicitly decide one with `python -m oracle --review-run RUN_ID --review-candidate CANDIDATE_ID --review-status accepted --review-note "Checked the source context." --review-strength 0.6`. Use `rejected` or `needs_context` when appropriate. Every saved comparison must include exact quotations found in BOTH source abstracts, GEO summaries, or retrieved full-text passages. Comparisons retain both source and evidence IDs, model, rationale, and pending_review status. These are review candidates, not verified contradictions or proof of agreement. ORACLE does not change claim status, evidence stance, or uncertainty scores based on these model suggestions. At most 30 claim pairs are sent per run by default.

### Citation network

Retrieve first-degree reference metadata for DOI-backed sources:

    python -m oracle --literature "cell fate signaling" --provider both --citation-network

This follows references reported by Crossref for retrieved DOI-backed works. It is not a complete incoming/outgoing citation graph; references without DOI are retained as title-only records where possible.

### Research portfolio and knowledge gaps

List saved research runs and compare their recorded coverage:

    python -m oracle --portfolio
    python -m oracle --assess-gaps RUN_ID
    python -m oracle --related-to "cell fate signaling"

The gap score is a transparent record-coverage heuristic based on source-backed evidence, claim review links, hypothesis evidence links, unresolved contradiction candidates, and task completion. It is not a probability, evidence quality score, or scientific completeness guarantee. Related-run search uses lexical token overlap only; it does not claim semantic similarity or discovery of a scientific connection.

### Source-quality review

ORACLE does not assign journal reputation or source reliability automatically. A human can inspect source provenance and record a transparent reliability assessment:

    python -m oracle --show-sources RUN_ID
    python -m oracle --source-action review --source-run RUN_ID --source-id SOURCE_ID --source-score 0.8 --source-note "Primary study; methods and controls reviewed."

The score is a human assessment on a 0–1 scale, not a calibrated probability. Updating a source score also updates the reliability field on evidence records linked to that source.

### Hypothesis evidence review

Inspect competing hypotheses and their source links:

    python -m oracle --show-hypotheses RUN_ID

Link independently reviewed source evidence, then record a human status decision:

    python -m oracle --hypothesis-action link --hypothesis-run RUN_ID --hypothesis-id HYP_ID --hypothesis-evidence-id EVIDENCE_ID --hypothesis-stance supports --hypothesis-note "Checked the source context."
    python -m oracle --hypothesis-action review --hypothesis-run RUN_ID --hypothesis-id HYP_ID --hypothesis-status supported --hypothesis-note "Relevant source records support the predicted outcome."

The system never promotes a hypothesis automatically. Supported, weakened, or rejected requires corresponding reviewed source evidence and a human note.

### Research task lifecycle

Inspect tasks, acceptance criteria, and evidence links:

    python -m oracle --show-tasks RUN_ID

Start a task, block it with a reason, retry it within the attempt budget, or complete it only with source-backed evidence:

    python -m oracle --task-action start --task-run RUN_ID --task-id TASK_ID
    python -m oracle --task-action complete --task-run RUN_ID --task-id TASK_ID --task-evidence-ids EVIDENCE_ID --task-note "Checked the source and recorded the result."
    python -m oracle --task-action block --task-run RUN_ID --task-id TASK_ID --task-note "No accessible source found."

Model inferences cannot satisfy the source-backed completion requirement. The default task retry budget is three attempts.

### Experiment lifecycle

Experiments are proposals until an explicit record is made. Record a simulation (never a physical experiment):

    python -m oracle --experiment-action simulate --experiment-run RUN_ID --experiment-id EXP_ID --simulation-engine "Python simulator v1" --experiment-results "Synthetic output ..." --simulation-limitations "Simplified model; no biological measurements."

Record a real experiment only when it was actually performed:

    python -m oracle --experiment-action perform --experiment-run RUN_ID --experiment-id EXP_ID --execution-method "qPCR, three biological replicates" --operator "Lab operator" --experiment-results "Recorded measurements ..."

Then record a human evaluation:

    python -m oracle --experiment-action evaluate --experiment-run RUN_ID --experiment-id EXP_ID --evaluation-note "Compared observations with preregistered predictions."

The execution kind remains preserved after evaluation. ORACLE does not execute physical experiments or invent results.

### Offline integrity benchmark

Run the cross-domain golden-question integrity benchmark:

    python -m unittest tests.test_golden_benchmark -v

It checks that the deterministic baseline preserves provenance and status invariants across eight question areas. It does not score scientific answer quality or validate Gemini reasoning.

## Current limitations

The Gemini adapter currently extracts quote-grounded candidate claims and proposes cross-paper relationships; it does not perform complete entailment verification or update scientific truth status. The autonomous cycle defaults to deterministic baseline agents; the optional Gemini agent suite can be selected explicitly. The decision engine measures newly persisted unique records (not scientific quality) and requests one bounded revised plan after the first stagnant cycle before stopping on repeated no-progress. A stopped run can be explicitly resumed; repeated no-progress cycles will stop it again unless a provider or new input produces new information.


### Explicit two-group GEO contrast (continuous log2 data only)

After checking the matrix scale and assigning every sample to exactly one of two groups, run:

```bash
python -m oracle --geo-contrast expression.tsv --geo-scale log2_continuous \
  --geo-group GSM_A1=control --geo-group GSM_A2=control \
  --geo-group GSM_B1=treated --geo-group GSM_B2=treated \
  --geo-group-a control --geo-group-b treated --json
```

This runs a per-feature Welch two-sample t-test and Benjamini-Hochberg false-discovery-rate correction. Group assignments are explicit user input; ORACLE does not infer them from sample titles. The adapter requires at least two observations per group and complete sample mapping. It is **not suitable for raw RNA-seq counts**, does not normalize values or correct batch effects, and assumes independent biological replicates and appropriately transformed continuous log2 measurements. Results are statistical associations, not causal or validated biological discoveries.


### Raw-count RNA-seq differential expression (optional DESeq2 backend)

The raw-count workflow uses Bioconductor DESeq2 through `Rscript`. It is separate from the continuous-log2 Welch adapter above. Install R, then install DESeq2 in R:

```r
if (!requireNamespace("BiocManager", quietly=TRUE))
    install.packages("BiocManager")
BiocManager::install("DESeq2")
```

Run only on an unnormalized integer read-count matrix with biological replicates and an explicit sample-to-group mapping:

```bash
python -m oracle --geo-deseq2 raw_counts.tsv \
  --geo-group GSM_A1=control --geo-group GSM_A2=control \
  --geo-group GSM_B1=treated --geo-group GSM_B2=treated \
  --geo-group-a control --geo-group-b treated --json
```

ORACLE validates non-negative integer counts, complete two-group sample assignment, unique feature IDs, and minimum replicate counts before invoking DESeq2. Results include base mean, log2 fold change, standard error, Wald statistic, p-value, adjusted p-value, matrix SHA-256, and R/DESeq2 versions. Python CI mocks the external R process; a live DESeq2 run is not claimed unless tested in an R environment with DESeq2 installed.

This first adapter supports a simple two-group design only. It does not infer groups, remove outliers, correct batch effects, or replace review of library sizes and DESeq2 diagnostics. It is not for TPM/FPKM, normalized/log-transformed values, or single-cell pseudobulk without a correctly constructed count matrix and design.


### Persisting a DESeq2 result in an ORACLE research run

To keep the analysis, its complete result table, contrast, sample mapping, matrix checksum, software versions, and limitations with an existing run, pass that run's ID:

```bash
python -m oracle --geo-deseq2 raw_counts.tsv \
  --geo-group C1=control --geo-group C2=control \
  --geo-group T1=treated --geo-group T2=treated \
  --geo-group-a control --geo-group-b treated \
  --geo-run-id RUN_ID --geo-accession GSE12345 --json
```

The analysis is stored in the run payload and the SQLite `differential_expression_analyses` table. It starts with `review_status=unreviewed`; no gene result is automatically promoted to a scientific claim or evidence link. Without `--geo-run-id`, the command remains a standalone analysis and does not persist a run record.


### Provisional DESeq2 candidate findings and human review

When a DESeq2 result is attached to a research run, ORACLE creates provisional candidate findings for rows with a non-null adjusted p-value at or below the configured threshold (default 0.05) and a finite log2 fold change:

```bash
python -m oracle --geo-deseq2 raw_counts.tsv \
  --geo-group C1=control --geo-group C2=control \
  --geo-group T1=treated --geo-group T2=treated \
  --geo-group-a control --geo-group-b treated \
  --geo-run-id RUN_ID --geo-accession GSE12345 --deseq2-fdr 0.05
```

Inspect the analysis and candidates:

```bash
python -m oracle --show-deseq2 RUN_ID
```

Record an explicit human decision with a rationale:

```bash
python -m oracle --review-deseq2 RUN_ID \
  --deseq2-analysis-id ANALYSIS_ID --deseq2-feature GENE_ID \
  --deseq2-review-status accepted \
  --deseq2-review-note "Checked sample design, contrast, and dataset context."
```

Review statuses are `pending_review`, `accepted`, `rejected`, or `needs_context`. A candidate can be reviewed only once through this command; a review note is mandatory. **Accepted here means a human accepted the candidate analysis finding, not that ORACLE has established a validated scientific claim.** This workflow does not automatically create claims, evidence links, or biological causality statements. Independent replication and source/context review are still required.


### Cross-dataset directional consistency screen

After saving DESeq2 analyses from more than one GEO Series into the same research run, ORACLE can compare an exact feature across analyses with distinct GEO accessions and distinct matrix SHA-256 checksums:

```bash
python -m oracle --screen-replication RUN_ID \
  --replication-analysis-id SOURCE_ANALYSIS_ID \
  --replication-feature GENE_ID --replication-fdr 0.05 --json
```

The screen reports whether other eligible datasets show a significant effect in the same or opposite direction, a non-significant effect, or did not test the feature. It excludes analyses that reuse the source accession or matrix checksum. This is deliberately a **directional consistency screen, not a replication verdict**: distinct accessions/checksums do not prove independent cohorts, and group labels alone do not prove comparable biology. A scientist must verify treatment/genotype, tissue, timepoint, phenotype, feature annotation, and design before calling results replication. It does not perform meta-analysis, batch correction, causal inference, or automatic claim promotion.


### Curated known-positive benchmark for DESeq2

ORACLE includes a reproducible **known-positive recovery** scorer. Supply a DESeq2 JSON output (the `--json` result) or a result TSV, plus a separately curated JSON manifest:

```json
{
  "dataset_accession": "GSE12345",
  "reference": "https://doi.org/REPLACE-WITH-CURATED-REFERENCE",
  "truth_set_version": "v1",
  "contrast": {"group_a": "control", "group_b": "treated"},
  "known_positive_features": ["GENE_A", "GENE_B"]
}
```

Run:

```bash
python -m oracle --benchmark-results deseq2-results.json \
  --benchmark-manifest benchmark-truth.json --benchmark-fdr 0.05 \
  --benchmark-abs-log2fc 0.0 --json
```

The report distinguishes recovered known positives, missed positives that were tested, positives absent from the tested matrix, and significant hits absent from the curated reference. It records both input SHA-256 checksums and the thresholds. This is a **known-positive recovery/overlap** score, not a complete classifier benchmark: unmatched hits are not automatically biological false positives, because the curated reference may be incomplete. Feature identifiers and contrast direction must be harmonized by the benchmark curator. Do not use placeholder manifests as biological evidence; include a real dataset-specific curation reference and documented truth-set version.
