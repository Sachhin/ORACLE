"""Tests for provider-backed auditor and literature novelty triage."""
import unittest

from oracle.agents import AgentContext
from oracle.model_agents import (
    GeminiAgentError,
    GeminiAuditorAgent,
    GeminiNoveltyAssessorAgent,
    GeminiCrossDomainConnectionAgent,
)
from oracle.models import Evidence, EvidenceKind, ResearchRun, SourceRecord
from oracle.knowledge import KnowledgeBase
from oracle.storage import ResearchStore
import tempfile
from pathlib import Path


class FakeProvider:
    model = "fake-model"

    def __init__(self, response):
        self.response = response
        self.calls = 0

    def generate_json(self, prompt):
        self.calls += 1
        return self.response


class GeminiReviewAgentTests(unittest.TestCase):
    def test_auditor_returns_provisional_findings_with_valid_evidence_ids(self):
        evidence = Evidence("A measured observation", "Paper A", source_id="src-1")
        provider = FakeProvider({"findings": [{
            "severity": "high",
            "finding": "The interpretation exceeds the measured result.",
            "evidence_ids": [evidence.evidence_id],
        }]})
        result = GeminiAuditorAgent(provider).run(
            AgentContext("Research question", 1, "both", evidence=[evidence])
        )
        self.assertIn("provisional integrity review", result.summary)
        self.assertEqual(len(result.warnings), 1)
        self.assertIn(evidence.evidence_id, result.warnings[0])

    def test_auditor_rejects_unknown_evidence_ids(self):
        provider = FakeProvider({"findings": [{
            "severity": "medium", "finding": "Unsupported.", "evidence_ids": ["ev-forged"]
        }]})
        with self.assertRaises(GeminiAgentError):
            GeminiAuditorAgent(provider).run(AgentContext("Question", 1, "both"))

    def test_novelty_does_not_call_model_without_literature_evidence(self):
        provider = FakeProvider({})
        result = GeminiNoveltyAssessorAgent(provider).run(
            AgentContext("Question", 1, "both",
                         evidence=[Evidence("Model inference", "ORACLE", EvidenceKind.INFERENCE)])
        )
        self.assertEqual(provider.calls, 0)
        self.assertIn("unassessed", result.summary)

    def test_novelty_requires_and_preserves_known_source_ids(self):
        evidence = Evidence("A paper reports a developmental pathway.",
                            "Example paper", EvidenceKind.SOURCE, source_id="src-paper-1")
        provider = FakeProvider({
            "status": "potentially_novel_gap",
            "rationale": "The supplied abstracts leave this mechanism unresolved.",
            "source_ids": ["src-paper-1"],
            "search_gaps": ["Search additional databases and full text."],
        })
        result = GeminiNoveltyAssessorAgent(provider).run(
            AgentContext("Question", 1, "both", evidence=[evidence])
        )
        self.assertIn("potentially_novel_gap", result.summary)
        self.assertIn("src-paper-1", result.summary)
        self.assertTrue(any("not an exhaustive" in item for item in result.warnings))

    def test_cross_domain_proposal_requires_two_source_ids_and_distinct_domains(self):
        first = Evidence("Cell signaling regulates development.", "Paper A",
                         EvidenceKind.SOURCE, source_id="src-a")
        second = Evidence("Control systems adapt to environmental signals.", "Paper B",
                          EvidenceKind.SOURCE, source_id="src-b")
        provider = FakeProvider({"connections": [{
            "statement": "A feedback-control framework may help test developmental signaling robustness.",
            "domain_a": "Developmental biology",
            "domain_b": "Control theory",
            "rationale": "Both fields study feedback and system stability.",
            "source_ids": ["src-a", "src-b"],
            "testable_prediction": "Perturbation response curves should reveal a feedback-dependent stability boundary.",
            "limitations": "Conceptual analogy only.",
        }]})
        result = GeminiCrossDomainConnectionAgent(provider).run(
            AgentContext("Question", 1, "both", evidence=[first, second])
        )
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].status, "pending_review")
        self.assertEqual(set(result.items[0].source_ids), {"src-a", "src-b"})

    def test_cross_domain_connection_requires_human_review_and_persists(self):
        run = ResearchRun("Cross-domain persistence")
        run.sources.extend([
            SourceRecord("Paper A", source_id="src-a"),
            SourceRecord("Paper B", source_id="src-b"),
        ])
        evidence = Evidence("Cross-domain idea", "ORACLE proposal", EvidenceKind.INFERENCE)
        connection = GeminiCrossDomainConnectionAgent(FakeProvider({"connections": [{
            "statement": "A shared feedback mechanism may be testable.",
            "domain_a": "Biology", "domain_b": "Control theory",
            "rationale": "Both describe feedback.",
            "source_ids": ["src-a", "src-b"],
            "testable_prediction": "Measure response to perturbation.",
            "limitations": "Hypothesis only.",
        }]})).run(
            AgentContext("Question", 1, "both", evidence=[
                Evidence("Source A", "Paper A", EvidenceKind.SOURCE, source_id="src-a"),
                Evidence("Source B", "Paper B", EvidenceKind.SOURCE, source_id="src-b"),
            ])
        ).items[0]
        run.cross_domain_connections.append(connection)
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(Path(tmp) / "oracle.sqlite3")
            store.save_run(run)
            loaded = store.load_run(run.run_id)
            self.assertEqual(len(loaded.cross_domain_connections), 1)
            with self.assertRaises(ValueError):
                KnowledgeBase().review_cross_domain_connection(
                    loaded, connection.connection_id, "accepted", ""
                )
            reviewed = KnowledgeBase().review_cross_domain_connection(
                loaded, connection.connection_id, "accepted", "Reviewed both source contexts."
            )
            store.save_run(loaded)
            reloaded = store.load_run(run.run_id)
            self.assertEqual(reloaded.cross_domain_connections[0].status, "accepted")
            self.assertEqual(reviewed.reviewer_note, "Reviewed both source contexts.")

    def test_novelty_rejects_fabricated_source_ids(self):
        evidence = Evidence("Paper finding", "Paper", EvidenceKind.SOURCE, source_id="src-real")
        provider = FakeProvider({
            "status": "possibly_previously_reported",
            "rationale": "Similar work exists.",
            "source_ids": ["src-invented"],
            "search_gaps": [],
        })
        with self.assertRaises(GeminiAgentError):
            GeminiNoveltyAssessorAgent(provider).run(
                AgentContext("Question", 1, "both", evidence=[evidence])
            )


if __name__ == "__main__":
    unittest.main()
