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

The normal run remains deterministic and offline. To explicitly opt in to Gemini-backed planning, research synthesis, exploration, competing hypothesis generation, skeptic review, experiment proposal, provisional evidence-integrity auditing, literature-conditioned novelty triage, and source-linked cross-domain connection proposals:

    export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    python -m oracle "How does a fertilized egg develop?" --agent-provider gemini --gemini-model gemini-2.5-flash --cycles 3

The Gemini agent suite uses the same `run(context) -> result` contract as the deterministic agents. Model-generated research statements are stored only as INFERENCE, never as source evidence. Hypotheses remain provisional and experiment designs remain PROPOSED. The Gemini auditor emits review warnings only and cannot alter evidence stance or claim status. Cross-domain proposals cite at least two existing source IDs, remain pending human review, and can be accepted/rejected/deferred through the CLI. The Gemini novelty assessor runs only when source-backed literature evidence is present, validates cited source IDs, and reports provisional prior-art triage rather than a novelty guarantee. These provider-backed review agents and cross-domain proposal gates have unit-level contract tests; live scientific quality has not yet been independently validated. The default provider is still `deterministic`; no model provider is called unless explicitly selected. `--agent-provider gemini` uses Gemini only. Opt-in `--agent-provider auto` enables ordered Gemini → Groq → OpenRouter fallback when credentials are configured. Set `GROQ_API_KEY` with `ORACLE_GROQ_MODEL`, and/or `OPENROUTER_API_KEY` with `ORACLE_OPENROUTER_MODEL`; provider keys are read only from environment variables and are never stored. Routing advances only for quota/rate-limit, network/timeout, and transient server failures; authentication/configuration errors stop rather than silently switching accounts. The active model is recorded on generated inference metadata. This is ordered failover, not automatic quality/cost optimization. Transient Gemini HTTP/network failures receive a small bounded retry; explicit quota-exhaustion responses stop immediately. Other provider errors fail and checkpoint the run rather than silently pretending that deterministic output came from Gemini.

Citation graph ranking and bounded multi-hop traversal are available for DOI-resolved links between papers already present in one saved run. Crossref can also expand outgoing references and OpenAlex incoming citations can expand citing works; both add bounded metadata-only external paper nodes:
```bash
python -m oracle --rank-citation-graph RUN_ID
python -m oracle --traverse-citation-graph RUN_ID --citation-start-source SOURCE_ID --citation-direction both --citation-depth 3
python -m oracle --literature "embryo development" --citation-network --reference-depth 3 --reference-nodes 100
python -m oracle --literature "embryo development" --incoming-citations --incoming-citation-depth 3 --incoming-citation-nodes 100
```
Traversal supports `outgoing` (works cited by the start paper), `incoming` (works citing it), or `both`, with depth capped at six and result count bounded by `--limit`. Each result includes its shortest source-ID path. Unresolved DOI targets are not fabricated as graph nodes; citation connectivity is not evidence quality, agreement, or scientific truth.

## Optional limma-voom analysis

For raw integer RNA-seq counts with an explicitly declared two-group design, ORACLE can call the installed R/Bioconductor stack (edgeR + limma). It does not infer sample groups; both groups need biological replicates. The result includes R/edgeR/limma versions, input checksum, BH-adjusted p-values, and can be persisted as pending-review candidates in a saved run.

```bash
python -m oracle --geo-voom counts.tsv \
  --geo-group GSM1=control --geo-group GSM2=control \
  --geo-group GSM3=treated --geo-group GSM4=treated \
  --geo-group-a control --geo-group-b treated --json
```

Install R, edgeR and limma separately. CI mocks the R subprocess; the adapter still needs independent comparison against trusted limma/edgeR reference outputs before production scientific use. It currently supports only a two-group design without additional covariates.

## Optional Affymetrix CEL RMA preprocessing

For Affymetrix raw CEL files, ORACLE can run Bioconductor RMA preprocessing through an explicitly selected package family. Supply each CEL file separately and choose `affy` for compatible classic 3-prime arrays or `oligo` for compatible oligonucleotide array families; do not guess the family from filenames.

```bash
python -m oracle --geo-affymetrix-rma sample1.CEL --geo-affymetrix-rma sample2.CEL \
  --affy-backend affy --affy-output normalized-expression.tsv --json
```

The adapter records every CEL SHA-256, file size, R/package versions, output checksum, and bounded runtime. It preserves feature/probe-set identifiers but does not perform annotation mapping, batch correction, differential testing, or biological interpretation. Install the selected Bioconductor package and its platform-specific annotation/CDF dependencies separately. CI tests the adapter contract with a mocked R subprocess; real CEL execution and comparison with trusted platform reference outputs remain unvalidated.

