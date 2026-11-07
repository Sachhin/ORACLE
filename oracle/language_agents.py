"""Structured, optional language reasoning over source-backed research context."""
from __future__ import annotations

import json
from typing import Protocol

from .agents import AgentContext, AgentResult
from .models import EvidenceKind, Hypothesis


class TextGenerator(Protocol):
    def generate(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str: ...


class LanguageReasoningAgent:
    """Ask an optional model for bounded proposals; never accept its output as evidence."""

    name = "language_reasoner"

    def __init__(self, model: TextGenerator, max_hypotheses: int = 4,
                 max_directions: int = 6) -> None:
        if not 1 <= max_hypotheses <= 8 or not 1 <= max_directions <= 12:
            raise ValueError("Language reasoning output limits are outside safe bounds.")
        self.model = model
        self.max_hypotheses = max_hypotheses
        self.max_directions = max_directions

    def run(self, context: AgentContext) -> AgentResult:
        evidence = [
            item for item in context.evidence
            if item.kind != EvidenceKind.INFERENCE and item.source_id
        ][:30]
        if not evidence:
            return AgentResult(
                self.name,
                "Skipped language reasoning because no source-backed evidence is available.",
                warnings=["Language model cannot substitute for missing scientific evidence."],
            )

        evidence_text = "\n".join(
            f"- evidence_id={item.evidence_id}; source_id={item.source_id}; "
            f"claim={item.claim[:1200]}"
            for item in evidence
        )
        schema = {
            "directions": ["short, testable research direction"],
            "hypotheses": [
                {
                    "statement": "falsifiable candidate hypothesis",
                    "rationale": "why the supplied evidence motivates it",
                    "predictions": ["observable prediction", "potential falsifier"],
                }
            ],
        }
        messages = [
            {
                "role": "system",
                "content": (
                    "You are ORACLE's language-reasoning assistant. /no_think Use only the supplied "
                    "question and evidence records. Do not invent citations, source IDs, "
                    "measurements, results, or claims of novelty. Distinguish correlation "
                    "from causation. Produce competing, falsifiable candidate ideas, not "
                    "scientific conclusions. If evidence is insufficient, return empty "
                    "arrays. Return only valid JSON matching this schema: "
                    + json.dumps(schema)
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Research question: {context.question}\n"
                    f"Research mode: {context.mode}\n"
                    f"Source-backed evidence records:\n{evidence_text}"
                ),
            },
        ]
        try:
            raw = self.model.generate(messages, temperature=0.2)
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("response must be a JSON object")
            directions = payload.get("directions", [])
            candidates = payload.get("hypotheses", [])
            if not isinstance(directions, list) or not isinstance(candidates, list):
                raise ValueError("directions and hypotheses must be arrays")
            if any(not isinstance(item, str) for item in directions):
                raise ValueError("directions must contain strings")
            hypotheses = []
            for item in candidates[:self.max_hypotheses]:
                if not isinstance(item, dict):
                    raise ValueError("each hypothesis must be an object")
                statement = item.get("statement")
                rationale = item.get("rationale")
                predictions = item.get("predictions")
                if (not isinstance(statement, str) or not statement.strip()
                        or not isinstance(rationale, str) or not rationale.strip()
                        or not isinstance(predictions, list)
                        or not predictions or any(not isinstance(p, str) or not p.strip()
                                                   for p in predictions)):
                    raise ValueError("hypothesis is missing a statement, rationale, or predictions")
                hypotheses.append(Hypothesis(
                    statement=statement.strip(),
                    rationale=(
                        "LLM-generated provisional proposal. " + rationale.strip()
                        + " It is not evidence and requires independent source verification."
                    ),
                    predictions=[p.strip() for p in predictions[:6]],
                    confidence="very low",
                ))
            clean_directions = [item.strip() for item in directions[:self.max_directions]
                                if item.strip()]
            return AgentResult(
                self.name,
                "Generated provisional language-assisted research proposals; none are established findings.",
                items=clean_directions + hypotheses,
                warnings=[
                    "All language-model outputs are untrusted proposals, not evidence.",
                    "Hypotheses require source linkage, skeptic review, and independent validation.",
                ],
            )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return AgentResult(
                self.name,
                "Rejected malformed language-model output; deterministic research continues.",
                warnings=[f"Language-model response failed schema validation: {exc}"],
            )
        except Exception as exc:
            return AgentResult(
                self.name,
                "Language model unavailable; deterministic research continues.",
                warnings=[f"Optional language reasoning failed: {str(exc)[:300]}"],
            )
