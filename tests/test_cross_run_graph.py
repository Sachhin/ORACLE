"""Tests for the shared, human-reviewed cross-run claim graph."""
import tempfile
import unittest
from pathlib import Path

from oracle.models import (
    Claim, Evidence, EvidenceClaimLink, EvidenceKind, EvidenceStance,
    ResearchRun, SourceRecord,
)
from oracle.portfolio import ResearchPortfolio
from oracle.storage import ResearchStore


def grounded_run(question, statement, suffix):
    run = ResearchRun(question)
    source = SourceRecord(f"Paper {suffix}", source_id=f"src-{suffix}")
    evidence = Evidence(
        statement, source.title, EvidenceKind.SOURCE,
        source_id=source.source_id, evidence_id=f"ev-{suffix}",
    )
    claim = Claim(statement, claim_id=f"cl-{suffix}")
    run.sources.append(source)
    run.evidence.append(evidence)
    run.claims.append(claim)
    run.evidence_claim_links.append(EvidenceClaimLink(
        claim.claim_id, evidence.evidence_id, EvidenceStance.SUPPORTS,
        rationale="Human-checked source link",
    ))
    return run


class CrossRunKnowledgeGraphTests(unittest.TestCase):
    def test_candidates_require_source_backed_claim_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(Path(tmp) / "oracle.sqlite3")
            first = grounded_run("development", "Cell signaling controls cell fate", "a")
            second = grounded_run("signaling", "Cell signaling regulates cell fate", "b")
            store.save_run(first)
            store.save_run(second)
            candidates = ResearchPortfolio(store).cross_run_claim_candidates(first.run_id)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["classification"], "unreviewed_candidate")
            self.assertEqual(candidates[0]["evidence_a_ids"], ["ev-a"])

    def test_cross_run_link_persists_and_requires_human_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(Path(tmp) / "oracle.sqlite3")
            first = grounded_run("development", "Cell signaling controls cell fate", "a")
            second = grounded_run("signaling", "Cell signaling regulates cell fate", "b")
            store.save_run(first)
            store.save_run(second)
            link = store.create_cross_run_claim_link(
                first.run_id, "cl-a", second.run_id, "cl-b",
                "same_topic", "The claims concern a shared pathway and cite distinct papers.",
            )
            self.assertEqual(link.status, "pending_review")
            self.assertEqual(link.evidence_a_ids, ["ev-a"])
            self.assertEqual(len(store.list_cross_run_claim_links()), 1)
            with self.assertRaises(ValueError):
                store.review_cross_run_claim_link(link.link_id, "accepted", "")
            reviewed = store.review_cross_run_claim_link(
                link.link_id, "accepted", "Compared both source records and claim scope."
            )
            self.assertEqual(reviewed.status, "accepted")
            self.assertEqual(store.list_cross_run_claim_links()[0]["reviewer_note"],
                             "Compared both source records and claim scope.")
            with self.assertRaises(ValueError):
                store.review_cross_run_claim_link(
                    link.link_id, "rejected", "Do not overwrite a completed decision."
                )

    def test_link_rejects_same_run_or_unprovenanced_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(Path(tmp) / "oracle.sqlite3")
            first = grounded_run("development", "Cell signaling controls cell fate", "a")
            second = grounded_run("signaling", "Cell signaling regulates cell fate", "b")
            store.save_run(first)
            store.save_run(second)
            with self.assertRaises(ValueError):
                store.create_cross_run_claim_link(
                    first.run_id, "cl-a", first.run_id, "cl-a",
                    "same_topic", "Same run is not cross-run.",
                )
            second.evidence_claim_links.clear()
            store.save_run(second)
            with self.assertRaises(ValueError):
                store.create_cross_run_claim_link(
                    first.run_id, "cl-a", second.run_id, "cl-b",
                    "supports", "No linked source evidence.",
                )

    def test_review_revalidates_claim_and_evidence_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(Path(tmp) / "oracle.sqlite3")
            first = grounded_run("development", "Cell signaling controls cell fate", "a")
            second = grounded_run("signaling", "Cell signaling regulates cell fate", "b")
            store.save_run(first)
            store.save_run(second)
            link = store.create_cross_run_claim_link(
                first.run_id, "cl-a", second.run_id, "cl-b",
                "contextualizes", "Context relationship candidate.",
            )
            first.evidence.clear()
            store.save_run(first)
            with self.assertRaises(ValueError):
                store.review_cross_run_claim_link(
                    link.link_id, "accepted", "Evidence has since been removed."
                )


if __name__ == "__main__":
    unittest.main()
