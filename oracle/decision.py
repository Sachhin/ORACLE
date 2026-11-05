"""Bounded autonomous decision policy."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Decision:
    action: str
    reason: str


def choose_next_action(cycle: int, max_cycles: int, progress: bool,
                       critical_warnings: int = 0) -> Decision:
    if critical_warnings:
        return Decision("replan", "Validation raised critical warnings; revise the plan before continuing.")
    if not progress:
        return Decision("stop", "No measurable progress in this cycle; stopping safely.")
    if cycle >= max_cycles:
        return Decision("conclude", "Configured cycle budget reached; save findings and open questions.")
    return Decision("continue", "Progress recorded and cycle budget remains.")