## Paired model evaluation

To compare a Gemini/hosted model with ORACLE's deterministic baseline, use the paired human-scoring template at `benchmarks/paired_model_comparison_template.json`. Populate it only after both systems answer the same frozen question using the same source packet, then have at least two reviewers score both answers with the same five-dimension rubric.

```bash
python -m oracle --paired-answer-benchmark benchmarks/my_paired_scores.json
```

The evaluator reports per-dimension paired score deltas and reproducible bootstrap intervals. Scores are subjective ordinal judgments, not calibrated accuracy or proof of general model superiority. The checked-in template contains no fabricated results.

## Independent preprocessing and evidence benchmarks

Compare ORACLE TMM normalization factors with a local edgeR installation on the exact same raw-count matrix:

```bash
python -m oracle --compare-tmm-edger counts.tsv --rscript Rscript
```

Run deterministic MCAR, MAR, or MNAR masking stress tests for row-median imputation:

```bash
python -m oracle --imputation-benchmark complete-matrix.tsv \
  --imputation-missing-fraction 0.1 --imputation-replicates 50 --imputation-seed 1729 \
  --imputation-mechanism MNAR
```

MCAR uses random masking, MAR depends on an observed sample-position covariate, and MNAR preferentially masks low values. These synthetic sensitivity tests do not identify a dataset’s actual missingness mechanism or establish downstream statistical bias.

For evidence attribution and entailment, `benchmarks/evidence_adjudication_template.json` defines a human-label schema. Populate it only after at least two reviewers independently check each source and disagreements are adjudicated. Score a completed file with:

```bash
python -m oracle --evidence-benchmark benchmarks/my_adjudicated_cases.json
```

The evaluator reports stance confusion, per-class precision/recall/F1, source-ID attribution validity, and exact-quote validity. The checked-in template is intentionally empty: ORACLE does not fabricate expert gold labels. Split evaluation data by source/study to reduce leakage.

## Domain-specific experiment protocols

ORACLE can append a conservative protocol scaffold to a saved run. Supported templates: `plant_biology`, `molecular_biology`, `cell_biology`, and `computational_biology`.

```bash
python -m oracle --propose-protocol RUN_ID --protocol-domain plant_biology --protocol-hypothesis-id HYPOTHESIS_ID
```

Templates prompt for controls, biological replication, randomization, batch metadata, pre-specified analysis, raw-data preservation, software versions, and checksums. They remain `PROPOSED`; they are not validated SOPs, do not execute experiments, and require qualified domain/ethics/biosafety review. Optional count-aware DESeq2 and limma-voom adapters are available when their R/Bioconductor packages are installed; independent reference validation and platform-specific raw-probe background correction remain pending.

## Human review for high-impact claims and performed experiments

Claims can be marked `normal`, `high`, or `critical` impact when reviewed. A supported claim needs source-backed support links; high-impact claims require at least two independent source groups, and critical claims require three. Weakened/rejected decisions require source-backed refuting links. Every decision records reviewer identity and rationale.

```bash
python -m oracle --review-claim RUN_ID --claim-id CLAIM_ID --claim-status supported --claim-impact-level high --claim-reviewer "Reviewer" --claim-note "Compared independent primary sources"
python -m oracle --experiment-action review --experiment-run RUN_ID --experiment-id EXPERIMENT_ID --execution-review-status accepted --execution-reviewer "Independent reviewer" --execution-review-note "Verified notebook, sample IDs, and raw files"
```

A real experiment remains recorded as performed but cannot be evaluated until a reviewer other than the recorded operator accepts its execution provenance. Simulations are not subject to this real-world execution check.

## Shared cross-run knowledge graph

Saved runs can be searched for lexically similar claim pairs, but only when each claim has at least one source-backed evidence link. The candidate queue is a retrieval heuristic, not a semantic verdict. Inspect candidates, then persist a relationship explicitly:

```bash
python -m oracle --cross-run-candidates RUN_ID
python -m oracle --link-cross-run-claims RUN_A --other-run-id RUN_B --claim-a-id CLAIM_A --claim-b-id CLAIM_B --cross-run-relation supports --cross-run-rationale "Explain why the source contexts support this relation"
python -m oracle --show-cross-run-links
python -m oracle --review-cross-run-link LINK_ID --cross-run-status accepted --cross-run-note "Reviewed both source records and claim scope"
```

