"""Deterministic baseline agents. These are test scaffolds, not an LLM."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import Evidence, EvidenceKind, Experiment, Hypothesis, ResearchTask


@dataclass
class AgentContext:
    question: str
    cycle: int
    mode: str
    evidence: list[Evidence] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)


@dataclass
class AgentResult:
    agent: str
    summary: str
    items: list[Any] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class PlannerAgent:
    name = "planner"

    def run(self, context: AgentContext) -> AgentResult:
        tasks = [
            ResearchTask("Define scope", f"Clarify the boundaries and key terms in: {context.question}", 1),
            ResearchTask("Map mechanisms", "Identify the major mechanisms and competing explanations.", 2),
            ResearchTask("Identify gaps", "List unknowns, missing evidence, and testable questions.", 2),
            ResearchTask("Challenge assumptions", "Look for alternative explanations and possible falsifiers.", 1),
        ]
        return AgentResult(self.name, "Created a balanced starter research plan.", tasks)


class ResearcherAgent:
    name = "researcher"

    def run(self, context: AgentContext) -> AgentResult:
        evidence = Evidence(
            claim=f"The research question requires a structured account of mechanisms, evidence, and unresolved uncertainties: {context.question}",
            source="ORACLE planning scaffold; not an external scientific source",
            kind=EvidenceKind.INFERENCE,
            method="Question decomposition",
            limitations="This is a planning inference, not empirical or literature evidence.",
            confidence="low",
        )
        return AgentResult(self.name, "Created a clearly labelled planning inference.", [evidence],
                           ["No external literature or datasets were queried in offline mode."])


class ExplorerAgent:
    name = "explorer"

    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(self.name,
            "Generated exploration directions from the question structure.",
            ["Look for overlooked mechanisms", "Compare competing models",
             "Search for boundary conditions and counterexamples"])


class HypothesisAgent:
    name = "hypothesis_generator"

    def run(self, context: AgentContext) -> AgentResult:
        hypothesis = Hypothesis(
            statement=f"A useful explanation of '{context.question}' may require multiple interacting mechanisms rather than a single controlling factor.",
            rationale="A broad systems-level framing is a testable starting point, not an established conclusion.",
            predictions=["A multi-factor model should explain observations that a single-factor model cannot."],
            confidence="very low",
        )
        alternative = Hypothesis(
            statement=f"A dominant single mechanism may explain most of: '{context.question}'.",
            rationale="A simpler competing model is retained so the first hypothesis is not treated as the default truth.",
            predictions=["A single-mechanism model should explain the key observations without requiring additional interacting factors."],
            confidence="very low",
        )
        return AgentResult(self.name, "Created competing provisional hypotheses for later testing.",
                           [hypothesis, alternative])


class SkepticAgent:
    name = "skeptic"

    def run(self, context: AgentContext) -> AgentResult:
        warnings = [
            "The hypothesis may be too broad to falsify without operational definitions.",
            "No independent evidence currently supports or refutes this hypothesis.",
            "A simpler single-mechanism explanation must be compared before preferring a complex model.",
        ]
        return AgentResult(self.name, "Applied a conservative adversarial review.", warnings=warnings)


class AuditorAgent:
    name = "auditor"

    def run(self, context: AgentContext) -> AgentResult:
        warnings = []
        for item in context.evidence:
            if item.kind == EvidenceKind.INFERENCE and "not an external" in item.source:
                warnings.append("Planning inference correctly remains distinct from sourced evidence.")
        if not context.evidence:
            warnings.append("No evidence records exist; do not make factual conclusions.")
        return AgentResult(self.name, "Completed provenance and evidence-type audit.", warnings=warnings)


class ExperimentDesignerAgent:
    name = "experiment_designer"

    def run(self, context: AgentContext) -> AgentResult:
        if not context.hypotheses:
            return AgentResult(self.name, "No hypothesis available; experiment design deferred.")
        experiment = Experiment(
            question=f"What observation would distinguish the hypothesis from a simpler alternative?",
            protocol=[
                "Define measurable variables and operational criteria.",
                "Specify a baseline or competing-model control.",
                "Pre-register predicted outcomes and exclusion criteria.",
                "Collect independent observations using an appropriate validated method.",
            ],
            predictions=context.hypotheses[0].predictions,
            limitations="Design only. No experiment has been performed or simulated.",
        )
        return AgentResult(self.name, "Created a proposed experiment design, not an executed experiment.", [experiment])


class NoveltyAssessorAgent:
    name = "novelty_assessor"

    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(self.name,
            "Novelty cannot be established without a literature search and prior-art comparison.",
            warnings=["Novelty status: unassessed. No priority claim is permitted."])
