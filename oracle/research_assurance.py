"""Model-free research assurance engines for ORACLE.

All outputs are deterministic screening results. They do not establish causality,
scientific novelty, or human expert approval.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


def _rows(value: Any) -> list[dict[str, Any]]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _text(value: Any) -> str:
    return str(value or "").strip()


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]{3,}", value.casefold())
            if token not in {"the", "and", "for", "with", "from", "that", "this", "are", "was"}}


def evidence_integrity_audit(payload: dict[str, Any]) -> dict[str, Any]:
    """Check referential integrity and minimum provenance fields without guessing."""
    run = payload.get("run", payload)
    if not isinstance(run, dict):
        raise ValueError("Input must be a run object or contain a run object")
    sources = _rows(run.get("sources"))
    evidence = _rows(run.get("evidence"))
    claims = _rows(run.get("claims"))
    links = _rows(run.get("evidence_claim_links"))
    source_ids = {_text(item.get("source_id")) for item in sources if _text(item.get("source_id"))}
    evidence_ids = {_text(item.get("evidence_id")) for item in evidence if _text(item.get("evidence_id"))}
    claim_ids = {_text(item.get("claim_id")) for item in claims if _text(item.get("claim_id"))}
    issues: list[dict[str, str]] = []

    def issue(severity: str, code: str, detail: str) -> None:
        issues.append({"severity": severity, "code": code, "detail": detail})

    if len(source_ids) != len(sources):
        issue("error", "SOURCE_ID_MISSING_OR_DUPLICATE", "Every source must have a unique non-empty source_id.")
    if len(evidence_ids) != len(evidence):
        issue("error", "EVIDENCE_ID_MISSING_OR_DUPLICATE", "Every evidence record must have a unique non-empty evidence_id.")
    if len(claim_ids) != len(claims):
        issue("error", "CLAIM_ID_MISSING_OR_DUPLICATE", "Every claim must have a unique non-empty claim_id.")

    for item in evidence:
        eid = _text(item.get("evidence_id")) or "<missing>"
        sid = _text(item.get("source_id"))
        kind = _text(item.get("kind")).casefold()
        if kind != "inference" and (not sid or sid not in source_ids):
            issue("error", "EVIDENCE_SOURCE_UNRESOLVED", f"Evidence {eid} has no resolvable source_id.")
        if kind == "inference" and sid and sid not in source_ids:
            issue("warning", "INFERENCE_SOURCE_UNRESOLVED", f"Inference {eid} references an unknown source_id.")
        if not _text(item.get("claim")):
            issue("warning", "EVIDENCE_CLAIM_EMPTY", f"Evidence {eid} has no claim text.")
    for item in links:
        cid, eid = _text(item.get("claim_id")), _text(item.get("evidence_id"))
        if cid not in claim_ids or eid not in evidence_ids:
            issue("error", "DANGLING_EVIDENCE_CLAIM_LINK",
                  f"Link references claim_id={cid or '<missing>'}, evidence_id={eid or '<missing>'}.")
        try:
            strength = float(item.get("strength", 1.0))
            if not 0.0 <= strength <= 1.0:
                raise ValueError
        except (TypeError, ValueError):
            issue("error", "INVALID_LINK_STRENGTH", "Evidence-claim link strength must be between 0 and 1.")
    for item in sources:
        sid = _text(item.get("source_id")) or "<missing>"
        if not (_text(item.get("url")) or _text(item.get("doi")) or _text(item.get("pmid"))
                or _text(item.get("pmcid")) or _text(item.get("dataset_accession"))):
            issue("warning", "SOURCE_LOCATOR_MISSING", f"Source {sid} has no URL, DOI, PMID, PMCID, or dataset accession.")
    errors = sum(item["severity"] == "error" for item in issues)
    return {
        "module": "evidence_integrity",
        "status": "PASS" if errors == 0 else "BLOCKED",
        "source_count": len(sources), "evidence_count": len(evidence),
        "claim_count": len(claims), "link_count": len(links),
        "error_count": errors, "warning_count": len(issues) - errors,
        "issues": issues,
        "scope": "Structural provenance checks only; source truth and scientific validity require inspection."
    }


def cross_dataset_validation(analyses: list[dict[str, Any]], *, fdr_threshold: float = 0.05,
                             minimum_datasets: int = 2) -> dict[str, Any]:
    """Summarise per-feature direction and FDR across distinct accessions."""
    if not 0 < fdr_threshold < 1:
        raise ValueError("fdr_threshold must be strictly between 0 and 1")
    if minimum_datasets < 2:
        raise ValueError("minimum_datasets must be at least 2")
    by_feature: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    skipped = 0
    for analysis in _rows(analyses):
        accession = _text(analysis.get("dataset_accession")).upper()
        if not accession:
            skipped += 1
            continue
        for result in _rows(analysis.get("results")):
            feature = _text(result.get("feature") or result.get("gene") or result.get("probe"))
            try:
                effect = float(result.get("log2_fold_change", result.get("logFC")))
                padj = float(result.get("p_value_adjusted_bh", result.get("padj", result.get("adj.P.Val"))))
            except (TypeError, ValueError):
                skipped += 1
                continue
            if not feature or not (-1e12 < effect < 1e12) or not 0 <= padj <= 1:
                skipped += 1
                continue
            # One observation per feature per accession. Repeated analysis rows do not
            # inflate the independent dataset count; the first valid record is retained.
            by_feature[feature].setdefault(accession, {
                "log2_fold_change": effect, "adjusted_p_value": padj,
                "direction": "positive" if effect > 0 else "negative" if effect < 0 else "zero",
                "significant": padj <= fdr_threshold,
            })
    summaries = []
    for feature, datasets in sorted(by_feature.items()):
        rows = list(datasets.items())
        significant = [(acc, row) for acc, row in rows if row["significant"] and row["direction"] != "zero"]
        directions = {row["direction"] for _, row in significant}
        replicated = len(significant) >= minimum_datasets
        summaries.append({
            "feature": feature,
            "dataset_count": len(rows),
            "significant_dataset_count": len(significant),
            "significant_datasets": sorted(acc for acc, _ in significant),
            "directional_concordance": (len(directions) == 1) if replicated else None,
            "classification": (
                "replicated_directionally_concordant_screen" if replicated and len(directions) == 1
                else "replicated_directional_conflict" if replicated
                else "single_dataset_signal" if len(significant) == 1
                else "not_replicated_at_threshold"
            ),
            "effects": {acc: row["log2_fold_change"] for acc, row in sorted(datasets.items())},
            "adjusted_p_values": {acc: row["adjusted_p_value"] for acc, row in sorted(datasets.items())},
        })
    return {
        "module": "cross_dataset_validation",
        "status": "SCREEN_COMPLETE" if analyses else "NOT_RUN",
        "fdr_threshold": fdr_threshold, "minimum_independent_datasets": minimum_datasets,
        "feature_count": len(summaries), "skipped_result_count": skipped,
        "features": summaries,
        "limitations": [
            "Distinct accession IDs are treated as distinct datasets, not proof of non-overlapping participants.",
            "This is a direction/FDR screen, not a pooled meta-analysis or causal test.",
            "Study design, tissue, platform, covariates, sample overlap and effect-size comparability require review."
        ]
    }


def novelty_screen(hypotheses: list[dict[str, Any]], prior_art: list[dict[str, Any]],
                   *, similarity_threshold: float = 0.35) -> dict[str, Any]:
    """Compare candidate text to supplied prior-art records; never certify novelty."""
    if not 0 < similarity_threshold <= 1:
        raise ValueError("similarity_threshold must be in (0, 1]")
    papers = _rows(prior_art)
    comparisons = []
    for hypothesis in _rows(hypotheses):
        statement = _text(hypothesis.get("statement"))
        terms = _tokens(statement)
        matches = []
        for paper in papers:
            text = " ".join(_text(paper.get(key)) for key in ("title", "abstract", "claim", "summary"))
            other = _tokens(text)
            score = len(terms & other) / len(terms | other) if terms and other else 0.0
            if score >= similarity_threshold:
                matches.append({
                    "title": _text(paper.get("title")) or "Untitled prior-art record",
                    "doi": _text(paper.get("doi")), "pmid": _text(paper.get("pmid")),
                    "similarity": round(score, 4)
                })
        matches.sort(key=lambda item: item["similarity"], reverse=True)
        comparisons.append({
            "hypothesis_id": _text(hypothesis.get("hypothesis_id")),
            "statement": statement,
            "prior_art_records_compared": len(papers),
            "closest_matches": matches[:5],
            "screen_status": "possible_prior_art_overlap" if matches else "no_overlap_detected_in_supplied_records",
            "novelty_conclusion": "NOT_ESTABLISHED",
        })
    return {
        "module": "novelty_screen", "status": "SCREEN_COMPLETE" if papers else "PRIOR_ART_NOT_SUPPLIED",
        "hypothesis_count": len(comparisons), "prior_art_record_count": len(papers),
        "comparisons": comparisons,
        "limitations": "Text similarity is a retrieval aid, not an exhaustive literature search, patent search, or novelty determination."
    }


def skeptic_review(payload: dict[str, Any], cross_dataset_report: dict[str, Any] | None = None) -> dict[str, Any]:
    """Generate deterministic falsification prompts and evidence-quality warnings."""
    run = payload.get("run", payload)
    if not isinstance(run, dict):
        raise ValueError("Input must be a run object or contain a run object")
    evidence = _rows(run.get("evidence"))
    sources = _rows(run.get("sources"))
    source_ids = {_text(item.get("source_id")) for item in sources}
    evidence_by_id = {_text(item.get("evidence_id")): item for item in evidence if _text(item.get("evidence_id"))}
    replicated = {}
    if cross_dataset_report:
        replicated = {item.get("feature"): item for item in cross_dataset_report.get("features", [])}
    reviews = []
    for hypothesis in _rows(run.get("hypotheses")):
        statement = _text(hypothesis.get("statement"))
        refs = [_text(x) for x in (hypothesis.get("supporting_evidence_ids") or []) if _text(x)]
        linked = [evidence_by_id[x] for x in refs if x in evidence_by_id]
        source_backed = [item for item in linked if _text(item.get("source_id")) in source_ids
                         and _text(item.get("kind")).casefold() != "inference"]
        flags = []
        if not source_backed:
            flags.append("No source-backed supporting evidence is linked.")
        if not _text(hypothesis.get("predictions")):
            flags.append("No explicit, falsifiable prediction is recorded.")
        if not (_text(hypothesis.get("opposing_evidence_ids"))):
            flags.append("No opposing evidence is linked; actively search for counterexamples.")
        if re.search(r"\b(causes?|drives?|determines?|prevents?|proves?)\b", statement, re.I):
            flags.append("Causal wording requires a design capable of supporting causal inference.")
        if len(_tokens(statement)) < 5:
            flags.append("Hypothesis may be too vague to operationalise.")
        conflicts = [feature for feature, row in replicated.items()
                     if row.get("classification") == "replicated_directional_conflict"
                     and feature.casefold() in statement.casefold()]
        if conflicts:
            flags.append("Cross-dataset direction conflict detected for: " + ", ".join(conflicts))
        reviews.append({
            "hypothesis_id": _text(hypothesis.get("hypothesis_id")),
            "status": "REQUIRES_ADVERSARIAL_REVIEW" if flags else "NO_AUTOMATED_RED_FLAGS",
            "source_backed_support_count": len(source_backed),
            "flags": flags,
            "falsification_questions": [
                "What result would make this hypothesis unlikely or false?",
                "Could age, sex, tissue composition, batch, medication, or survival/selection bias explain the association?",
                "Does the result persist in a genuinely independent cohort and under reasonable analysis choices?",
                "What is the strongest published counterexample or competing mechanism?"
            ]
        })
    return {
        "module": "skeptic_review", "status": "SCREEN_COMPLETE",
        "hypothesis_count": len(reviews), "reviews": reviews,
        "scope": "Deterministic red-team prompts; not an independent human or model peer review."
    }


def discover_mechanism_candidates(cross_dataset_report: dict[str, Any],
                                  annotations: list[dict[str, Any]] | None = None,
                                  novelty_report: dict[str, Any] | None = None) -> dict[str, Any]:
    """Promote only replicated feature screens with explicit annotation provenance."""
    annotation_rows = _rows(annotations or [])
    annotation_map = {_text(item.get("feature")): item for item in annotation_rows if _text(item.get("feature"))}
    candidates = []
    for feature in cross_dataset_report.get("features", []):
        if feature.get("classification") != "replicated_directionally_concordant_screen":
            continue
        annotation = annotation_map.get(_text(feature.get("feature")), {})
        candidates.append({
            "feature": feature.get("feature"),
            "direction": "positive" if all(value > 0 for value in feature.get("effects", {}).values()) else "negative",
            "supporting_dataset_accessions": feature.get("significant_datasets", []),
            "annotation": _text(annotation.get("annotation")),
            "pathway": _text(annotation.get("pathway")),
            "annotation_source": _text(annotation.get("source_url")),
            "candidate_status": "REPLICATED_ASSOCIATION_CANDIDATE",
            "mechanism_status": "NOT_ESTABLISHED",
            "novelty_status": "NOT_ESTABLISHED",
            "next_step": "Validate annotation provenance, cohort independence, tissue context, confounding and functional mechanism."
        })
    return {
        "module": "mechanism_discovery",
        "status": "CANDIDATES_FOUND" if candidates else "NO_REPLICATED_CANDIDATES",
        "candidate_count": len(candidates), "candidates": candidates,
        "limitations": "Replicated gene-level associations are not mechanisms. Pathway labels require a source URL and independent biological validation."
    }


def prioritize_experiments(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Rank proposed validation experiments using transparent, user-supplied 1–5 inputs."""
    ranked = []
    for index, item in enumerate(_rows(candidates), start=1):
        name = _text(item.get("name") or item.get("hypothesis") or item.get("question")) or f"candidate_{index}"
        dimensions = {}
        for key, default in (("feasibility", 3), ("information_gain", 3), ("falsifiability", 3), ("data_readiness", 3)):
            try:
                value = float(item.get(key, default))
            except (TypeError, ValueError):
                raise ValueError(f"{name}: {key} must be between 1 and 5")
            if not 1 <= value <= 5:
                raise ValueError(f"{name}: {key} must be between 1 and 5")
            dimensions[key] = value
        score = (dimensions["feasibility"] * 0.30 + dimensions["information_gain"] * 0.30
                 + dimensions["falsifiability"] * 0.25 + dimensions["data_readiness"] * 0.15)
        ranked.append({
            "name": name, "priority_score": round(score, 3), "dimensions": dimensions,
            "proposed_validation": _text(item.get("proposed_validation")),
            "required_controls": _text(item.get("required_controls")),
            "status": "PROPOSED_NOT_EXECUTED"
        })
    ranked.sort(key=lambda item: (-item["priority_score"], item["name"]))
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank
    return {
        "module": "experiment_prioritization", "status": "RANKED" if ranked else "NO_CANDIDATES",
        "weights": {"feasibility": 0.30, "information_gain": 0.30, "falsifiability": 0.25, "data_readiness": 0.15},
        "experiments": ranked,
        "scope": "Transparent planning heuristic; rankings are not empirical outcomes or evidence of execution."
    }


