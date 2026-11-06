"""Progress-aware, bounded autonomous decision policy."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Decision:
    action: str
    reason: str


def choose_next_action(
    cycle: int,
    max_cycles: int,
    progress: bool,
    critical_warnings: int = 0,
    consecutive_no_progress: int = 0,
    max_no_progress: int = 1,
) -> Decision:
    """Choose a safe next action from measured progress and explicit limits.

    Critical integrity failures stop the run. A cycle-budget boundary concludes
    normally. Repeated no-progress cycles stop safely; a single stagnant cycle
    may be tolerated when the caller configures a larger threshold.
    """
    if cycle < 0 or max_cycles < 1:
        raise ValueError("cycle must be non-negative and max_cycles must be positive.")
    if consecutive_no_progress < 0 or max_no_progress < 1:
        raise ValueError("No-progress counters must be non-negative and threshold positive.")
    if critical_warnings:
        return Decision("stop", "Critical scientific-integrity validation failed; stopping without promoting findings.")
    if cycle >= max_cycles:
        return Decision("conclude", "Configured cycle budget reached; save findings and open questions.")
    if progress:
        return Decision("continue", "New research information was recorded and cycle budget remains.")
    if consecutive_no_progress + 1 >= max_no_progress:
        return Decision("stop", "Repeated cycles produced no new research information; stopping safely.")
    return Decision("replan", "No new information this cycle; request one bounded revised plan before the next attempt.")
