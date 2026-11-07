"""Tests for structured language reasoning and safe degradation."""
import unittest

from oracle.agents import AgentContext
from oracle.language_agents import LanguageReasoningAgent
from oracle.models import Evidence, EvidenceKind


class FakeModel:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def generate(self, messages, temperature=0.2):
        self.calls += 1
        return self.response


class LanguageReasoningAgentTests(unittest.TestCase):
    def test_skips_without_source_backed_evidence(self):
        model = FakeModel('{"directions":[],"hypotheses":[]}')
        result = LanguageReasoningAgent(model).run(AgentContext("Q", 1, "both"))
        self.assertEqual(model.calls, 0)
        self.assertTrue(result.warnings)

    def test_parses_provisional_hypothesis(self):
        model = FakeModel(
            '{"directions":["test pathway X"],"hypotheses":['
            '{"statement":"X modifies Y under condition Z",'
            '"rationale":"Two source records motivate testing this relationship",'
            '"predictions":["X and Y covary in an independent cohort"]}]}'
        )
        evidence = [
            Evidence("Study reports pathway X", "paper A", EvidenceKind.SOURCE, source_id="s1"),
            Evidence("Study reports outcome Y", "paper B", EvidenceKind.SOURCE, source_id="s2"),
        ]
        result = LanguageReasoningAgent(model).run(
            AgentContext("Q", 1, "both", evidence=evidence)
        )
        self.assertEqual(model.calls, 1)
        hypothesis = result.items[-1]
        self.assertEqual(hypothesis.confidence, "very low")
        self.assertIn("not evidence", hypothesis.rationale)

    def test_accepts_json_wrapped_in_markdown_fence(self):
        model = FakeModel(
            '```json\n{"directions": [], "hypotheses": []}\n```'
        )
        evidence = [Evidence("Claim", "paper", EvidenceKind.SOURCE, source_id="s1")]
        result = LanguageReasoningAgent(model).run(
            AgentContext("Q", 1, "both", evidence=evidence)
        )
        self.assertIn("Generated provisional", result.summary)
        self.assertFalse(any("schema validation" in warning for warning in result.warnings))

    def test_rejects_invalid_json_and_degrades_gracefully(self):
        model = FakeModel("not json")
        evidence = [Evidence("Claim", "paper", EvidenceKind.SOURCE, source_id="s1")]
        result = LanguageReasoningAgent(model).run(
            AgentContext("Q", 1, "both", evidence=evidence)
        )
        self.assertIn("Rejected malformed", result.summary)
        self.assertTrue(result.warnings)

    def test_model_failure_does_not_raise(self):
        class BrokenModel:
            def generate(self, *_args, **_kwargs):
                raise OSError("offline")
        evidence = [Evidence("Claim", "paper", EvidenceKind.SOURCE, source_id="s1")]
        result = LanguageReasoningAgent(BrokenModel()).run(
            AgentContext("Q", 1, "both", evidence=evidence)
        )
        self.assertIn("unavailable", result.summary)


if __name__ == "__main__":
    unittest.main()
