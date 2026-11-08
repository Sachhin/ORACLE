# External evidence benchmark: SciFact

ORACLE includes an evaluator for the public SciFact scientific claim verification
dataset. SciFact supplies expert-written claims, evidence-containing abstracts,
SUPPORT/CONTRADICT labels, and rationale sentence IDs. Labelled train/dev claims
can be scored. The released test split withholds gold evidence labels and must
not be used to report accuracy, precision, recall, or F1.

## Two distinct prediction settings

- `scripts/predict_scifact_local.py` is an **oracle-cited-document diagnostic**:
  it receives each claim's published `cited_doc_ids`. It is not open-corpus
  retrieval and must not be described as such.
- `scripts/predict_scifact_open_corpus.py` performs **open-corpus BM25 retrieval**
  over the supplied corpus titles and abstracts, then asks an explicitly
  configured local model to classify retrieved evidence and cite sentence IDs.

The BM25 retriever is deterministic and dependency-free, but lexical rather than
semantic. The report includes post-inference gold-document recall as well as
downstream stance and evidence scores. The model prompt receives only the claim
and retrieved abstracts; gold labels, evidence document IDs, and rationale
indices are not exposed. Gold evidence is consulted after predictions are frozen
only to calculate retrieval diagnostics and benchmark scores.

## Download

Download the official archive from
https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz
and extract it locally. With the archive layout used by the Termux workflow, the
files are under `data/scifact/data/`:

- `claims_dev.jsonl` (300 labelled development claims)
- `claims_train.jsonl` (809 labelled training claims)
- `claims_test.jsonl` (300 claims with withheld gold labels)
- `corpus.jsonl` (5,183 abstracts)

## Run tests

```bash
python -m unittest tests.test_scifact_benchmark tests.test_scifact_local_predictor tests.test_scifact_open_corpus -v
```

## Run retrieval-only evaluation (no model required)

This measures how often lexical BM25 retrieves the expert-labelled evidence
documents from the full corpus. It runs locally without an LLM, API key, or
network request after the dataset is downloaded:

```bash
python scripts/evaluate_scifact_retrieval.py \
  --claims data/scifact/data/claims_dev.jsonl \
  --corpus data/scifact/data/corpus.jsonl \
  --top-k 20 \
  --output data/scifact/bm25_retrieval_dev.report.json
```

This produces real retrieval recall diagnostics, not claim-verification
accuracy. It is the first runnable open-corpus benchmark step on a device
without a local model server.

## Run an open-corpus pilot

Inference requires an explicitly configured operator-owned OpenAI-compatible
local model server, such as llama.cpp or Ollama. No Gemini API, hosted provider,
or vendor fallback is used. Without a running local model endpoint, only the
dataset checks and retriever tests can run; a complete model benchmark cannot
be claimed.

```bash
python scripts/predict_scifact_open_corpus.py \
  --claims data/scifact/data/claims_dev.jsonl \
  --corpus data/scifact/data/corpus.jsonl \
  --output data/scifact/open_corpus_dev_predictions.jsonl \
  --base-url http://127.0.0.1:8000/v1 \
  --model LOCAL_MODEL_NAME --top-k 20 --max-claims 10
```

Review the pilot report, then run all 300 dev claims by omitting
`--max-claims`. Use `--resume` to continue an interrupted run with the same
output file. Do not mix predictions from different models or retrieval settings.

The report records dataset/prediction hashes, prediction coverage, stance
accuracy, abstract- and sentence-level evidence precision/recall/F1, and
post-inference BM25 retrieval recall. These measurements do not prove general
scientific reasoning, causal inference, or biological discovery.

## Direct scoring of an existing prediction file

```bash
python -m oracle.scifact_benchmark \
  --claims data/scifact/data/claims_dev.jsonl \
  --corpus data/scifact/data/corpus.jsonl \
  --predictions data/scifact/open_corpus_dev_predictions.jsonl \
  --split dev
```

SciFact does not expose per-reviewer annotations, so ORACLE does not invent
reviewer IDs or report inter-reviewer agreement for this dataset.


## Run sentence-level retrieval-only evaluation (no model required)

This second model-free diagnostic ranks individual abstract sentences over the
entire corpus using BM25. It measures whether the top-ranked sentences recover
the expert rationale sentence IDs, including exact rationale-group recovery.
Gold rationale IDs are consulted only after rankings are frozen:

```bash
python scripts/evaluate_scifact_sentence_retrieval.py \
  --claims data/scifact/data/claims_dev.jsonl \
  --corpus data/scifact/data/corpus.jsonl \
  --top-k 10 \
  --output data/scifact/bm25_sentence_retrieval_dev.report.json
```

The report includes sentence precision/recall/F1, claim-level hit rate, and
fully retrieved rationale-group rate. This is still lexical retrieval only:
it does not classify SUPPORT/CONTRADICT, evaluate entailment, or generate
hypotheses. Run it on the labelled dev split for model-free validation; do not
use the unlabelled test split to claim benchmark scores.
