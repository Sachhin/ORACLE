"""Human-auditable task lifecycle with evidence-backed completion and bounded attempts."""
from __future__ import annotations

from .models import EvidenceKind, ResearchRun, ResearchTask, utc_now


class TaskManager:
    def __init__(self, max_attempts: int = 3, max_tasks: int = 50):
        if not 1 <= max_attempts <= 10:
            raise ValueError("max_attempts must be between 1 and 10.")
        if not 1 <= max_tasks <= 100:
            raise ValueError("max_tasks must be between 1 and 100.")
        self.max_attempts = max_attempts
        self.max_tasks = max_tasks

    @staticmethod
    def _find(run: ResearchRun, task_id: str) -> ResearchTask:
        task = next((item for item in run.tasks if item.task_id == task_id), None)
        if task is None:
            raise ValueError(f"Research task not found: {task_id}")
        return task

    def validate_plan(self, tasks: list[ResearchTask]) -> None:
        if len(tasks) > self.max_tasks:
            raise ValueError(f"Planner exceeded the {self.max_tasks}-task budget.")
        if any(not task.name.strip() or not task.description.strip() for task in tasks):
            raise ValueError("Every task requires a name and description.")
        if any(not 1 <= task.priority <= 5 for task in tasks):
            raise ValueError("Task priority must be between 1 and 5.")

    def start(self, run: ResearchRun, task_id: str) -> ResearchTask:
        task = self._find(run, task_id)
        if task.status not in {"pending", "in_progress"}:
            raise ValueError(f"Cannot start a task with status {task.status}. Retry it first if blocked.")
        if task.attempts >= self.max_attempts:
            raise ValueError(f"Task exceeded the {self.max_attempts}-attempt limit.")
        task.status = "in_progress"
        task.attempts += 1
        task.started_at = utc_now()
        return task

    def complete(
        self, run: ResearchRun, task_id: str, evidence_ids: list[str], note: str,
    ) -> ResearchTask:
        task = self._find(run, task_id)
        if task.status not in {"pending", "in_progress"}:
            raise ValueError(f"Cannot complete a task with status {task.status}.")
        if not note.strip() or not evidence_ids:
            raise ValueError("Task completion requires a note and at least one source-backed evidence ID.")
        evidence_by_id = {item.evidence_id: item for item in run.evidence}
        source_ids = {item.source_id for item in run.sources}
        for evidence_id in evidence_ids:
            evidence = evidence_by_id.get(evidence_id)
            if (evidence is None or evidence.kind == EvidenceKind.INFERENCE
                    or not evidence.source_id or evidence.source_id not in source_ids):
                raise ValueError(
                    f"Task completion evidence must be source-backed; invalid evidence ID: {evidence_id}"
                )
        task.evidence_ids = list(dict.fromkeys(evidence_ids))
        task.completion_note = note.strip()
        task.completed_at = utc_now()
        task.blocked_reason = ""
        task.status = "completed"
        return task

    def block(self, run: ResearchRun, task_id: str, reason: str) -> ResearchTask:
        task = self._find(run, task_id)
        if task.status == "completed":
            raise ValueError("A completed task cannot be blocked.")
        if not reason.strip():
            raise ValueError("A blocked task requires a reason.")
        task.status = "blocked"
        task.blocked_reason = reason.strip()
        return task

    def retry(self, run: ResearchRun, task_id: str) -> ResearchTask:
        task = self._find(run, task_id)
        if task.status != "blocked":
            raise ValueError("Only a blocked task can be retried.")
        if task.attempts >= self.max_attempts:
            raise ValueError(f"Task exceeded the {self.max_attempts}-attempt limit.")
        task.status = "pending"
        task.blocked_reason = ""
        return task
