"""Explicit experiment lifecycle operations; simulations never become real experiments."""
from __future__ import annotations

from .models import Experiment, ExperimentStatus, ResearchRun, utc_now


class ExperimentManager:
    """Record proposals, simulations, real executions, and evaluation separately."""

    @staticmethod
    def _find(run: ResearchRun, experiment_id: str) -> Experiment:
        experiment = next(
            (item for item in run.experiments if item.experiment_id == experiment_id), None
        )
        if experiment is None:
            raise ValueError(f"Experiment not found: {experiment_id}")
        return experiment

    def record_simulation(
        self, run: ResearchRun, experiment_id: str, simulation_engine: str,
        results: str, limitations: str,
    ) -> Experiment:
        experiment = self._find(run, experiment_id)
        if experiment.status != ExperimentStatus.PROPOSED:
            raise ValueError("Only a proposed experiment can be simulated.")
        if not simulation_engine.strip() or not results.strip() or not limitations.strip():
            raise ValueError("Simulation engine, results, and limitations are required.")
        experiment.status = ExperimentStatus.SIMULATED
        experiment.execution_kind = "simulated"
        experiment.simulation_engine = simulation_engine.strip()
        experiment.results = results.strip()
        experiment.executed_at = utc_now()
        experiment.limitations = (
            experiment.limitations.rstrip()
            + f" Simulation only, using {experiment.simulation_engine}; not a real-world experiment. "
            + "Simulation limitations: " + limitations.strip()
        ).strip()
        run.findings.append(
            f"Experiment {experiment.experiment_id} has simulated output only; no physical experiment was performed."
        )
        return experiment

    def record_performed(
        self, run: ResearchRun, experiment_id: str, execution_method: str,
        operator: str, results: str,
    ) -> Experiment:
        experiment = self._find(run, experiment_id)
        if experiment.status != ExperimentStatus.PROPOSED:
            raise ValueError("Only a proposed experiment can be recorded as performed.")
        if not execution_method.strip() or not operator.strip() or not results.strip():
            raise ValueError("Execution method, operator, and results are required.")
        experiment.status = ExperimentStatus.PERFORMED
        experiment.execution_kind = "performed"
        experiment.execution_review_status = "pending_review"
        experiment.execution_method = execution_method.strip()
        experiment.operator = operator.strip()
        experiment.results = results.strip()
        experiment.executed_at = utc_now()
        run.findings.append(
            f"Experiment {experiment.experiment_id} was recorded as performed by {experiment.operator}; verify its attached method and results."
        )
        return experiment


    def review_performed_execution(
        self, run: ResearchRun, experiment_id: str, status: str,
        reviewer: str, reviewer_note: str,
    ) -> Experiment:
        """Record an independent human check of the claimed real-world execution."""
        experiment = self._find(run, experiment_id)
        if experiment.execution_kind != "performed" or experiment.status != ExperimentStatus.PERFORMED:
            raise ValueError("Only a recorded performed experiment can receive execution review.")
        if experiment.execution_review_status != "pending_review":
            raise ValueError("Performed execution has already been reviewed.")
        if status not in {"accepted", "rejected", "needs_context"}:
            raise ValueError("Execution review status must be accepted, rejected, or needs_context.")
        if not reviewer.strip() or not reviewer_note.strip():
            raise ValueError("A reviewer identity and rationale are required.")
        if reviewer.strip().casefold() == experiment.operator.strip().casefold():
            raise ValueError("Execution reviewer must be different from the recorded operator.")
        experiment.execution_review_status = status
        experiment.execution_review_note = reviewer_note.strip()
        experiment.execution_reviewed_by = reviewer.strip()
        experiment.execution_reviewed_at = utc_now()
        return experiment

    def mark_evaluated(
        self, run: ResearchRun, experiment_id: str, evaluation_note: str,
    ) -> Experiment:
        experiment = self._find(run, experiment_id)
        if experiment.status not in {ExperimentStatus.SIMULATED, ExperimentStatus.PERFORMED}:
            raise ValueError("Only a simulated or performed experiment can be evaluated.")
        if (experiment.execution_kind == "performed"
                and experiment.execution_review_status != "accepted"):
            raise ValueError("A performed experiment requires accepted human execution review before evaluation.")
        if not evaluation_note.strip():
            raise ValueError("An evaluation note is required.")
        if not experiment.results.strip():
            raise ValueError("Experiment results are required before evaluation.")
        # execution_kind preserves whether the evaluated record came from simulation or reality.
        experiment.status = ExperimentStatus.EVALUATED
        experiment.evaluation_note = evaluation_note.strip()
        run.findings.append(
            f"Experiment {experiment.experiment_id} evaluation recorded; execution kind remains {experiment.execution_kind}."
        )
        return experiment
