# External evidence benchmark: SciFact

ORACLE's SciFact tools are model-independent diagnostics for deterministic
lexical evidence retrieval and scoring of already-frozen prediction files.
They do not load, call, download, or configure an AI model.

SciFact supplies expert-written claims, evidence-containing abstracts,
SUPPORT/CONTRADICT labels, and rationale sentence IDs. Labelled train/dev claims
can be scored. The released test split withholds gold evidence labels and must
not be used to report accuracy, precision, recall, or F1.

## Download

Download the official archive from
https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz
and extract it locally. The expected files are under `data/scifact/data/`:

- `claims_dev.jsonl` (300 labelled development claims)
- `claims_train.jsonl` (809 labelled training claims)
- `claims_test.jsonl` (300 claims with withheld gold labels)
- `corpus.jsonl` (5,183 abstracts)

## Run the retrieval diagnostics

Document-level BM25 retrieval:

```bash
python scripts/evaluate_scifact_retrieval.py \
  --claims data/scifact/data/claims_dev.jsonl \
  --corpus data/scifact/data/corpus.jsonl \
  --top-k 20 \
  --output data/scifact/bm25_retrieval_dev.report.json
```

Sentence-level BM25 retrieval:

```bash
python scripts/evaluate_scifact_sentence_retrieval.py \
  --claims data/scifact/data/claims_dev.jsonl \
  --corpus data/scifact/data/corpus.jsonl \
  --top-k 10 \
  --output data/scifact/bm25_sentence_retrieval_dev.report.json
```

These tools report lexical retrieval coverage against the labelled development
set. They do not classify SUPPORT/CONTRADICT, evaluate entailment, establish
scientific reasoning, or generate hypotheses.

## Score a previously frozen prediction file

The evaluator can score a prediction file created outside the current
model-independent ORACLE runtime. Scoring does not run inference:

```bash
python -m oracle.scifact_benchmark \
  --claims data/scifact/data/claims_dev.jsonl \
  --corpus data/scifact/data/corpus.jsonl \
  --predictions PATH_TO_FROZEN_PREDICTIONS.jsonl \
  --split dev
```

Clearly label the provenance of any imported prediction file. Do not present
historical model-generated predictions as output from the current ORACLE
engine. Report prediction coverage separately from accuracy on scored claims.
SciFact does not expose per-reviewer annotations, so do not invent reviewer
IDs or report inter-reviewer agreement.
