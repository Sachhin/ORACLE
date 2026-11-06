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
                "knowledge_gap_score": assessment.score,
            })
        return entries

    def assess(self, run_id: str) -> KnowledgeGapAssessment:
        run = self.store.load_run(run_id)
        if run is None:
            raise ValueError(f"Research run not found: {run_id}")
        return self.assessor.assess(run)

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
