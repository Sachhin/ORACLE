# Blinded expert review packets

The paired evaluator requires each reviewer to score both the deterministic
baseline and candidate answer for the same frozen question and source packet.
This utility creates reviewer-specific packets with randomized A/B labels and
keeps the A/B-to-system mapping in separate private key files.

## Prepare the frozen input

Each case in the input JSON contains:

- `case_id`, `question`, and `source_packet`
- `baseline_answer` and `candidate_answer`
- `prompt_version` and `model_version` (record both systems and configurations)

The builder hashes the canonical source packet and each answer. If a
`source_packet_sha256` is supplied, it must match.

## Build packets

```bash
python -m oracle.blinded_review build \
  --input benchmarks/frozen_paired_answers.json \
  --output-dir data/blinded-review-round-01 \
  --reviewers reviewer_01 reviewer_02 reviewer_03 \
  --seed 1729
```

Distribute only `reviewer_packets/*.json` and their score templates. Never
send `private_unblinding_keys/*.key.json` to reviewers. Each reviewer receives
independently randomized A/B assignments. Freeze returned scores before
unblinding.

## Unblind and score

After reviewers return completed score templates:

```bash
python -m oracle.blinded_review unblind \
  --input benchmarks/frozen_paired_answers.json \
  --scores data/reviewed/reviewer_01.json data/reviewed/reviewer_02.json \
  --keys data/blinded-review-round-01/private_unblinding_keys/reviewer_01.key.json data/blinded-review-round-01/private_unblinding_keys/reviewer_02.key.json \
  --output benchmarks/paired_human_scores.json

python -m oracle --paired-answer-benchmark benchmarks/paired_human_scores.json
```

Unblinding verifies that every reviewer scored every case, both A/B answer
scores cover all five rubric dimensions, source packets are unchanged, and
model/prompt versions match. It then emits the schema consumed by the existing
case-level paired bootstrap evaluator.

This automates blinding and data integrity only. It does not recruit reviewers,
make expert judgments, or prove candidate superiority. Keep keys access-
controlled until annotations are locked.
