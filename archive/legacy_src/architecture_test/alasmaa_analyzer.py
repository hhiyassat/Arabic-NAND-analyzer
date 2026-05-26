"""DEPRECATED — superseded by ``analyze_word_adapter.py``.

The pipeline already integrates alasmaa via ``analyze_word_adapter.run_analyze_word_step``
as Step 0 (before architecture steps). This module is kept only as a thin
compatibility shim re-exporting the same functionality, so that any external
caller importing ``architecture_test.alasmaa_analyzer`` does not break.

For new code, prefer:

    from architecture_test.analyze_word_adapter import (
        load_analyze_word_module,
        load_mushtaqat_weights,
        analyze_token_surface,
        extract_root_from_match,
        run_analyze_word_step,
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .analyze_word_adapter import (
    _DEFAULT_WEIGHTS,
    _DEFAULT_WEIGHTS_XLSX,
    analyze_token_surface,
    extract_root_from_match,
    load_analyze_word_module,
    load_mushtaqat_weights,
)


@dataclass
class AlasmaaResult:
    """Compatibility wrapper around ``analyze_token_surface`` output."""

    is_operator: bool
    no_match: bool
    wazn: Optional[str]
    bab: Optional[str]
    root: Optional[str]
    variant: Optional[str]
    variant_label: Optional[str]
    all_candidates: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_operator": self.is_operator,
            "no_match": self.no_match,
            "wazn": self.wazn,
            "bab": self.bab,
            "root": self.root,
            "variant": self.variant,
            "variant_label": self.variant_label,
            "all_candidates": self.all_candidates,
        }


class AlasmaaAnalyzer:
    """Compatibility wrapper. Prefer analyze_word_adapter directly."""

    def __init__(self, weights_path: Path | None = None):
        self._mod = load_analyze_word_module()
        self.weights = load_mushtaqat_weights(self._mod, weights_path)
        self.weights_path = weights_path or _DEFAULT_WEIGHTS

    def analyze(self, token: str) -> AlasmaaResult:
        res = analyze_token_surface(self._mod, self.weights, token)
        status = res.get("status")
        return AlasmaaResult(
            is_operator=(status == "OPERATOR_SKIPPED"),
            no_match=(status in ("NO_WAZN", "NO_ROOT_FROM_WAZN")),
            wazn=res.get("best_wazn"),
            bab=res.get("bab"),
            root=res.get("extracted_root"),
            variant=None,
            variant_label=res.get("variant_label"),
            all_candidates=[],
        )

    def weights_count(self) -> int:
        return len(self.weights)


def load_alasmaa_analyzer(weights_path: Path | None = None) -> AlasmaaAnalyzer:
    return AlasmaaAnalyzer(weights_path=weights_path)


def extract_root_from_wazn(wazn: str, variant: str) -> Optional[str]:
    """Standalone helper preserved for callers that imported it directly."""
    mod = load_analyze_word_module()
    return extract_root_from_match(mod, {"weight": wazn, "variant": variant})