Links are stored in a dedicated SQLite table with both run IDs, claim IDs, and evidence IDs. Evidence provenance is revalidated at review time. All links begin as `pending_review`; accepting, rejecting, or requesting context requires a non-empty human note. A cross-run relation does not automatically merge claims or promote either claim to fact.

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
    python -m oracle --literature "embryo development" --provider all --limit 15 --citation-network --incoming-citations
    python -m oracle --literature "embryo development" --provider all --limit 15 --incoming-citations --incoming-citation-depth 3 --incoming-citation-nodes 100
    python -m oracle "Arabidopsis heat stress" --research-literature --provider geo --discover-geo-files
    python -m oracle "Arabidopsis heat stress" --research-literature --provider geo --download-geo-files --dataset-max-mb 50
    python -m oracle "Arabidopsis heat stress" --research-literature --provider geo --analyze-geo-files --dataset-max-mb 50
    python -m oracle "How does a fertilized egg develop?" --research-literature --full-text --agent-provider gemini --cycles 3

For OpenAlex expansion, depth is capped at five and newly added external nodes at 250. Added nodes contain bibliographic metadata only (no abstracts-as-evidence, claims, or quality scores); they are tagged `external_citation`. The discovery is incoming-only and bounded by the per-source result cap. Citation links are navigation metadata, not scientific support.

For batch-aware RNA-seq analysis, pass a JSON file mapping each categorical covariate to every matrix sample, for example:
```json
{"batch":{"GSM1":"batch_A","GSM2":"batch_B","GSM3":"batch_A","GSM4":"batch_B"}}
```
Then add `--geo-covariates covariates.json` to the `--geo-deseq2` command. ORACLE validates exact sample coverage and rejects invalid/reserved covariate names; DESeq2 checks the resulting design matrix for rank deficiency/confounding. The default DESeq2 pipeline applies median-of-ratios size-factor normalization. Only categorical covariates are currently supported; continuous covariates, interactions, and general microarray normalization are not implemented.

Use --literature for a standalone retrieval run, or --research-literature to ingest retrieved sources into the full QUESTION → PLAN → RESEARCH → DISCOVER → HYPOTHESIZE → CHALLENGE → EXPERIMENT DESIGN → DECIDE cycle. The latter makes retrieved abstracts and GEO summaries available to the selected research agents. Each work is stored with DOI/PMID/PMCID when available, authors, journal, date, provider, landing URL, licence/open-access metadata, and abstract text. The opt-in --full-text path retrieves article bodies only when Europe PMC reports open access, a PMCID exists, and the licence passes a strict reuse gate (CC BY, CC BY-SA, or CC0; non-commercial and no-derivatives variants are skipped). Retrieved text is bounded by size limits and retains its source and licence provenance. GEO Series records can have supplementary files listed with --discover-geo-files; --download-geo-files downloads them only when explicitly requested, with a default 50 MB per-file cap and SHA-256 checksums. --analyze-geo-files also discovers and downloads files, then parses supported TSV/CSV text expression matrices (including gzip-compressed GEO series_matrix files) under uncompressed-byte, row, sample, and cell limits. It verifies the recorded SHA-256 and stores per-sample descriptive summaries plus a source-linked DATASET record. It also preserves GEO sample accessions, titles, and per-sample characteristics (such as treatment/genotype) as annotations; ORACLE does not infer or silently assign experimental groups from those labels. It calculates per-sample numeric/missing counts, missing fraction, sample variance, and conservative QC flags (high missingness, constant values, or no numeric values). QC flags never remove samples automatically. It does not normalize data, perform differential-expression statistics, or infer biological effects; unsupported archives and binary formats are reported as skipped. Abstracts are source evidence with the exact "Abstract" locator. Sentence splitting produces unreviewed statement candidates only: it does not prove a claim or decide whether a paper supports/refutes it. Initial evidence links are contextual with zero weight until reviewed.

Optional Gemini claim extraction is available with --extract-claims. It creates source-quoted, unreviewed candidates only; it does not determine truth, entailment, contradiction, or whether a paper supports a hypothesis. Other dataset repositories, full statistical modeling outside the documented adapters, and calibrated evidence evaluation are not yet included. First-degree outgoing reference discovery and bounded incoming-citation discovery via OpenAlex are implemented. Optional full-text retrieval is limited to Europe PMC records with PMCID and a recognized reuse-friendly Creative Commons licence. Gemini can now propose quote-grounded support/refute/contextual evidence-review candidates through --review-evidence, but every suggestion remains pending human review and never changes evidence weights automatically. The opt-in Gemini suite covers planner, researcher, explorer, hypothesis generator, skeptic, and experiment designer; auditor and novelty assessment remain deterministic and conservative. Publisher copyright may apply to abstract text.

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

