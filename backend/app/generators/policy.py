from dataclasses import dataclass
from typing import Literal

GenerationStatus = Literal["completed", "completed_with_errors", "waiting", "failed"]


@dataclass(frozen=True)
class CoverageDecision:
    coverage: float
    status: GenerationStatus


def coverage_decision(total: int, succeeded: int, failed: int, threshold: float) -> CoverageDecision:
    if total <= 0 or succeeded <= 0:
        return CoverageDecision(0.0, "failed")
    coverage = min(1.0, succeeded / total)
    if coverage < threshold:
        return CoverageDecision(coverage, "waiting")
    return CoverageDecision(coverage, "completed_with_errors" if failed else "completed")