def run_research_assurance(payload: dict[str, Any]) -> dict[str, Any]:
    """Run all five replacement modules against one ORACLE run/artifact bundle."""
    run = payload.get("run", payload)
    if not isinstance(run, dict):
        raise ValueError("Input must be a run object or contain a run object")
    analyses = _rows(run.get("differential_expression_analyses"))
    cross = cross_dataset_validation(analyses) if analyses else cross_dataset_validation([])
    integrity = evidence_integrity_audit(payload)
    novelty = novelty_screen(_rows(run.get("hypotheses")), _rows(payload.get("prior_art")))
    skeptic = skeptic_review(payload, cross)
    discovery = discover_mechanism_candidates(cross, _rows(payload.get("annotations")), novelty)
    experiments = prioritize_experiments(_rows(payload.get("experiment_candidates")))
    return {
        "assurance_version": "1.0.0",
        "status": "SCREEN_COMPLETE",
        "modules": {
            "evidence_integrity": integrity,
            "cross_dataset_validation": cross,
            "mechanism_discovery": discovery,
            "novelty_screen": novelty,
            "skeptic_review": skeptic,
            "experiment_prioritization": experiments
        },
        "release_caution": "This report does not replace source-authenticated CRA000515 labels, the PXD047528 clinical crosswalk, genuine independent human review, or experimental validation."
    }