### Cross-domain connection proposals

When at least two source-backed literature records are available, the optional Gemini agent can propose cross-domain connections. Each proposal must cite at least two source IDs and remains pending human review:

```bash
python -m oracle "How do feedback principles connect developmental biology and control theory?" \
  --research-literature --agent-provider gemini --cycles 3
python -m oracle --show-connections RUN_ID
python -m oracle --review-connection RUN_ID --connection-id CONNECTION_ID \
  --connection-status accepted --connection-note "Reviewed both source contexts and the proposed prediction."
```

Statuses are `pending_review`, `accepted`, `rejected`, and `needs_context`. Acceptance records a human review decision on the proposal; it does not establish that the proposed connection is true or novel. Every cited source ID must already exist in the run's provenance store.

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


### Explicit GEO matrix normalization

Normalize a downloaded matrix into a separate output file:
```bash
# Continuous microarray-like measurements
python -m oracle --normalize-geo-matrix matrix.txt.gz --normalization-method quantile --normalization-output matrix.quantile.tsv

# Raw integer RNA-seq counts: exploratory library-size transform
python -m oracle --normalize-geo-matrix counts.tsv --normalization-method log2-cpm --normalization-output counts.log2cpm.tsv

# TMM effective-library-size adjusted CPM/log2-CPM (compare with edgeR before production use)
python -m oracle --normalize-geo-matrix counts.tsv --normalization-method tmm-log2-cpm --normalization-output counts.tmm-log2cpm.tsv

# Explicit row-median imputation for continuous matrices; emits a separate hashed missingness mask
python -m oracle --normalize-geo-matrix matrix_with_NA.tsv --normalization-method quantile-row-median --normalization-output matrix.imputed-quantile.tsv

# Repeat the same transform in the same runtime and compare output checksums
python -m oracle --normalize-geo-matrix matrix.txt.gz --normalization-method quantile --normalization-output matrix.check.tsv --verify-normalization
```
Supported methods: quantile normalization for continuous microarray-like measurements; CPM/log2-CPM and TMM-adjusted CPM/log2-CPM for non-negative integer raw counts; explicit row-median imputation followed by quantile normalization for continuous matrices with missing cells. The input is never overwritten. The report records input/output SHA-256, sample library sizes, and limitations. The optional rerun check compares byte-identical outputs in the same Python runtime; it is not an independent cross-platform validation. Quantile normalization should not be blindly applied to raw RNA-seq counts. CPM/log2-CPM is not DESeq2 or a differential-expression test. TMM is an ORACLE implementation of trimmed M-value effective-library-size scaling and has not yet been independently validated against edgeR reference outputs; do not use it as a production substitute until that comparison is completed. Row-median imputation emits a per-cell missingness mask and imputation values, but may bias distributions; it is an explicit exploratory option, not a missing-data model. Use DESeq2 for count-aware inference and verify assay/platform assumptions before interpretation.

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


### Build a DESeq2 matrix from individual GEO sample count files

Some GEO Series provide one raw-count table per GSM sample rather than one matrix. ORACLE can merge these files only when the user explicitly maps each sample to its file. Feature IDs must match exactly across files; the tool does not infer sample groups or gene annotations.

```bash
python -m oracle --merge-geo-counts \
  --geo-sample-file GSM3021223=data/geo/GSE111062/GSM3021223_GL48h1.txt.gz \
  --geo-sample-file GSM3021224=data/geo/GSE111062/GSM3021224_GL48h2.txt.gz \
  --geo-sample-file GSM3021235=data/geo/GSE111062/GSM3021235_HL48h1.txt.gz \
  --geo-sample-file GSM3021236=data/geo/GSE111062/GSM3021236_HL48h2.txt.gz \
  --count-feature-column 0 --count-value-column -1 \
  --count-output data/geo/GSE111062/HL48h_vs_GL48h_counts.tsv --json
```

**Important:** The example sample set is the 48-hour high-light (HL) versus growth-light (GL) contrast from GSE111062, with two samples per condition. GEO identifies this as a 7-day-old whole-seedling Arabidopsis high-light time course and describes duplicate samples at each time point. Inspect the downloaded files before running the command: confirm the actual feature/count column positions and use `--count-feature-column`, `--count-value-column`, and `--count-delimiter` to match them. The defaults above are illustrative, not a verified assertion about every GEO file layout. Confirm biological replicate status and exact sample metadata before analysis.

