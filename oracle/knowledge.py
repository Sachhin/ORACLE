"""Provenance-aware claim/evidence graph and conservative uncertainty accounting."""
from __future__ import annotations

import re

from .models import (
    Claim, ClaimRevision, ContradictionCandidate, EvidenceClaimLink, EvidenceStance,
    Hypothesis, HypothesisGroup, ResearchRun, SourceRecord, UncertaintyAssessment,
)


class KnowledgeBase:
    """Transparent bookkeeping; it does not infer scientific truth from prose."""

    def add_source(self, run: ResearchRun, source: SourceRecord) -> SourceRecord:
        if not 0.0 <= source.reliability_score <= 1.0:
            raise ValueError("Source reliability must be between 0 and 1.")
        if not source.title.strip():
            raise ValueError("Source title cannot be empty.")
        existing = next((s for s in run.sources if s.source_id == source.source_id), None)
        if existing:
            return existing
        if source.url:
            duplicate = next((s for s in run.sources if s.url and s.url == source.url), None)
            if duplicate:
                return duplicate
        run.sources.append(source)
        return source

    def add_claim(self, run: ResearchRun, statement: str,
                  claim_type: str = "scientific") -> Claim:
        statement = statement.strip()
        if not statement:
            raise ValueError("Claim statement cannot be empty.")
        existing = next((c for c in run.claims
                         if self._normalize(c.statement) == self._normalize(statement)), None)
        if existing:
            return existing
        claim = Claim(statement=statement, claim_type=claim_type)
        run.claims.append(claim)
        self.detect_contradictions(run)
        return claim

    def revise_claim(self, run: ResearchRun, claim_id: str, new_statement: str,
                     reason: str) -> Claim:
        claim = next((c for c in run.claims if c.claim_id == claim_id), None)
        if claim is None:
            raise ValueError(f"Unknown claim: {claim_id}")
        new_statement = new_statement.strip()
        if not new_statement or not reason.strip():
            raise ValueError("A revised statement and change reason are required.")
        if self._normalize(new_statement) == self._normalize(claim.statement):
            return claim
        run.claim_revisions.append(ClaimRevision(
            claim_id=claim.claim_id, revision=claim.revision,
            statement=claim.statement, change_reason=reason.strip(),
        ))
        claim.statement = new_statement
        claim.revision += 1
        self.detect_contradictions(run)
        return claim

    def link_evidence(self, run: ResearchRun, claim_id: str, evidence_id: str,
                      stance: EvidenceStance, strength: float = 1.0,
                      rationale: str = "") -> EvidenceClaimLink:
        if not 0.0 <= strength <= 1.0:
            raise ValueError("Evidence strength must be between 0 and 1.")
        if not any(c.claim_id == claim_id for c in run.claims):
            raise ValueError(f"Unknown claim: {claim_id}")
        evidence = next((e for e in run.evidence if e.evidence_id == evidence_id), None)
        if evidence is None:
            raise ValueError(f"Unknown evidence: {evidence_id}")
        if not 0.0 <= evidence.reliability <= 1.0:
            raise ValueError("Evidence reliability must be between 0 and 1.")
        if evidence.source_id and not any(s.source_id == evidence.source_id for s in run.sources):
            raise ValueError(f"Unknown source: {evidence.source_id}")
        prior = next((x for x in run.evidence_claim_links
                      if x.claim_id == claim_id and x.evidence_id == evidence_id), None)
        if prior:
            prior.stance, prior.strength, prior.rationale = stance, strength, rationale
            return prior
        link = EvidenceClaimLink(claim_id, evidence_id, stance, strength, rationale)
        run.evidence_claim_links.append(link)
        return link

    def add_hypothesis(self, run: ResearchRun, hypothesis: Hypothesis,
                       group_id: str | None = None) -> HypothesisGroup:
        group = next((g for g in run.hypothesis_groups if g.group_id == group_id), None)
        if group is None:
            group = next((g for g in run.hypothesis_groups
                          if g.question == run.question and g.status == "open"), None)
        if group is None:
            group = HypothesisGroup(question=run.question)
            run.hypothesis_groups.append(group)
        hypothesis.group_id = group.group_id
        if not any(h.hypothesis_id == hypothesis.hypothesis_id for h in run.hypotheses):
            run.hypotheses.append(hypothesis)
            group.hypothesis_ids.append(hypothesis.hypothesis_id)
        return group

    def detect_contradictions(self, run: ResearchRun) -> list[tuple[str, str]]:
        """Create review candidates only; direct-negation matching is deliberately narrow."""
        pairs: list[tuple[str, str]] = []
        claims = run.claims
        for i, left in enumerate(claims):
            for right in claims[i + 1:]:
                explicit = (right.claim_id in left.contradicts_claim_ids or
                            left.claim_id in right.contradicts_claim_ids)
                a, b = self._normalize(left.statement), self._normalize(right.statement)
                negations = (b.replace(" not ", " "), a.replace(" not ", " "),
                             b.replace(" no ", " "), a.replace(" no ", " "))
                direct = a in (negations[0], negations[2]) or b in (negations[1], negations[3])
                if explicit or direct:
                    pair = (left.claim_id, right.claim_id)
                    pairs.append(pair)
                    if not any({c.claim_a_id, c.claim_b_id} == set(pair)
                               for c in run.contradiction_candidates):
                        run.contradiction_candidates.append(ContradictionCandidate(
                            pair[0], pair[1],
                            "explicit_link" if explicit else "direct_negation_heuristic",
                            "Candidate only: human or model review is required; no automatic resolution.",
                        ))
        return pairs

    def review_contradiction(self, run: ResearchRun, candidate_id: str,
                             status: str, reviewer_note: str) -> ContradictionCandidate:
        if status not in {"confirmed", "rejected", "needs_context"}:
            raise ValueError("Status must be confirmed, rejected, or needs_context.")
        candidate = next((c for c in run.contradiction_candidates
                          if c.candidate_id == candidate_id), None)
        if candidate is None:
            raise ValueError(f"Unknown contradiction candidate: {candidate_id}")
        candidate.status, candidate.reviewer_note = status, reviewer_note
        return candidate

    def assess_claim(self, run: ResearchRun, claim_id: str) -> UncertaintyAssessment:
        claim = next((c for c in run.claims if c.claim_id == claim_id), None)
        if claim is None:
            raise ValueError(f"Unknown claim: {claim_id}")
        evidence_by_id = {e.evidence_id: e for e in run.evidence}
        links = [x for x in run.evidence_claim_links if x.claim_id == claim_id]
        # Evidence derived from the same dependence group contributes only its strongest item.
        buckets: dict[tuple[str, str], float] = {}
        for link in links:
            if link.stance == EvidenceStance.CONTEXTUAL:
                continue
            evidence = evidence_by_id[link.evidence_id]
            group = evidence.dependence_group.strip() or evidence.evidence_id
            key = (link.stance.value, group)
            weight = link.strength * evidence.reliability
            buckets[key] = max(buckets.get(key, 0.0), weight)
        support = sum(v for (stance, _), v in buckets.items() if stance == EvidenceStance.SUPPORTS.value)
        oppose = sum(v for (stance, _), v in buckets.items() if stance == EvidenceStance.REFUTES.value)
        groups = len({group for _, group in buckets})
        unresolved = sum(1 for c in run.contradiction_candidates
                         if claim_id in (c.claim_a_id, c.claim_b_id)
                         and c.status in {"pending_review", "needs_context"})
        estimate = None if not buckets or support + oppose == 0 else support / (support + oppose)
        rationale = (
            "No usable supporting/refuting evidence is linked." if not buckets else
            "Reliability-weighted evidence-balance indicator; not a probability or calibrated confidence."
        )
        rationale += " Evidence sharing a dependence_group is conservatively counted once per stance."
        if unresolved:
            rationale += f" {unresolved} unresolved contradiction candidate(s) remain."
        assessment = UncertaintyAssessment(
            subject_id=claim_id, subject_type="claim", evidence_count=sum(
                1 for x in links if x.stance != EvidenceStance.CONTEXTUAL),
            supporting_weight=support, opposing_weight=oppose,
            unresolved_contradictions=unresolved, confidence_estimate=estimate,
            rationale=rationale, independent_evidence_groups=groups,
        )
        run.uncertainty_assessments.append(assessment)
        return assessment

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9 ]", "", value.lower()).strip()
