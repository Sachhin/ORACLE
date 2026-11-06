"""Create blinded paired-answer review packets and unblind human scores."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any

from .answer_benchmark import DIMENSIONS, validate_answer_review


def _canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _safe_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    if not name:
        raise ValueError("Reviewer IDs must produce a safe non-empty file name")
    return name


def _load(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list) or not payload["cases"]:
        raise ValueError("Input must be a JSON object containing a non-empty cases list")
    return payload


def build_blinded_packets(input_path: str | Path, output_dir: str | Path,
                          reviewer_ids: list[str], *, seed: int = 1729) -> dict:
    payload = _load(input_path)
    if len(reviewer_ids) < 2 or any(not isinstance(x, str) or not x.strip() for x in reviewer_ids):
        raise ValueError("At least two non-empty reviewer IDs are required")
    if len(set(reviewer_ids)) != len(reviewer_ids):
        raise ValueError("Reviewer IDs must be unique")
    filenames = [_safe_name(x) for x in reviewer_ids]
    if len(set(filenames)) != len(filenames):
        raise ValueError("Reviewer IDs collide after safe filename conversion")
    case_ids = set()
    normalized = []
    for index, case in enumerate(payload["cases"]):
        if not isinstance(case, dict):
            raise ValueError(f"Case {index} must be an object")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip() or case_id in case_ids:
            raise ValueError(f"Case {index} requires a unique non-empty case_id")
        case_ids.add(case_id)
        for field in ("question", "source_packet", "baseline_answer", "candidate_answer",
                      "prompt_version", "model_version"):
            if field not in case:
                raise ValueError(f"Case {case_id} requires {field}")
        if not isinstance(case["question"], str) or not case["question"].strip():
            raise ValueError(f"Case {case_id} question must be non-empty text")
        if not isinstance(case["baseline_answer"], str) or not case["baseline_answer"].strip():
            raise ValueError(f"Case {case_id} baseline_answer must be non-empty text")
        if not isinstance(case["candidate_answer"], str) or not case["candidate_answer"].strip():
            raise ValueError(f"Case {case_id} candidate_answer must be non-empty text")
        source_hash = _canonical_hash(case["source_packet"])
        supplied_hash = case.get("source_packet_sha256")
        if supplied_hash is not None and supplied_hash != source_hash:
            raise ValueError(f"Case {case_id} source_packet_sha256 does not match frozen source_packet")
        normalized.append({
            "case_id": case_id, "question": case["question"],
            "source_packet": case["source_packet"],
            "source_packet_sha256": source_hash,
            "prompt_version": str(case["prompt_version"]),
            "model_version": str(case["model_version"]),
            "baseline_answer_sha256": hashlib.sha256(case["baseline_answer"].encode("utf-8")).hexdigest(),
            "candidate_answer_sha256": hashlib.sha256(case["candidate_answer"].encode("utf-8")).hexdigest(),
            "baseline_answer": case["baseline_answer"],
            "candidate_answer": case["candidate_answer"],
        })
    root = Path(output_dir)
    packet_dir, key_dir = root / "reviewer_packets", root / "private_unblinding_keys"
    packet_dir.mkdir(parents=True, exist_ok=True)
    key_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    created = []
    for reviewer, filename in zip(reviewer_ids, filenames):
        packet_cases, key_cases = [], {}
        for case in normalized:
            baseline_first = bool(rng.getrandbits(1))
            answer_a = case["baseline_answer"] if baseline_first else case["candidate_answer"]
            answer_b = case["candidate_answer"] if baseline_first else case["baseline_answer"]
            packet_cases.append({
                "case_id": case["case_id"], "question": case["question"],
                "source_packet": case["source_packet"],
                "source_packet_sha256": case["source_packet_sha256"],
                "answer_A": answer_a, "answer_B": answer_b,
            })
            key_cases[case["case_id"]] = {
                "A": "baseline" if baseline_first else "candidate",
                "B": "candidate" if baseline_first else "baseline",
                "prompt_version": case["prompt_version"],
                "model_version": case["model_version"],
                "baseline_answer_sha256": case["baseline_answer_sha256"],
                "candidate_answer_sha256": case["candidate_answer_sha256"],
            }
        packet = {
            "benchmark_id": payload.get("benchmark_id", "ORACLE-BLINDED-PAIRED-REVIEW"),
            "reviewer_id": reviewer,
            "blinded": True,
            "rubric_dimensions": list(DIMENSIONS),
            "score_scale": {"minimum": 1, "maximum": 5},
            "instructions": "Score answer A and answer B independently for every dimension. Do not guess system identity. Use the same question and source packet for both answers.",
            "cases": packet_cases,
        }
        score_template = {
            "reviewer_id": reviewer,
            "instructions": "Return one record per case with scores_A and scores_B, each containing all five rubric dimensions as integer scores 1-5.",
            "cases": [{
                "case_id": case["case_id"],
                "scores_A": {dimension: None for dimension in DIMENSIONS},
                "scores_B": {dimension: None for dimension in DIMENSIONS},
                "review_note": "",
            } for case in normalized],
        }
        packet_path = packet_dir / f"{filename}.json"
        template_path = packet_dir / f"{filename}.scores-template.json"
        key_path = key_dir / f"{filename}.key.json"
        packet_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        template_path.write_text(json.dumps(score_template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        key_path.write_text(json.dumps({
            "reviewer_id": reviewer, "seed": seed, "cases": key_cases,
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        created.append({
            "reviewer_id": reviewer,
            "packet": str(packet_path),
            "scores_template": str(template_path),
            "private_key": str(key_path),
        })
    return {
        "status": "BLINDED_PACKETS_CREATED",
        "case_count": len(normalized),
        "reviewer_count": len(reviewer_ids),
        "seed": seed,
        "created": created,
        "warning": "Distribute only reviewer_packets/*.json and score templates. Keep private_unblinding_keys/ inaccessible to reviewers until scoring is frozen.",
    }


def unblind_paired_reviews(input_path: str | Path, score_paths: list[str | Path],
                           key_paths: list[str | Path], output_path: str | Path) -> dict:
    payload = _load(input_path)
    if len(score_paths) < 2 or len(score_paths) != len(key_paths):
        raise ValueError("At least two matching reviewer score and private key files are required")
    source_cases = {case["case_id"]: case for case in payload["cases"]}
    if len(source_cases) != len(payload["cases"]):
        raise ValueError("Input case IDs must be unique")
    reviewer_ids, reviewers = [], {}
    for score_path, key_path in zip(score_paths, key_paths):
        scores = json.loads(Path(score_path).read_text(encoding="utf-8"))
        key = json.loads(Path(key_path).read_text(encoding="utf-8"))
        reviewer = scores.get("reviewer_id")
        if not isinstance(reviewer, str) or not reviewer.strip() or reviewer != key.get("reviewer_id"):
            raise ValueError("Score file and unblinding key reviewer IDs must match")
        if reviewer in reviewers:
            raise ValueError("Duplicate reviewer score file")
        score_cases = scores.get("cases")
        key_cases = key.get("cases")
        if not isinstance(score_cases, list) or not isinstance(key_cases, dict):
            raise ValueError(f"Reviewer {reviewer}: malformed score or key file")
        score_by_id = {item.get("case_id"): item for item in score_cases if isinstance(item, dict)}
        if len(score_by_id) != len(score_cases) or set(score_by_id) != set(source_cases) or set(key_cases) != set(source_cases):
            raise ValueError(f"Reviewer {reviewer}: score and key files must cover every case exactly once")
        normalized = {}
        for case_id, score in score_by_id.items():
            mapping = key_cases[case_id]
            if set(mapping) < {"A", "B", "prompt_version", "model_version"}:
                raise ValueError(f"Reviewer {reviewer}/{case_id}: incomplete unblinding key")
            a = validate_answer_review(score.get("scores_A", {}))
            b = validate_answer_review(score.get("scores_B", {}))
            if {mapping["A"], mapping["B"]} != {"baseline", "candidate"}:
                raise ValueError(f"Reviewer {reviewer}/{case_id}: invalid A/B key")
            normalized[case_id] = {
                "baseline_scores": a if mapping["A"] == "baseline" else b,
                "candidate_scores": a if mapping["A"] == "candidate" else b,
            }
        reviewer_ids.append(reviewer)
        reviewers[reviewer] = normalized
    final_cases = []
    for case_id, case in source_cases.items():
        source_hash = _canonical_hash(case["source_packet"])
        if case.get("source_packet_sha256") not in (None, source_hash):
            raise ValueError(f"Case {case_id}: source packet changed after review")
        case_reviewers = {
            reviewer: reviewers[reviewer][case_id] for reviewer in reviewer_ids
        }
        model_versions = {json.loads(Path(k).read_text(encoding="utf-8"))["cases"][case_id]["model_version"]
                          for k in key_paths}
        prompt_versions = {json.loads(Path(k).read_text(encoding="utf-8"))["cases"][case_id]["prompt_version"]
                           for k in key_paths}
        if len(model_versions) != 1 or len(prompt_versions) != 1:
            raise ValueError(f"Case {case_id}: reviewers did not use the same frozen model/prompt versions")
        final_cases.append({
            "case_id": case_id,
            "source_packet_sha256": source_hash,
            "prompt_version": next(iter(prompt_versions)),
            "model_version": next(iter(model_versions)),
            "reviewer_ids": reviewer_ids,
            "reviewer_scores": case_reviewers,
        })
    result = {
        "benchmark_id": payload.get("benchmark_id", "ORACLE-BLINDED-PAIRED-REVIEW"),
        "version": "1.0",
        "review_status": "UNBLINDED_FROZEN_HUMAN_SCORES",
        "reviewer_ids": reviewer_ids,
        "cases": final_cases,
    }
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"status": result["review_status"], "case_count": len(final_cases),
            "reviewer_count": len(reviewer_ids), "output": str(out)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build blinded ORACLE paired-answer review packets or unblind frozen scores")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--input", required=True)
    build.add_argument("--output-dir", required=True)
    build.add_argument("--reviewers", nargs="+", required=True)
    build.add_argument("--seed", type=int, default=1729)
    unblind = sub.add_parser("unblind")
    unblind.add_argument("--input", required=True)
    unblind.add_argument("--scores", nargs="+", required=True)
    unblind.add_argument("--keys", nargs="+", required=True)
    unblind.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "build":
        report = build_blinded_packets(args.input, args.output_dir, args.reviewers, seed=args.seed)
    else:
        report = unblind_paired_reviews(args.input, args.scores, args.keys, args.output)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
