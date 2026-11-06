"""External SciFact scientific evidence benchmark.

Uses the public SciFact labelled dev/train claims and model predictions in the
official document/rationale format. It does not invent reviewer identities or
claim inter-reviewer agreement when the released corpus does not expose them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

LABEL_MAP = {"SUPPORT": "supports", "CONTRADICT": "refutes"}
LABELS = ("supports", "refutes", "contextual")


def _jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: each JSONL record must be an object")
            rows.append(row)
    return rows


def _hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _stance(labels: set[str]) -> str:
    if len(labels) == 1:
        return next(iter(labels))
    return "contextual"


def evaluate_scifact(claims_path: str | Path, corpus_path: str | Path,
                     predictions_path: str | Path, *, split: str = "dev") -> dict:
    if split not in {"train", "dev"}:
        raise ValueError("Only labelled SciFact train/dev splits can be scored; test gold labels are withheld")
    claims = _jsonl(claims_path)
    corpus = _jsonl(corpus_path)
    predictions = _jsonl(predictions_path)
    corpus_ids = {str(row.get("doc_id")) for row in corpus}
    if len(corpus_ids) != len(corpus):
        raise ValueError("SciFact corpus contains duplicate doc_id values")
    claim_by_id = {}
    for row in claims:
        cid = str(row.get("id"))
        if cid in claim_by_id or not cid or not isinstance(row.get("claim"), str):
            raise ValueError("SciFact claims require unique IDs and claim text")
        if "evidence" not in row:
            raise ValueError(f"Claim {cid} has no gold evidence field; use a labelled train/dev split")
        claim_by_id[cid] = row
    pred_by_id = {}
    for row in predictions:
        cid = str(row.get("id"))
        if cid not in claim_by_id or cid in pred_by_id:
            raise ValueError(f"Prediction claim ID {cid!r} is unknown or duplicated")
        evidence = row.get("evidence", {})
        if not isinstance(evidence, dict):
            raise ValueError(f"Prediction {cid}: evidence must be an object keyed by document ID")
        normalized = {}
        for doc_id, item in evidence.items():
            if str(doc_id) not in corpus_ids:
                raise ValueError(f"Prediction {cid}: document {doc_id} is absent from the supplied corpus")
            if not isinstance(item, dict) or item.get("label") not in LABEL_MAP:
                raise ValueError(f"Prediction {cid}/{doc_id}: label must be SUPPORT or CONTRADICT")
            sentences = item.get("sentences")
            if (not isinstance(sentences, list) or
                    any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in sentences) or
                    len(set(sentences)) != len(sentences)):
                raise ValueError(f"Prediction {cid}/{doc_id}: sentences must be unique non-negative indices")
            normalized[str(doc_id)] = {
                "label": LABEL_MAP[item["label"]],
                "sentences": set(sentences),
            }
        pred_by_id[cid] = normalized

    confusion = {gold: {pred: 0 for pred in LABELS} for gold in LABELS}
    gold_doc_count = pred_doc_count = correct_doc_count = 0
    gold_sentence_count = pred_sentence_count = correct_sentence_count = 0
    stance_correct = 0
    claim_rows = []
    for cid, claim in claim_by_id.items():
        gold_evidence = claim["evidence"]
        if not isinstance(gold_evidence, dict):
            raise ValueError(f"Claim {cid}: evidence must be an object")
        gold_labels: set[str] = set()
        gold_docs = {}
        for doc_id, rationales in gold_evidence.items():
            doc = str(doc_id)
            if doc not in corpus_ids:
                raise ValueError(f"Claim {cid}: gold evidence document {doc} absent from corpus")
            if not isinstance(rationales, list) or not rationales:
                raise ValueError(f"Claim {cid}/{doc}: evidence rationales must be a non-empty list")
            sets = []
            doc_labels = set()
            for rationale in rationales:
                if not isinstance(rationale, dict) or rationale.get("label") not in LABEL_MAP:
                    raise ValueError(f"Claim {cid}/{doc}: invalid gold evidence label")
                sentence_ids = rationale.get("sentences")
                if (not isinstance(sentence_ids, list) or not sentence_ids or
                        any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in sentence_ids)):
                    raise ValueError(f"Claim {cid}/{doc}: invalid gold sentence rationale")
                if len(set(sentence_ids)) != len(sentence_ids):
                    raise ValueError(f"Claim {cid}/{doc}: duplicate sentence indices")
                doc_labels.add(LABEL_MAP[rationale["label"]])
                sets.append(set(sentence_ids))
            if len(doc_labels) != 1:
                raise ValueError(f"Claim {cid}/{doc}: conflicting labels within a document are unsupported")
            label = next(iter(doc_labels))
            gold_labels.add(label)
            gold_docs[doc] = {"label": label, "rationales": sets}
        gold_stance = _stance(gold_labels)
        predicted = pred_by_id.get(cid, {})
        predicted_labels = {item["label"] for item in predicted.values()}
        predicted_stance = _stance(predicted_labels)
        confusion[gold_stance][predicted_stance] += 1
        stance_correct += int(gold_stance == predicted_stance)

        gold_doc_count += len(gold_docs)
        pred_doc_count += len(predicted)
        for doc, item in predicted.items():
            gold = gold_docs.get(doc)
            if gold and gold["label"] == item["label"] and any(
                    rationale.issubset(item["sentences"]) for rationale in gold["rationales"]):
                correct_doc_count += 1
        for doc, gold in gold_docs.items():
            gold_sentence_count += len(set().union(*gold["rationales"]))
        for doc, item in predicted.items():
            pred_sentence_count += len(item["sentences"])
            gold = gold_docs.get(doc)
            if gold and gold["label"] == item["label"]:
                credited_sentences = set()
                for rationale in gold["rationales"]:
                    if rationale.issubset(item["sentences"]):
                        credited_sentences.update(rationale)
                correct_sentence_count += len(credited_sentences)
        claim_rows.append({
            "claim_id": cid, "gold_stance": gold_stance,
            "predicted_stance": predicted_stance,
            "stance_correct": gold_stance == predicted_stance,
            "gold_evidence_documents": len(gold_docs),
            "predicted_evidence_documents": len(predicted),
        })

    def prf(correct, predicted, gold):
        precision = correct / predicted if predicted else None
        recall = correct / gold if gold else None
        f1 = (2 * precision * recall / (precision + recall)
              if precision is not None and recall is not None and precision + recall else None)
        return {"precision": precision, "recall": recall, "f1": f1,
                "correct": correct, "predicted": predicted, "gold": gold}

    return {
        "benchmark_type": "external_scifact_scientific_evidence",
        "dataset": "SciFact",
        "split": split,
        "claim_count": len(claim_by_id),
        "prediction_coverage": len(pred_by_id) / len(claim_by_id) if claim_by_id else 0.0,
        "stance_accuracy": stance_correct / len(claim_by_id) if claim_by_id else None,
        "stance_confusion_gold_rows_predicted_columns": confusion,
        "abstract_level_evidence": prf(correct_doc_count, pred_doc_count, gold_doc_count),
        "sentence_level_evidence": prf(correct_sentence_count, pred_sentence_count, gold_sentence_count),
        "claims": claim_rows,
        "provenance": {
            "claims_sha256": _hash(claims_path),
            "corpus_sha256": _hash(corpus_path),
            "predictions_sha256": _hash(predictions_path),
        },
        "limitations": (
            "SciFact provides expert-annotated scientific claims, cited abstracts, labels, and rationale "
            "sentences. The released files do not provide per-reviewer annotations, so this report does "
            "not calculate inter-reviewer agreement. SciFact dev/train is a scientific claim verification "
            "benchmark, not a complete measure of scientific reasoning, causal inference, or coverage of "
            "all disciplines. Predictions must be produced independently and frozen before scoring."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Score ORACLE predictions on labelled SciFact claims")
    parser.add_argument("--claims", required=True, help="SciFact claims_dev.jsonl or claims_train.jsonl")
    parser.add_argument("--corpus", required=True, help="SciFact corpus.jsonl")
    parser.add_argument("--predictions", required=True, help="Model predictions in official SciFact JSONL format")
    parser.add_argument("--split", choices=["train", "dev"], default="dev")
    args = parser.parse_args()
    print(json.dumps(evaluate_scifact(args.claims, args.corpus, args.predictions, split=args.split),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
