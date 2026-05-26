"""Architecture application tests (معمار المعنى العربي)."""

from .cli import main as cli_main
from .pipeline import ArchitectureTestResult, run_architecture_test, run_sample_01
from .pipeline import DEFAULT_SAMPLE as SAMPLE_01

__all__ = [
    "ArchitectureTestResult",
    "SAMPLE_01",
    "cli_main",
    "run_architecture_test",
    "run_sample_01",
]
