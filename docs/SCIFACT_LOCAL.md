# Local-model SciFact evaluation

ORACLE can create frozen SciFact predictions using an explicitly configured
self-hosted model such as llama.cpp on the operator's phone. No hosted LLM API,
API key, or model-provider integration is used.

## Download the public benchmark

From the repository root:

```bash
mkdir -p data/scifact
curl -L --fail --retry 3 \
  https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz \
  -o data/scifact/data.tar.gz
tar -xzf data/scifact/data.tar.gz -C data/scifact
```

The extracted files should include `claims_dev.jsonl` and `corpus.jsonl`.
Use the labelled dev split only for evaluation; the hidden test labels are not
available for local scoring.

## Generate a small pilot

Start the local llama.cpp server on loopback (for example,
`http://127.0.0.1:8080`), then run:

```bash
python scripts/predict_scifact_local.py \
  --claims data/scifact/claims_dev.jsonl \
  --corpus data/scifact/corpus.jsonl \
  --output data/scifact/oracle-local-pilot.jsonl \
  --base-url http://127.0.0.1:8080/v1 \
  --model Qwen3 \
  --max-tokens 512 \
  --timeout 180 \
  --max-claims 20
```

After inspecting the pilot, run the complete dev split:

```bash
python scripts/predict_scifact_local.py \
  --claims data/scifact/claims_dev.jsonl \
  --corpus data/scifact/corpus.jsonl \
  --output data/scifact/oracle-local-dev.jsonl \
  --base-url http://127.0.0.1:8080/v1 \
  --model Qwen3 \
  --max-tokens 512 \
  --timeout 180
```

If inference is interrupted, rerun the same command with `--resume`. Existing
claim IDs in the output are skipped. The script writes a frozen prediction
JSONL and a companion `.report.json` with coverage, stance accuracy,
abstract/sentence evidence metrics, input/output hashes, and model provenance.

## Evaluation scope and safeguards

This is **oracle-cited-document retrieval**: the model receives the claim and
the candidate document IDs supplied in SciFact's `cited_doc_ids`. It does not
search the full corpus. The model prompt deliberately excludes the gold
`evidence` labels and rationale sentence indices. Output document IDs,
labels, and sentence indices are validated against the supplied candidates
and abstracts; malformed or out-of-range predictions are rejected.

An empty evidence list means no direct evidence was found among the supplied
cited documents. This is not proof that the claim is false or unsupported in
the wider literature. Scores from a small local model are empirical results
for this specific model, prompt, and retrieval setting—not a general measure
of scientific reasoning, causal inference, or discovery ability. Preserve the
prediction file and report hashes; do not compare runs unless their split,
candidate set, prompt, and model provenance are recorded.
