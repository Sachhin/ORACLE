"""Cross-run research portfolio and transparent knowledge-gap heuristics.

Scores describe missing coverage in ORACLE's current records, not scientific truth,
novelty, or probability. Similar-question matching is lexical only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import EvidenceKind, EvidenceStance, ResearchRun
from .storage import ResearchStore


@dataclass
class KnowledgeGapAssessment:
    run_id: str
    question: str
    score: int
    criteria: dict[str, float]
    gaps: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)


class KnowledgeGapAssessor:
    """Score evidence coverage gaps using documented, reproducible ratios."""

    WEIGHTS = {
        "source_coverage_gap": 30.0,
        "claim_review_gap": 30.0,
        "hypothesis_evidence_gap": 20.0,
        "contradiction_gap": 15.0,
        "task_completion_gap": 5.0,
    }

    def assess(self, run: ResearchRun) -> KnowledgeGapAssessment:
        source_ids = {source.source_id for source in run.sources}
        source_evidence = [
            item for item in run.evidence
            if item.kind != EvidenceKind.INFERENCE
            and item.source_id and item.source_id in source_ids
        ]
        source_evidence_ids = {item.evidence_id for item in source_evidence}
        candidate_claims = [
            claim for claim in run.claims
            if claim.status in {"unreviewed_candidate", "unassessed"}
        ]
        reviewed_claim_ids = {
            link.claim_id for link in run.evidence_claim_links
            if link.evidence_id in source_evidence_ids
            and link.stance in {EvidenceStance.SUPPORTS, EvidenceStance.REFUTES}
            and link.strength > 0
        }
        reviewed_candidates = sum(
            1 for claim in candidate_claims if claim.claim_id in reviewed_claim_ids
        )
        hypotheses_with_evidence = sum(
            1 for hypothesis in run.hypotheses
            if (set(hypothesis.supporting_evidence_ids)
                | set(hypothesis.opposing_evidence_ids)) & source_evidence_ids
        )
        unresolved_contradictions = sum(
            1 for item in run.contradiction_candidates
            if item.status in {"pending_review", "needs_context"}
        )
        completed_tasks = sum(1 for task in run.tasks if task.status == "completed")

        source_coverage = min(1.0, len(source_evidence) / 5.0)
        claim_review_coverage = (
            reviewed_candidates / len(candidate_claims) if candidate_claims else 0.0
        )
        hypothesis_coverage = (
            hypotheses_with_evidence / len(run.hypotheses) if run.hypotheses else 0.0
        )
        contradiction_resolution = (
            1.0 - unresolved_contradictions / len(run.contradiction_candidates)
            if run.contradiction_candidates else 1.0
        )
        task_completion = completed_tasks / len(run.tasks) if run.tasks else 0.0

        criteria = {
            "source_coverage_gap": round(1.0 - source_coverage, 4),
            "claim_review_gap": round(1.0 - claim_review_coverage, 4),
            "hypothesis_evidence_gap": round(1.0 - hypothesis_coverage, 4),
            "contradiction_gap": round(1.0 - contradiction_resolution, 4),
            "task_completion_gap": round(1.0 - task_completion, 4),
        }
        score = round(sum(self.WEIGHTS[key] * value for key, value in criteria.items()))
        gaps = []
        if not source_evidence:
            gaps.append("No source-backed evidence is currently linked to this research run.")
        elif len(source_evidence) < 5:
            gaps.append(f"Only {len(source_evidence)} source-backed evidence records are stored; coverage is limited.")
        if not candidate_claims:
            gaps.append("No reviewable candidate or unassessed claims are recorded.")
        elif reviewed_candidates < len(candidate_claims):
            gaps.append(
                f"{len(candidate_claims) - reviewed_candidates} candidate claim(s) lack accepted support/refute evidence links."
            )
        if not run.hypotheses:
            gaps.append("No competing hypotheses are recorded.")
        elif hypotheses_with_evidence < len(run.hypotheses):
            gaps.append(
                f"{len(run.hypotheses) - hypotheses_with_evidence} hypothesis(es) lack linked supporting or opposing evidence."
            )
        if unresolved_contradictions:
            gaps.append(f"{unresolved_contradictions} contradiction candidate(s) remain unresolved.")
        pending_tasks = len(run.tasks) - completed_tasks
        if pending_tasks:
            gaps.append(f"{pending_tasks} planned research task(s) are not marked completed.")
        if not gaps:
            gaps.append("No gaps were detected by this limited record-coverage heuristic; scientific completeness is not established.")

        return KnowledgeGapAssessment(
            run_id=run.run_id, question=run.question, score=score,
            criteria=criteria, gaps=gaps,
            counts={
                "sources": len(run.sources),
                "source_backed_evidence": len(source_evidence),
                "claims": len(run.claims),
                "reviewable_claims": len(candidate_claims),
                "reviewed_claims": reviewed_candidates,
                "hypotheses": len(run.hypotheses),
                "hypotheses_with_evidence": hypotheses_with_evidence,
                "contradictions": len(run.contradiction_candidates),
                "unresolved_contradictions": unresolved_contradictions,
                "tasks": len(run.tasks),
                "completed_tasks": completed_tasks,
            },
        )


class ResearchPortfolio:
    """Browse prior runs and retrieve lexically related questions."""

    STOPWORDS = {
        "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for",
        "from", "how", "in", "into", "is", "of", "on", "or", "the", "to", "what",
        "when", "where", "which", "why", "with",
    }

    def __init__(self, store: ResearchStore):
        self.store = store
        self.assessor = KnowledgeGapAssessor()

    @classmethod
    def _tokens(cls, text: str) -> set[str]:
        return {
            token for token in re.findall(r"[a-z0-9]{2,}", text.casefold())
            if token not in cls.STOPWORDS
        }

    def list_entries(self, limit: int = 100) -> list[dict]:
        entries = []
        for item in self.store.list_runs(limit):
            run = self.store.load_run(item["run_id"])
            if run is None:
                continue
            assessment = self.assessor.assess(run)
            entries.append({
                **item,
                "sources": len(run.sources),
                "evidence": len(run.evidence),
                "claims": len(run.claims),
                "hypotheses": len(run.hypotheses),
                "dataset_files": len(run.dataset_files),
                "citation_links": len(run.citation_links),
                "knowledge_gap_score": assessment.score,
            })
        return entries

    def assess(self, run_id: str) -> KnowledgeGapAssessment:
        run = self.store.load_run(run_id)
        if run is None:
            raise ValueError(f"Research run not found: {run_id}")
        return self.assessor.assess(run)


    def cross_run_claim_candidates(self, run_id: str, limit: int = 50) -> list[dict]:
        """Queue lexical claim pairs with source-backed links in separate runs."""
        target = self.store.load_run(run_id)
        if target is None:
            raise ValueError(f"Research run not found: {run_id}")
        existing = set()
        for item in self.store.list_cross_run_claim_links():
            existing.add((item["run_a_id"], item["claim_a_id"], item["run_b_id"], item["claim_b_id"]))
            existing.add((item["run_b_id"], item["claim_b_id"], item["run_a_id"], item["claim_a_id"]))
        def grounded(run, claim_id):
            source_ids = {source.source_id for source in run.sources}
            evidence = {item.evidence_id: item for item in run.evidence}
            return sorted({
                link.evidence_id for link in run.evidence_claim_links
                if link.claim_id == claim_id and link.evidence_id in evidence
                and evidence[link.evidence_id].source_id in source_ids
                and evidence[link.evidence_id].source_id
                and evidence[link.evidence_id].kind != EvidenceKind.INFERENCE
            })
        matches = []
        for entry in self.store.list_runs(500):
            if entry["run_id"] == run_id:
                continue
            other = self.store.load_run(entry["run_id"])
            if other is None:
                continue
            for left in target.claims:
                evidence_a = grounded(target, left.claim_id)
                tokens_a = self._tokens(left.statement)
                if not evidence_a or not tokens_a:
                    continue
                for right in other.claims:
                    evidence_b = grounded(other, right.claim_id)
                    if not evidence_b:
                        continue
                    key = (target.run_id, left.claim_id, other.run_id, right.claim_id)
                    if key in existing:
                        continue
                    tokens_b = self._tokens(right.statement)
                    union = tokens_a | tokens_b
                    score = len(tokens_a & tokens_b) / len(union) if union else 0.0
                    if score >= 0.20:
                        matches.append({
                            "run_a_id": target.run_id, "claim_a_id": left.claim_id,
                            "claim_a": left.statement, "run_b_id": other.run_id,
                            "claim_b_id": right.claim_id, "claim_b": right.statement,
                            "lexical_similarity": round(score, 3),
                            "evidence_a_ids": evidence_a, "evidence_b_ids": evidence_b,
                            "classification": "unreviewed_candidate",
                        })
        matches.sort(key=lambda item: item["lexical_similarity"], reverse=True)
        return matches[:max(1, min(limit, 200))]

    def related_runs(self, question: str, limit: int = 10) -> list[dict]:
        query_tokens = self._tokens(question)
        if not query_tokens:
            return []
        matches = []
        for item in self.store.list_runs(500):
            run = self.store.load_run(item["run_id"])
            if run is None:
                continue
            run_tokens = self._tokens(run.question)
            union = query_tokens | run_tokens
            similarity = len(query_tokens & run_tokens) / len(union) if union else 0.0
            if similarity > 0:
                matches.append({
                    "run_id": run.run_id,
                    "question": run.question,
                    "status": run.status.value,
                    "lexical_similarity": round(similarity, 3),
                    "updated_at": run.updated_at,
                })
        matches.sort(key=lambda item: (item["lexical_similarity"], item["updated_at"]), reverse=True)
        return matches[:max(1, min(limit, 50))]
