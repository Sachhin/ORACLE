# ORACLE Longevity Mission — Quality Audit

- Run ID: `run_a19934cc2692`
- Status: `completed`
- Question: Can we identify previously unknown biological mechanisms involved in human longevity?

## Counts

| Item | Count |
|---|---:|
| Sources | 256 |
| Evidence records | 51 |
| Candidate claims | 435 |
| Human-relevant sources (metadata screen) | 40 |
| Hypotheses | 2 |
| Differential-expression analyses | 0 |
| Dataset analyses | 0 |

## Quality gates

| Gate | Status |
|---|---|
| Literature prior-art / novelty | **not_established** |
| Human relevance | **human_sources_found** (study-level verification still required) |
| Independent evidence | **multiple_source_groups** (independence not proven) |
| Statistical support | **not_run** |
| Biological replication | **not_demonstrated** |
| Contradiction review | **none_recorded** |
| Dataset interpretation | **no_dataset_analysis** |
| Independent expert review | **required** |

## Hypotheses

- `hyp_b3e31af7f7f4`: longevity may involve multiple interacting mechanisms. Supporting evidence: 0; opposing evidence: 0; status: unverified candidate.
- `hyp_e5e7d942bb8f`: a dominant single mechanism may explain most of the question. Supporting evidence: 0; opposing evidence: 0; status: unverified candidate.

## Overall assessment

**screening_only_no_validated_discovery**

The run retrieved literature metadata/abstracts and citation links. One GEO supplementary count matrix (GSE351605) was downloaded, but the run did not parse it into a supported expression matrix or execute differential-expression analysis. No inferential statistics, independent-cohort feature replication, causal test, or physical experiment was performed. Optional Qwen reasoning timed out or returned invalid schema; the deterministic core completed.

## Limitations

- Full-text article bodies were not retrieved.
- NCBI GEO and GenBank requests encountered HTTP 429; PDB, PubChem and Zenodo lookups also failed or were not applicable.
- The 40 human-source count is a metadata screen, not a verified cohort-level assessment.
- 51 evidence source groups do not prove independent cohorts or participants.
- No independent expert annotations or blinded score files have been received.
- Novelty, causality, and clinical relevance remain unestablished.
