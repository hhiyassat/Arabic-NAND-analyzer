"""Sample 01 defaults — Quran 94:6 (re-exports pipeline)."""

from .pipeline import (
    ArchitectureTestResult,
    DEFAULT_SAMPLE,
    LAYER_ORDER,
    STATE_PATTERNS,
    run_architecture_test,
    run_sample_01,
)

SAMPLE_01 = DEFAULT_SAMPLE

__all__ = [
    "ArchitectureTestResult",
    "LAYER_ORDER",
    "SAMPLE_01",
    "STATE_PATTERNS",
    "run_architecture_test",
    "run_sample_01",
]