Then run DESeq2 with explicit group labels:

```bash
python -m oracle --geo-deseq2 data/geo/GSE111062/HL48h_vs_GL48h_counts.tsv \
  --geo-accession GSE111062 \
  --geo-group GSM3021223=GL --geo-group GSM3021224=GL \
  --geo-group GSM3021235=HL --geo-group GSM3021236=HL \
  --geo-group-a GL --geo-group-b HL --json
```

GEO record: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE111062  
Study paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC7030938/

The published paper and GEO record establish the study context and deposited data, but the paper's overall high-light findings are **not** a curated truth set for this exact 48-hour contrast. Do not score this contrast against an aggregate DEG count or an unrelated gene list. A benchmark manifest must use a documented, contrast-matched reference gene set before known-positive recovery metrics can be interpreted.


### Download only selected GEO GSM supplementary count files

GEO often exposes individual sample-level count files under each GSM accession, even when the Series supplementary directory contains a single archive. ORACLE can now discover and download only explicitly selected GSM files from the official NCBI HTTPS host. Each download is size-capped and receives a SHA-256 checksum.

For the GSE111062 48-hour growth-light versus high-light contrast, GEO identifies these samples:

- Growth light: GSM3021223 (GL48h1), GSM3021224 (GL48h2)
- High light: GSM3021235 (HL48h1), GSM3021236 (HL48h2)

Download:

```bash
python -m oracle --download-geo-samples \
  --gsm GSM3021223 --gsm GSM3021224 \
  --gsm GSM3021235 --gsm GSM3021236 \
  --dataset-max-mb 5 --json
```

The files are saved under `data/geo_samples/GSM.../`. Then inspect one file's header and first rows before choosing columns:

```bash
gzip -cd data/geo_samples/GSM3021223/*.gz | head
```

Merge the four files (adjust column flags to the observed file format):

```bash
python -m oracle --merge-geo-counts \
  --geo-sample-file GSM3021223=data/geo_samples/GSM3021223/GSM3021223_GL48h1.txt.gz \
  --geo-sample-file GSM3021224=data/geo_samples/GSM3021224/GSM3021224_GL48h2.txt.gz \
  --geo-sample-file GSM3021235=data/geo_samples/GSM3021235/GSM3021235_HL48h1.txt.gz \
  --geo-sample-file GSM3021236=data/geo_samples/GSM3021236/GSM3021236_HL48h2.txt.gz \
  --count-feature-column 0 --count-value-column -1 \
  --count-output data/geo/GSE111062/HL48h_vs_GL48h_counts.tsv --json
```

**Do not assume the illustrative column positions are correct without inspecting the files.** The GSM records describe tab-delimited gene-level raw counts, aligned to TAIR10 and generated with HTSeq, but the actual downloaded header/columns must be checked before merging. If there are extra annotation columns, configure the correct count column. GEO sample records: [GSM3021223](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM3021223), [GSM3021224](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM3021224), [GSM3021235](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM3021235), [GSM3021236](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM3021236).

After confirming sample identities, file format, count semantics, and biological replicate design, use the explicit `--geo-group` assignments documented above to run DESeq2. This downloader does not infer treatment groups, and downloading files is not itself a biological analysis.


### Preferred GSE archive workflow (GSE111062)

The GSE111062 GEO Series record advertises one supplementary archive, `GSE111062_RAW.tar` (about 3.2 MB), containing TXT sample files. Prefer the Series archive for this dataset; per-GSM supplementary directories are not guaranteed to contain the files. The direct GSM downloader above is useful only when a GSM directory actually lists a supplementary file.

Download the official Series archive:

```bash
python -m oracle --download-geo-series-archive GSE111062 --dataset-max-mb 10
```

Safely extract GSM-prefixed regular files (path traversal, links, non-sample files, excessive member counts and oversized extraction are rejected or skipped):

```bash
python -m oracle --extract-geo-archive data/geo/GSE111062/GSE111062_RAW.tar
```

Then inspect the extracted filenames and one file's contents before selecting the correct count columns:

```bash
find data/geo/GSE111062/GSE111062_RAW_extracted -maxdepth 1 -type f -printf '%f\n'
gzip -cd data/geo/GSE111062/GSE111062_RAW_extracted/GSM3021223* | head
```

Use the actual extracted paths with `--merge-geo-counts`. Do not assume column positions until inspecting the file. The archive's existence and sample names do not themselves validate sample group labels or replicate independence. The GEO Series record documents the study's sample design and the archive: [GSE111062](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE111062).
