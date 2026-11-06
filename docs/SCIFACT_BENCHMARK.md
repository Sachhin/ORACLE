# External evidence benchmark: SciFact

ORACLE includes a loader/evaluator for the public SciFact scientific claim
verification dataset. SciFact supplies expert-written scientific claims,
evidence-containing abstracts, SUPPORT/CONTRADICT labels, and rationale
sentence IDs. The labelled train/dev claims include cited abstracts without
annotated evidence; these are treated as contextual/insufficient evidence for
stance classification. The evaluator reports stance accuracy, abstract-level
evidence precision/recall/F1, and sentence-level evidence precision/recall/F1.

## Download

Download the official archive from
https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz
and extract it locally. Use the labelled `claims_dev.jsonl` split for final
development evaluation; do not use `claims_test.jsonl` because its gold labels
are withheld. The official corpus is `corpus.jsonl`.

## Prediction format

Predictions are one JSON object per claim, matching the SciFact submission
format:

```json
{"id": 52, "evidence": {"11": {"sentences": [11], "label": "SUPPORT"}}}
```

An empty `evidence` object means the system found no evidence for that claim.
Freeze model/provider/prompt versions and the source corpus before generating
predictions. Do not generate predictions using gold rationale sentences or
gold evidence-document IDs.

## Score

```bash
python -m oracle.scifact_benchmark \
  --claims data/scifact/claims_dev.jsonl \
  --corpus data/scifact/corpus.jsonl \
  --predictions data/scifact/oracle_predictions.jsonl \
  --split dev
```

The report hashes all inputs. Abstract-level scoring requires a predicted
document's stance to match and at least one complete gold rationale set to be
contained in the predicted sentence IDs. Sentence-level scoring credits only
complete rationale sets, following the official benchmark's rationale logic.

SciFact's released data does not expose individual reviewer annotations, so
ORACLE does not invent reviewer IDs or report Cohen's kappa for this corpus.
The existing human-adjudicated benchmark remains the route for reviewer-level
agreement and adjudication. SciFact is a curated evidence benchmark, not a
complete evaluation of scientific reasoning or causal discovery.
