"""baseline_comparator.py — مُقارَنَة metrics ضِدّ baseline مُجَمَّد (Step F).

يَقرأ:
  • audit_outputs/BASELINE_summary.txt              (frozen baseline)
  • audit_outputs/full_quran_regression_summary.txt (current)
  • audit_outputs/BASELINE_seg_leak.csv              (frozen)
  • audit_outputs/segmentation_leak_audit.csv       (current)
  • audit_outputs/BASELINE_false_events.csv         (frozen)
  • audit_outputs/false_event_audit.csv             (current)
  • audit_outputs/BASELINE_relation_sanity.csv      (frozen)
  • audit_outputs/relation_sanity_audit.csv         (current)

ويُنشِئ DriftReport يَرصُد أَيّ انحِراف غَير مُتَوَقَّع.

Tolerances (إِفتراضِيًّا):
  • alignment_pct        ± 0.10
  • class accuracy       ± 0.20
  • source_dist pct      ± 1.00
  • seg_leak ratio       ± 0.05  (نِسبَة لِلتوكنز المَفحوصَة)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .regression_runner import load_regression_summary

_HERE = Path(__file__).resolve().parent.parent.parent
_AUDIT_OUT = _HERE / "audit_outputs"

_DEFAULT_TOL = {
    "alignment_pct": 0.10,
    "class_acc": 0.20,
    "source_pct": 1.00,
    "seg_leak_ratio_pct": 0.05,
}


@dataclass
class DriftReport:
    """تَقرير drift شامِل."""
    alignment_baseline: float = 0.0
    alignment_current: float = 0.0
    alignment_drift: float = 0.0
    class_drifts: dict = field(default_factory=dict)
    source_drifts: dict = field(default_factory=dict)
    seg_leak_baseline_ratio: float = 0.0
    seg_leak_current_ratio: float = 0.0
    seg_leak_drift: float = 0.0
    false_event_baseline_count: int = 0
    false_event_current_count: int = 0
    relation_sanity_baseline: int = 0
    relation_sanity_current: int = 0
    test_count_baseline: int = 0
    test_count_current: int = 0
    flags: list[str] = field(default_factory=list)
    tolerances: dict = field(default_factory=lambda: dict(_DEFAULT_TOL))

    def is_clean(self) -> bool:
        return len(self.flags) == 0


def _count_lines(p: Path) -> int:
    if not p.exists():
        return 0
    return sum(1 for _ in p.open(encoding="utf-8")) - 1  # minus header


def compare_against_baseline(
    baseline_summary: Optional[Path] = None,
    current_summary: Optional[Path] = None,
    tolerances: Optional[dict] = None,
) -> DriftReport:
    """يُقارِن current vs baseline ويُرجِع DriftReport.

    إِذا الـpaths None، يَستَخدِم default audit_outputs/.
    """
    if baseline_summary is None:
        baseline_summary = _AUDIT_OUT / "BASELINE_summary.txt"
    if current_summary is None:
        current_summary = _AUDIT_OUT / "full_quran_regression_summary.txt"
    tol = dict(_DEFAULT_TOL)
    if tolerances:
        tol.update(tolerances)

    if not baseline_summary.exists():
        raise FileNotFoundError(f"baseline missing: {baseline_summary}")
    if not current_summary.exists():
        raise FileNotFoundError(f"current missing: {current_summary}")

    base = load_regression_summary(baseline_summary)
    curr = load_regression_summary(current_summary)

    rep = DriftReport(tolerances=tol)

    # alignment
    rep.alignment_baseline = base.get("alignment_pct", 0.0)
    rep.alignment_current = curr.get("alignment_pct", 0.0)
    rep.alignment_drift = rep.alignment_current - rep.alignment_baseline
    if abs(rep.alignment_drift) > tol["alignment_pct"]:
        rep.flags.append(
            f"alignment_drift {rep.alignment_drift:+.2f}% > tol {tol['alignment_pct']}%")

    # per-class accuracy
    for wc, (cor, tot, pct) in base["by_class"].items():
        if wc in curr["by_class"]:
            _, _, cur_pct = curr["by_class"][wc]
            d = cur_pct - pct
            rep.class_drifts[wc] = d
            if abs(d) > tol["class_acc"]:
                rep.flags.append(f"class_drift[{wc}] {d:+.2f}% > tol {tol['class_acc']}%")
        else:
            rep.flags.append(f"class_missing[{wc}]")

    # source distribution
    for src, (cnt, pct) in base["source_dist"].items():
        if src in curr["source_dist"]:
            _, cur_pct = curr["source_dist"][src]
            d = cur_pct - pct
            rep.source_drifts[src] = d
            if abs(d) > tol["source_pct"]:
                rep.flags.append(f"source_drift[{src}] {d:+.2f}% > tol {tol['source_pct']}%")
        else:
            rep.flags.append(f"source_missing[{src}]")

    # seg_leak ratio (lines / total_tokens)
    base_seg = _count_lines(_AUDIT_OUT / "BASELINE_seg_leak.csv")
    curr_seg = _count_lines(_AUDIT_OUT / "segmentation_leak_audit.csv")
    base_tot = base.get("total_tokens", 1)
    curr_tot = curr.get("total_tokens", 1)
    rep.seg_leak_baseline_ratio = (base_seg / max(base_tot, 1)) * 100
    rep.seg_leak_current_ratio = (curr_seg / max(curr_tot, 1)) * 100
    rep.seg_leak_drift = rep.seg_leak_current_ratio - rep.seg_leak_baseline_ratio
    if abs(rep.seg_leak_drift) > tol["seg_leak_ratio_pct"]:
        rep.flags.append(
            f"seg_leak_ratio_drift {rep.seg_leak_drift:+.3f}% > tol {tol['seg_leak_ratio_pct']}%")

    # false event count
    rep.false_event_baseline_count = _count_lines(_AUDIT_OUT / "BASELINE_false_events.csv")
    rep.false_event_current_count = _count_lines(_AUDIT_OUT / "false_event_audit.csv")

    # relation sanity rows
    rep.relation_sanity_baseline = _count_lines(_AUDIT_OUT / "BASELINE_relation_sanity.csv")
    rep.relation_sanity_current = _count_lines(_AUDIT_OUT / "relation_sanity_audit.csv")

    return rep


def has_drift(rep: DriftReport) -> bool:
    """True إذا أَيّ drift خَرَج عَن tolerances."""
    return not rep.is_clean()


__all__ = ["DriftReport", "compare_against_baseline", "has_drift"]
