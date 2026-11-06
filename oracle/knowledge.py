"""Provenance-aware claim/evidence graph and conservative uncertainty accounting."""
from __future__ import annotations

import re

from .models import (
    Claim, ClaimRevision, ContradictionCandidate, EvidenceClaimLink, EvidenceReviewCandidate,
    EvidenceKind, EvidenceStance, Hypothesis, HypothesisGroup, HypothesisStatus, ResearchRun,
    SourceRecord, UncertaintyAssessment, utc_now, utc_now,
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

    def review_source_quality(
        self, run: ResearchRun, source_id: str, reliability_score: float,
        rationale: str,
    ) -> SourceRecord:
        """Record a human source-quality assessment and sync linked evidence weights."""
        if not 0.0 <= reliability_score <= 1.0:
            raise ValueError("Source reliability must be between 0 and 1.")
        if not rationale.strip():
            raise ValueError("A human quality-review rationale is required.")
        source = next((item for item in run.sources if item.source_id == source_id), None)
        if source is None:
            raise ValueError(f"Unknown source: {source_id}")
        source.reliability_score = reliability_score
        source.reliability_rationale = rationale.strip()
        source.quality_reviewer_note = rationale.strip()
        source.quality_reviewed_at = utc_now()
        for evidence in run.evidence:
            if evidence.source_id == source_id:
                evidence.reliability = reliability_score
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

    def add_evidence_review_candidate(
        self, run: ResearchRun, claim_id: str, evidence_id: str,
        proposed_stance: EvidenceStance, rationale: str, source_quote: str, model: str,
    ) -> EvidenceReviewCandidate:
        """Store a quote-grounded model suggestion without changing evidence weight."""
        claim = next((item for item in run.claims if item.claim_id == claim_id), None)
        evidence = next((item for item in run.evidence if item.evidence_id == evidence_id), None)
        if claim is None or evidence is None:
            raise ValueError("Evidence review must reference an existing claim and evidence record.")
        if evidence.kind == EvidenceKind.INFERENCE or not evidence.source_id:
            raise ValueError("Only source-backed evidence can receive a scientific evidence review.")
        if not isinstance(proposed_stance, EvidenceStance):
            raise ValueError("Proposed stance must be a valid EvidenceStance.")
        if not source_quote or source_quote not in evidence.claim:
            raise ValueError("Review quote must be an exact substring of the evidence text.")
        if not rationale.strip() or not model.strip():
            raise ValueError("Review rationale and model name are required.")
        existing = next((item for item in run.evidence_review_candidates
                         if item.claim_id == claim_id and item.evidence_id == evidence_id), None)
        if existing:
            return existing
        candidate = EvidenceReviewCandidate(
            claim_id=claim_id, evidence_id=evidence_id,
            proposed_stance=proposed_stance, rationale=rationale.strip(),
            source_quote=source_quote, model=model,
        )
        run.evidence_review_candidates.append(candidate)
        return candidate

    def review_evidence_candidate(
        self, run: ResearchRun, candidate_id: str, status: str,
        reviewer_note: str, strength: float = 1.0,
    ) -> EvidenceReviewCandidate:
        """Apply a model suggestion only after an explicit human acceptance."""
        if status not in {"accepted", "rejected", "needs_context"}:
            raise ValueError("Status must be accepted, rejected, or needs_context.")
        if not reviewer_note.strip():
            raise ValueError("A reviewer note is required for every evidence-review decision.")
        candidate = next((item for item in run.evidence_review_candidates
                          if item.candidate_id == candidate_id), None)
        if candidate is None:
            raise ValueError(f"Unknown evidence review candidate: {candidate_id}")
        if candidate.status != "pending_review":
            raise ValueError("Evidence review candidate has already been reviewed.")
        if status == "accepted":
            self.link_evidence(
                run, candidate.claim_id, candidate.evidence_id,
                candidate.proposed_stance, strength,
                "Human accepted a quote-grounded model review: " + reviewer_note.strip(),
            )
        candidate.status = status
        candidate.reviewer_note = reviewer_note.strip()
        return candidate

    def link_hypothesis_evidence(
        self, run: ResearchRun, hypothesis_id: str, evidence_id: str,
        stance: EvidenceStance, reviewer_note: str,
    ) -> Hypothesis:
        """Attach source-backed evidence to a hypothesis after explicit review."""
        hypothesis = next((item for item in run.hypotheses
                           if item.hypothesis_id == hypothesis_id), None)
        evidence = next((item for item in run.evidence
                         if item.evidence_id == evidence_id), None)
        if hypothesis is None or evidence is None:
            raise ValueError("Hypothesis evidence link must reference existing records.")
        if stance not in {EvidenceStance.SUPPORTS, EvidenceStance.REFUTES}:
            raise ValueError("Hypothesis evidence must be classified as supports or refutes.")
        if (evidence.kind == EvidenceKind.INFERENCE or not evidence.source_id
                or not any(source.source_id == evidence.source_id for source in run.sources)):
            raise ValueError("Only source-backed evidence can be linked to a hypothesis.")
        if not reviewer_note.strip():
            raise ValueError("A human review note is required for hypothesis evidence links.")
        target = (hypothesis.supporting_evidence_ids if stance == EvidenceStance.SUPPORTS
                  else hypothesis.opposing_evidence_ids)
        opposite = (hypothesis.opposing_evidence_ids if stance == EvidenceStance.SUPPORTS
                    else hypothesis.supporting_evidence_ids)
        if evidence_id in opposite:
            raise ValueError("The same evidence record cannot support and refute one hypothesis.")
        if evidence_id not in target:
            target.append(evidence_id)
        hypothesis.status = HypothesisStatus.UNDER_REVIEW
        hypothesis.reviewer_note = reviewer_note.strip()
        hypothesis.reviewed_at = utc_now()
        return hypothesis

    def review_hypothesis(
        self, run: ResearchRun, hypothesis_id: str, status: str, reviewer_note: str,
    ) -> Hypothesis:
        """Record a human hypothesis judgement; never infer status automatically."""
        allowed = {
            "supported", "weakened", "rejected", "open",
        }
        if status not in allowed:
            raise ValueError("Hypothesis status must be supported, weakened, rejected, or open.")
        if not reviewer_note.strip():
            raise ValueError("A human review note is required.")
        hypothesis = next((item for item in run.hypotheses
                           if item.hypothesis_id == hypothesis_id), None)
        if hypothesis is None:
            raise ValueError(f"Unknown hypothesis: {hypothesis_id}")
        if status == "supported" and not hypothesis.supporting_evidence_ids:
            raise ValueError("A supported judgement requires linked supporting evidence.")
        if status in {"weakened", "rejected"} and not hypothesis.opposing_evidence_ids:
            raise ValueError("A weakened/rejected judgement requires linked opposing evidence.")
        hypothesis.status = HypothesisStatus(status)
        hypothesis.reviewer_note = reviewer_note.strip()
        hypothesis.reviewed_at = utc_now()
        return hypothesis

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

    def review_cross_domain_connection(self, run: ResearchRun, connection_id: str,
                                       status: str, reviewer_note: str):
        """Record a human decision on a source-linked cross-domain proposal."""
        if status not in {"accepted", "rejected", "needs_context"}:
            raise ValueError("Connection status must be accepted, rejected, or needs_context.")
        if not reviewer_note.strip():
            raise ValueError("A human review note is required.")
        connection = next((item for item in run.cross_domain_connections
                           if item.connection_id == connection_id), None)
        if connection is None:
            raise ValueError(f"Unknown cross-domain connection: {connection_id}")
        source_ids = {source.source_id for source in run.sources}
        if any(source_id not in source_ids for source_id in connection.source_ids):
            raise ValueError("Connection references a source absent from the run.")
        connection.status = status
        connection.reviewer_note = reviewer_note.strip()
        connection.reviewed_at = utc_now()
        return connection

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
            "Reliability-weighted evidence-balance indicator; not a calibrated probability or confidence."
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
