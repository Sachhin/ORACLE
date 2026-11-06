"""Tests for provider-backed auditor and literature novelty triage."""
import unittest

from oracle.agents import AgentContext
from oracle.model_agents import (
    GeminiAgentError,
    GeminiAuditorAgent,
    GeminiNoveltyAssessorAgent,
)
from oracle.models import Evidence, EvidenceKind


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
