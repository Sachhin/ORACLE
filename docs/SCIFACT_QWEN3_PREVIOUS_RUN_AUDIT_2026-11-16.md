# Audit of previous Qwen3 SciFact run artifact — 2026-11-16

## Frozen artifact

- GitHub Actions artifact ID: `14116895299`
- Downloaded archive: `qwen3-previous-full-benchmark.zip`
- Archive SHA-256: `6f5a03ff3c32ceeb4967f6562698696d2ddf2aba2519cf707ffb86110d805bd8`
- Model in the artifact: **Qwen3-0.6B** (this is not the newer pinned Qwen3-1.7B workflow model).
- Dataset: SciFact dev, 300 labelled claims, 5,183 corpus documents.

## Verified report

| Metric | Observed |
|---|---:|
| Claims in dev split | 300 |
| Scored predictions | 243 |
| Prediction coverage | 81.0% |
| Stance accuracy on scored claims | 40.33% |
| Predicted evidence documents | 508 |
| Gold evidence documents | 173 |
| Correct evidence documents | 0 |
| Sentence-level evidence predictions | 0 |
| Gold evidence sentences | 304 |
| Sentence-level evidence recall | 0% |
| Invalid model responses | 31 |

The 243 prediction rows contain 508 document-level evidence entries. **All 508 entries have empty sentence arrays**. Labels are 507 SUPPORT and 1 CONTRADICT. Thus the apparent document-level evidence is not sentence-grounded and earns zero sentence-level evidence credit. The model also never predicts REFUTE at the claim-level aggregation in the report.

## Root-cause diagnosis from the error sidecar

- 30 of 31 invalid responses ended with a single period after otherwise parseable JSON. Example: `{"evidence":[...] }.`
- One response cited document ID `5448237`, which was not in the candidate set for that claim.
- The parser fix accepting one terminal period is already on main.
- The former validator allowed evidence entries with omitted or empty `sentences`, which is how 508 ungrounded document labels passed validation.
- The previous run stopped after the invalid-response limit was exceeded, explaining why only 243 of 300 claims were scored.

## Corrective engineering now in progress

PR #127 aligned the Qwen3 preflight and full-run generation cap to 192 tokens and was merged after Python 3.10–3.14 plus live R/Bioconductor checks passed.

PR #129 adds strict evidence grounding:
- every predicted evidence document must cite 1–3 supplied sentence indices;
- at most two evidence documents per claim;
- explicit distinction between CONTRADICT and merely topical/unrelated material;
- retry guidance repeats these constraints;
- regression tests reject empty citations, overlong sentence lists, and too many documents.

## Scientific interpretation and release decision

The previous run is a **failed/incomplete baseline**, not a successful SciFact benchmark. Its 40.33% stance accuracy is conditional on the 243 scored claims and is not directly comparable to full-coverage runs. The zero sentence-level recall is a decisive evidence-grounding failure.

Do not report improved accuracy until a fresh run with the pinned Qwen3-1.7B model produces a complete prediction file and its report, invalid-response sidecar, retrieval metrics, and model provenance have been inspected. If strict sentence-grounding validation lowers coverage, report the invalid/abstention rate rather than weakening the validator.
