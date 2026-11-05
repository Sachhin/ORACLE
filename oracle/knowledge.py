"""Evidence-to-claim links, explicit contradictions, alternatives and uncertainty."""
from __future__ import annotations

import re

from .models import (
    Claim, EvidenceClaimLink, EvidenceStance, Hypothesis, HypothesisGroup,
    ResearchRun, UncertaintyAssessment,
)


class KnowledgeBase:
    """A transparent, deterministic knowledge layer; it does not infer truth from text."""

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

    def link_evidence(self, run: ResearchRun, claim_id: str, evidence_id: str,
                      stance: EvidenceStance, strength: float = 1.0,
                      rationale: str = "") -> EvidenceClaimLink:
        if not 0.0 <= strength <= 1.0:
            raise ValueError("Evidence strength must be between 0 and 1.")
        if not any(c.claim_id == claim_id for c in run.claims):
            raise ValueError(f"Unknown claim: {claim_id}")
        if not any(e.evidence_id == evidence_id for e in run.evidence):
            raise ValueError(f"Unknown evidence: {evidence_id}")
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
        """Detect only explicit links and simple direct-negation pairs; no semantic guessing."""
        found = []
        claims = run.claims
        for i, left in enumerate(claims):
            for right in claims[i + 1:]:
                explicit = (right.claim_id in left.contradicts_claim_ids or
                            left.claim_id in right.contradicts_claim_ids)
                a, b = self._normalize(left.statement), self._normalize(right.statement)
                direct_negation = (
                    a == b.replace(" not ", " ") or
                    b == a.replace(" not ", " ") or
                    a == b.replace(" no ", " ") or
                    b == a.replace(" no ", " ")
                )
                if explicit or direct_negation:
                    pair = (left.claim_id, right.claim_id)
                    if pair not in found:
                        found.append(pair)
        return found

    def assess_claim(self, run: ResearchRun, claim_id: str) -> UncertaintyAssessment:
        claim = next((c for c in run.claims if c.claim_id == claim_id), None)
        if claim is None:
            raise ValueError(f"Unknown claim: {claim_id}")
        links = [x for x in run.evidence_claim_links if x.claim_id == claim_id]
        support = sum(x.strength for x in links if x.stance == EvidenceStance.SUPPORTS)
        oppose = sum(x.strength for x in links if x.stance == EvidenceStance.REFUTES)
        relevant = [x for x in links if x.stance != EvidenceStance.CONTEXTUAL]
        contradictions = sum(1 for pair in self.detect_contradictions(run) if claim_id in pair)
        # This is a transparent evidence-balance indicator, not a calibrated probability.
        estimate = None if not relevant else support / (support + oppose) if support + oppose else None
        rationale = ("No supporting/refuting evidence is linked." if not relevant else
                     "Evidence-balance indicator only; not a calibrated probability.")
        if contradictions:
            rationale += f" {contradictions} unresolved claim contradiction(s) remain."
        assessment = UncertaintyAssessment(
            subject_id=claim_id, subject_type="claim",
            evidence_count=len(relevant), supporting_weight=support,
            opposing_weight=oppose, unresolved_contradictions=contradictions,
            confidence_estimate=estimate, rationale=rationale,
        )
        run.uncertainty_assessments.append(assessment)
        return assessment

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9 ]", "", value.lower()).strip()
