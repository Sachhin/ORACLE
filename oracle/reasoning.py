"""API-free, provenance-aware scientific reasoning primitives.

These deterministic methods organize evidence and generate reviewable candidates.
They do not establish causality, novelty, or scientific truth.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import re

from .models import Evidence, EvidenceKind, Hypothesis

_STOP_WORDS = {
    "about", "after", "against", "among", "also", "and", "are", "because",
    "been", "being", "between", "both", "can", "could", "does", "during",
    "from", "have", "into", "involved", "into", "involve", "involving",
    "identify", "human", "how", "into", "its", "may", "mechanism",
    "mechanisms", "more", "most", "new", "our", "over", "previously",
    "should", "some", "such", "than", "that", "their", "there", "these",
    "this", "those", "through", "under", "unknown", "what", "which",
    "while", "with", "within", "would", "the", "for", "was", "were",
    "are", "is", "of", "to", "a", "an", "on", "by", "as", "at", "or",
}

_TOKEN_RE = re.compile(r"[a-z][a-z0-9-]{2,}", re.IGNORECASE)


def terms(text: str) -> set[str]:
    """Return normalized content terms; intentionally lexical, not semantic."""
    return {
        token.casefold().strip("-")
        for token in _TOKEN_RE.findall(text or "")
        if token.casefold() not in _STOP_WORDS
    }


@dataclass(frozen=True)
class EvidenceGap:
    term: str
    evidence_count: int
    evidence_ids: tuple[str, ...] = ()


@dataclass
class ReasoningReport:
    question_terms: list[str] = field(default_factory=list)
    covered_terms: list[str] = field(default_factory=list)
    gaps: list[EvidenceGap] = field(default_factory=list)
    source_backed_evidence_count: int = 0
    independent_source_groups: int = 0
    warnings: list[str] = field(default_factory=list)


def analyze_evidence_gaps(question: str, evidence: list[Evidence]) -> ReasoningReport:
    """Measure lexical coverage of mission terms by evidence records.

    A gap means 'not mentioned in the supplied evidence text', not that a
    scientific topic is genuinely unknown in the literature.
    """
    mission_terms = sorted(terms(question))
    evidence_terms: dict[str, list[str]] = defaultdict(list)
    source_backed = [
        item for item in evidence
        if item.kind != EvidenceKind.INFERENCE and bool(item.source_id)
    ]
    for item in evidence:
        for token in terms(item.claim):
            evidence_terms[token].append(item.evidence_id)

    covered = [token for token in mission_terms if evidence_terms.get(token)]
    gaps = [
        EvidenceGap(token, len(set(evidence_terms.get(token, []))),
                    tuple(sorted(set(evidence_terms.get(token, [])))))
        for token in mission_terms if not evidence_terms.get(token)
    ]
    groups = {
        item.dependence_group.strip() or item.source_id
        for item in source_backed
    }
    warnings = [
        "Lexical coverage is not semantic understanding; synonyms and context may be missed.",
        "An uncovered term is a retrieval/coverage gap, not proof that the science is unknown.",
    ]
    if not source_backed:
        warnings.append("No source-backed evidence is available; scientific hypotheses must remain ungenerated.")
    return ReasoningReport(
        question_terms=mission_terms,
        covered_terms=covered,
        gaps=gaps,
        source_backed_evidence_count=len(source_backed),
        independent_source_groups=len(groups),
        warnings=warnings,
    )


def generate_competing_hypotheses(
    question: str, evidence: list[Evidence], max_candidates: int = 4,
) -> list[Hypothesis]:
    """Generate conservative co-mention candidates from independent sourced evidence.

    Co-mention is only a discovery heuristic. Each candidate explicitly requires
    follow-up testing and must not be described as a discovered mechanism.
    """
    if not 1 <= max_candidates <= 20:
        raise ValueError("max_candidates must be between 1 and 20.")
    eligible = [
        item for item in evidence
        if item.kind != EvidenceKind.INFERENCE and item.source_id
    ]
    if len(eligible) < 2:
        return []

    by_term: dict[str, list[Evidence]] = defaultdict(list)
    for item in eligible:
        for token in terms(item.claim):
            by_term[token].append(item)

    pairs: Counter[tuple[str, str]] = Counter()
    for item_list in by_term.values():
        unique = {item.evidence_id: item for item in item_list}
        items = list(unique.values())
        for i, left in enumerate(items):
            for right in items[i + 1:]:
                if left.source_id != right.source_id:
                    pair = tuple(sorted((left.evidence_id, right.evidence_id)))
                    pairs[pair] += 1

    ranked = sorted(pairs.items(), key=lambda entry: (-entry[1], entry[0]))
    candidates: list[Hypothesis] = []
    evidence_by_id = {item.evidence_id: item for item in eligible}
    for (left_id, right_id), shared_terms in ranked[:max_candidates]:
        left, right = evidence_by_id[left_id], evidence_by_id[right_id]
        shared = sorted(terms(left.claim) & terms(right.claim))
        if not shared:
            continue
        anchor = ", ".join(shared[:3])
        statement = (
            f"Across the supplied sources, the recurring relationship involving "
            f"{anchor} may represent a candidate mechanism relevant to: {question}"
        )
        rationale = (
            "Generated by cross-source lexical co-mention, not by causal inference. "
            f"Candidate evidence IDs: {left_id}, {right_id}. "
            "Independent replication and confounder-aware analysis are required."
        )
        prediction = (
            f"If this candidate relationship is real, an independently collected "
            f"dataset should show a pre-specified association involving {anchor} "
            "after adjustment for plausible confounders."
        )
        candidates.append(Hypothesis(
            statement=statement,
            rationale=rationale,
            predictions=[prediction],
            confidence="very low",
        ))
    return candidates


def skeptic_checks(
    hypotheses: list[Hypothesis], evidence: list[Evidence],
) -> list[str]:
    """Return deterministic integrity warnings; never auto-accept a hypothesis."""
    warnings: list[str] = []
    source_backed = {
        item.evidence_id: item for item in evidence
        if item.kind != EvidenceKind.INFERENCE and item.source_id
    }
    if not hypotheses:
        warnings.append("No evidence-grounded hypothesis candidates were generated.")
    for hypothesis in hypotheses:
        if not hypothesis.predictions:
            warnings.append(f"{hypothesis.hypothesis_id}: no falsifiable prediction recorded.")
        cited = set(hypothesis.supporting_evidence_ids + hypothesis.opposing_evidence_ids)
        if any(evidence_id not in source_backed for evidence_id in cited):
            warnings.append(f"{hypothesis.hypothesis_id}: contains a non-source-backed evidence link.")
        groups = {
            source_backed[evidence_id].dependence_group.strip()
            or source_backed[evidence_id].source_id
            for evidence_id in cited if evidence_id in source_backed
        }
        if len(groups) < 2:
            warnings.append(
                f"{hypothesis.hypothesis_id}: fewer than two independent evidence groups are linked."
            )
    warnings.append(
        "Lexical co-mention and heuristic ranking do not demonstrate causality or novelty."
    )
    return warnings
