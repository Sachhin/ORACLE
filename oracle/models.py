"""Typed domain models for research, evidence, hypotheses, and experiments."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class ResearchMode(str, Enum):
    DEEP_RESEARCH = "deep_research"
    AUTONOMOUS_DISCOVERY = "autonomous_discovery"
    BOTH = "both"


class EvidenceKind(str, Enum):
    SOURCE = "source"
    OBSERVATION = "observation"
    DATASET = "dataset"
    INFERENCE = "inference"


class HypothesisStatus(str, Enum):
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    SUPPORTED = "supported"
    WEAKENED = "weakened"
    REJECTED = "rejected"
    OPEN = "open"


class ExperimentStatus(str, Enum):
    PROPOSED = "proposed"
    SIMULATED = "simulated"
    PERFORMED = "performed"
    EVALUATED = "evaluated"


class RunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class Evidence:
    claim: str
    source: str
    kind: EvidenceKind = EvidenceKind.SOURCE
    method: str = "not specified"
    limitations: str = "not assessed"
    confidence: str = "unknown"
    evidence_id: str = field(default_factory=lambda: new_id("ev"))
    created_at: str = field(default_factory=utc_now)


@dataclass
class Hypothesis:
    statement: str
    rationale: str
    predictions: list[str] = field(default_factory=list)
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    confidence: str = "unknown"
    supporting_evidence_ids: list[str] = field(default_factory=list)
    opposing_evidence_ids: list[str] = field(default_factory=list)
    hypothesis_id: str = field(default_factory=lambda: new_id("hyp"))
    created_at: str = field(default_factory=utc_now)


@dataclass
class Experiment:
    question: str
    protocol: list[str]
    predictions: list[str]
    status: ExperimentStatus = ExperimentStatus.PROPOSED
    results: str = ""
    limitations: str = ""
    experiment_id: str = field(default_factory=lambda: new_id("exp"))
    created_at: str = field(default_factory=utc_now)


@dataclass
class ResearchTask:
    name: str
    description: str
    priority: int = 3
    task_id: str = field(default_factory=lambda: new_id("task"))
    status: str = "pending"


@dataclass
class ResearchRun:
    question: str
    mode: ResearchMode = ResearchMode.BOTH
    max_cycles: int = 3
    run_id: str = field(default_factory=lambda: new_id("run"))
    status: RunStatus = RunStatus.CREATED
    current_cycle: int = 0
    tasks: list[ResearchTask] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    experiments: list[Experiment] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
