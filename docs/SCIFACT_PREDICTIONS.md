# Generate model predictions for the SciFact evidence benchmark

The scorer in `oracle.scifact_benchmark` evaluates frozen predictions against
SciFact's labelled train/dev claims. This generator creates predictions without
reading gold evidence labels.

## Download official data

Use the official SciFact repository's `claims_dev.jsonl` (or
`claims_train.jsonl`) and `corpus.jsonl`. Keep the original files unchanged;
their SHA-256 hashes are written into the prediction report.

## Generate a bounded prediction run

Set `GEMINI_API_KEY` in the process environment. It is read by the existing
ORACLE Gemini provider and is never written to disk.

```bash
python -m oracle.scifact_predict \
  --claims data/scifact/claims_dev.jsonl \
  --corpus data/scifact/corpus.jsonl \
  --predictions data/scifact/oracle-gemini-dev-predictions.jsonl \
  --report data/scifact/oracle-gemini-dev-run.json \
  --split dev --model gemini-2.5-flash --top-k 10 --max-claims 50
```

Retrieval is deterministic BM25 over the complete supplied corpus. Gemini sees
the claim and the top retrieved abstracts, not the gold evidence field. Each
predicted document must be in the retrieved set; each sentence index must be
valid; and the returned quote must match the selected abstract sentence text
exactly. Invalid or unsupported model output is discarded. Empty evidence is
retained as a contextual/no-evidence prediction.

## Score frozen predictions

```bash
python -m oracle --scifact-benchmark \
  --scifact-claims data/scifact/claims_dev.jsonl \
  --scifact-corpus data/scifact/corpus.jsonl \
  --scifact-predictions data/scifact/oracle-gemini-dev-predictions.jsonl \
  --scifact-split dev
```

The prediction run report and score report are separate artifacts. Record model,
prompt version, retrieval configuration, and all hashes. Start with a bounded
claim limit to control provider cost and quota. Do not score a prediction file
on a different split from the one recorded in its provenance.
