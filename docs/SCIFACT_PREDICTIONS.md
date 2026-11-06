# Generate ORACLE predictions on SciFact

The evaluator in `oracle.scifact_benchmark` scores frozen predictions; it does
not generate them. The new `oracle.scifact_predict` command supplies that
missing step using ORACLE's existing Gemini JSON provider.

## Reproducible prediction run

Download the official SciFact archive and extract it:

```bash
mkdir -p data/scifact
curl --fail --location --retry 4 \
  https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz \
  -o data/scifact/data.tar.gz
tar -xzf data/scifact/data.tar.gz -C data/scifact
```

Set `GEMINI_API_KEY` in the environment (never commit it), then generate
predictions without exposing the gold evidence labels to the model:

```bash
python -m oracle.scifact_predict \
  --claims data/scifact/claims_dev.jsonl \
  --corpus data/scifact/corpus.jsonl \
  --output data/scifact/oracle_predictions_dev.jsonl \
  --model gemini-2.5-flash --top-k 8
```

The retriever uses deterministic BM25 over titles and abstract text. Gemini
receives only the claim and retrieved abstracts; the code deliberately omits
gold evidence labels, cited-document IDs, and rationale sentence IDs. Model
outputs are rejected if they cite an unretrieved document, invent a sentence
index, or use an unsupported stance label. A metadata sidecar freezes model,
prompt, retrieval settings, and SHA-256 hashes.

Score the frozen predictions:

```bash
python -m oracle.scifact_benchmark \
  --claims data/scifact/claims_dev.jsonl \
  --corpus data/scifact/corpus.jsonl \
  --predictions data/scifact/oracle_predictions_dev.jsonl \
  --split dev > data/scifact/oracle_scifact_report.json
```

A manually dispatched GitHub Actions workflow performs these steps and uploads
the predictions, provenance sidecar, and score report. It requires a repository
Actions secret named `GEMINI_API_KEY`; no key is stored in the repository.
The default workflow evaluates the full selected labelled split. API quota or
network failure stops the run rather than substituting fabricated predictions.

## Interpretation

This is a model-plus-retriever benchmark, not a pure reasoning-only score.
Report retrieval coverage separately from stance and rationale metrics. The
SciFact train/dev gold labels are used only by the evaluator after prediction
generation. The released corpus does not provide per-reviewer annotations;
this benchmark cannot replace the independent human expert review protocol.
