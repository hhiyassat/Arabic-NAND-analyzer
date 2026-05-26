#!/usr/bin/env python3
"""
a0_phase4_pipeline_probe.py — A0 Runner Template (NOT a completed A0)

Purpose
-------
A0 = measure whether `classify_with_context` is actually used by the current
full pipeline, and whether phase4 metadata propagates downstream — WITHOUT
modifying Phase C/D, L4/L5, gates, or unresolved rules.

Status
------
This script is a template. It does NOT report A0 results until it is executed
inside the real project repository with the two EDIT POINTs filled in.

Run modes
---------
  python a0_phase4_pipeline_probe.py --dry-run    # verify environment only
  python a0_phase4_pipeline_probe.py              # run real OFF/ON sweep

Outputs (created next to CWD, under audit_outputs/)
---------------------------------------------------
  audit_outputs/a0_flag_off/                       # raw + metrics for OFF
  audit_outputs/a0_flag_on/                        # raw + metrics for ON
  audit_outputs/A0_PHASE4_PIPELINE_ON_OFF_COMPARISON.md
  audit_outputs/A0_STATUS.json                     # machine-readable verdict

A0_STATUS.json schema
---------------------
{
  "a0_executed": bool,
  "repo_detected": bool,
  "pipeline_runner_configured": bool,
  "flag_off_completed": bool,
  "flag_on_completed": bool,
  "classify_call_count": int,
  "classify_with_context_call_count": int,
  "verdict": "FIX_LAYER1_HOOK" | "WIRE_PHASE4_INTO_L6_L7"
           | "RESOLVER_EFFECT_DOWNSTREAM_OK" | "A0_NOT_EXECUTED"
}

Fail-fast
---------
If the real sweep runner is not configured, the script exits immediately with:
  "A0_NOT_EXECUTED: real pipeline runner is not configured"

Flag semantics
--------------
Flag OFF truly unsets the env var (so any `bool(os.getenv(...))` check in the
integration evaluates as False). Flag ON sets it to "1".
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from collections import Counter
from pathlib import Path
from typing import Any, Callable

# ============================================================================
# CONFIG — edit points + sentinel
# ============================================================================

PROJECT_ROOT = Path(os.environ.get("ARABIC_ANALYZER_ROOT", ".")).resolve()
FLAG_ENV = "ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER"

# Flip to True ONLY after both EDIT POINT #1 and EDIT POINT #2 are filled in.
RUNNER_CONFIGURED: bool = False

# EDIT POINT #2 (PREFERRED): dotted callable specs.
# Format: "module.path:Class.method" or "module.path:function"
# TODO: set real callable specs for classify/classify_with_context
CANDIDATE_CALLABLES: list[str] = [
    # "i3rab_engine.layer1:WordClassClassifier.classify",
    # "i3rab_engine.layer1:WordClassClassifier.classify_with_context",
]

# EDIT POINT #2 (LEGACY, backward compatibility): module-level only.
# Each module here is expanded into "<mod>:classify" and "<mod>:classify_with_context".
# Prefer CANDIDATE_CALLABLES for class methods.
CANDIDATE_MODULES: list[str] = [
    # "arabic_analyzer.layer1.classifier",
]

# Optional sanity files: their presence confirms the repo is the right one.
EXPECTED_PROJECT_FILES: list[str] = [
    # "src/sweep_main.py",
    # "src/layer1/__init__.py",
]

# Acceptance thresholds (fractional tolerance on event/relation deltas).
EPSILON_EVENT = 0.01
EPSILON_RELATION = 0.01

CALL_COUNTERS: Counter[str] = Counter()
FIRST_TRACES: dict[str, list[str]] = {}


# ============================================================================
# EDIT POINT #1: real sweep entry point
# ============================================================================

def run_pipeline() -> dict[str, Any]:
    """
    TODO: import real sweep runner here

    Replace the body of this function with the real entry point used in
    production. Example:

        sys.path.insert(0, str(PROJECT_ROOT))
        from sweep_main import run_full_sweep
        return run_full_sweep()

    Expected return shape (dict OR list of per-ayah dicts):
      ayahs[].tokens[].phase4.{selected_function, certainty, source,
                               unresolved_ambiguous}
      ayahs[].tokens[].{qa_zero, is_interrogative_marker, segmentation_leak}
      ayahs[].events[].{head.surface, surface, is_fragment}
      ayahs[].relations[].{kind|type}
    """
    raise NotImplementedError(
        "EDIT POINT #1 not filled in. See docstring of run_pipeline()."
    )


# ============================================================================
# FLAG CONTROL
# ============================================================================

def _set_flag(flag_value):
    if str(flag_value).lower() in ("0", "false", "off", ""):
        os.environ.pop(FLAG_ENV, None)
    else:
        os.environ[FLAG_ENV] = "1"


# ============================================================================
# SPEC PARSING & TRACER (supports module-level functions AND class methods)
# ============================================================================

def _all_specs() -> list[str]:
    """Unified spec list: CANDIDATE_CALLABLES + auto-expanded CANDIDATE_MODULES."""
    specs = list(CANDIDATE_CALLABLES)
    for mod in CANDIDATE_MODULES:
        specs.append(f"{mod}:classify")
        specs.append(f"{mod}:classify_with_context")
    return specs


def _final_name(spec: str) -> str:
    if ":" in spec:
        return spec.split(":", 1)[1].split(".")[-1]
    return spec.split(".")[-1]


def _resolve_spec(spec: str):
    """Parse 'module.path:attr.path' into (parent, attr_name, raw_descriptor).

    raw_descriptor is what is stored in parent.__dict__[attr_name] (so we can
    detect staticmethod / classmethod / plain function), or None if the attr
    is inherited and not directly defined on parent.

    Raises on missing module / missing attribute.
    """
    if ":" not in spec:
        raise ValueError(
            f"spec must contain ':' separating module from attribute path: {spec!r}"
        )
    mod_name, attr_path = spec.split(":", 1)
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    mod = __import__(mod_name, fromlist=["*"])
    parts = attr_path.split(".")
    parent = mod
    for p in parts[:-1]:
        parent = getattr(parent, p)
    final_name = parts[-1]
    if not hasattr(parent, final_name):
        raise AttributeError(
            f"{spec}: attribute {final_name!r} not found on {parent!r}"
        )
    raw = None
    if hasattr(parent, "__dict__"):
        try:
            raw = parent.__dict__.get(final_name)
        except Exception:  # noqa: BLE001
            raw = None
    return parent, final_name, raw


def _make_wrapper(orig: Callable, key: str) -> Callable:
    def wrapper(*args, **kwargs):
        CALL_COUNTERS[key] += 1
        if key not in FIRST_TRACES:
            FIRST_TRACES[key] = traceback.format_stack()
        return orig(*args, **kwargs)
    wrapper.__wrapped__ = orig
    return wrapper


def _install_tracer() -> Callable[[], None]:
    """Patch every spec in _all_specs(). Supports module functions, regular
    methods, staticmethods, and classmethods. Restores everything on uninstall.
    """
    restorations: list[tuple[Any, str, Any, str]] = []

    for spec in _all_specs():
        try:
            parent, attr_name, raw = _resolve_spec(spec)
        except Exception as exc:  # noqa: BLE001
            print(f"[tracer] cannot resolve {spec}: {exc}", file=sys.stderr)
            continue

        key = spec

        if isinstance(parent, type):
            # Class member — inspect descriptor in __dict__.
            if isinstance(raw, staticmethod):
                orig_fn = raw.__func__
                wrapper = staticmethod(_make_wrapper(orig_fn, key))
                setattr(parent, attr_name, wrapper)
                restorations.append((parent, attr_name, raw, "static"))
            elif isinstance(raw, classmethod):
                orig_fn = raw.__func__
                wrapper = classmethod(_make_wrapper(orig_fn, key))
                setattr(parent, attr_name, wrapper)
                restorations.append((parent, attr_name, raw, "class"))
            elif callable(raw):
                wrapper = _make_wrapper(raw, key)
                setattr(parent, attr_name, wrapper)
                restorations.append((parent, attr_name, raw, "method"))
            else:
                # Attribute inherited from a base class (not in this class's __dict__).
                inherited = getattr(parent, attr_name, None)
                if not callable(inherited):
                    print(f"[tracer] {spec}: not callable, skipping",
                          file=sys.stderr)
                    continue
                wrapper = _make_wrapper(inherited, key)
                setattr(parent, attr_name, wrapper)
                # Restore by removing the local override so lookup falls back to base.
                restorations.append((parent, attr_name, None, "inherited"))
        else:
            # Module-level function (or other non-class parent).
            orig_fn = getattr(parent, attr_name, None)
            if not callable(orig_fn):
                print(f"[tracer] {spec}: not callable, skipping",
                      file=sys.stderr)
                continue
            wrapper = _make_wrapper(orig_fn, key)
            setattr(parent, attr_name, wrapper)
            restorations.append((parent, attr_name, orig_fn, "module"))

    def uninstall() -> None:
        for parent, attr_name, original, kind in restorations:
            if kind == "inherited":
                try:
                    delattr(parent, attr_name)
                except AttributeError:
                    pass
            else:
                setattr(parent, attr_name, original)

    return uninstall


# ============================================================================
# METRIC EXTRACTION
# ============================================================================

REQUIRED_METRICS = [
    "total_analyzed_ayahs",
    "total_tokens",
    "classify_with_context_call_count",
    "classify_call_count",
    "contextual_resolver_applications",
    "phase4_selected_function_count",
    "phase4_certificate_count",
    "phase4_hypothesis_count",
    "unresolved_ambiguous_count",
    "qa_zeros",
    "unresolved_edges",
    "relative_edges",
    "conditional_edges",
    "interrogative_markers",
    "event_count",
    "relation_count",
    "event_ik_count",
    "segmentation_leak_count",
    "fragment_event_count",
]


def _iter_tokens(payload: Any):
    ayahs = payload["ayahs"] if isinstance(payload, dict) and "ayahs" in payload \
        else payload if isinstance(payload, list) else []
    for ayah in ayahs:
        for tok in ayah.get("tokens", []) or []:
            yield ayah, tok


def _iter_events(payload: Any):
    ayahs = payload["ayahs"] if isinstance(payload, dict) and "ayahs" in payload \
        else payload if isinstance(payload, list) else []
    for ayah in ayahs:
        for ev in ayah.get("events", []) or []:
            yield ayah, ev


def _iter_relations(payload: Any):
    ayahs = payload["ayahs"] if isinstance(payload, dict) and "ayahs" in payload \
        else payload if isinstance(payload, list) else []
    for ayah in ayahs:
        for rel in ayah.get("relations", []) or []:
            yield ayah, rel


def extract_metrics(payload: Any) -> dict[str, int]:
    m: dict[str, int] = {k: 0 for k in REQUIRED_METRICS}

    # Match by final attribute name so both module-fn and class-method keys count.
    m["classify_with_context_call_count"] = sum(
        v for k, v in CALL_COUNTERS.items() if _final_name(k) == "classify_with_context"
    )
    m["classify_call_count"] = sum(
        v for k, v in CALL_COUNTERS.items() if _final_name(k) == "classify"
    )

    seen_ayahs = set()
    for ayah, tok in _iter_tokens(payload):
        seen_ayahs.add(id(ayah))
        m["total_tokens"] += 1
        phase4 = tok.get("phase4") or {}
        if phase4.get("selected_function"):
            m["phase4_selected_function_count"] += 1
        if phase4.get("certainty") == "Certificate":
            m["phase4_certificate_count"] += 1
        if phase4.get("certainty") == "Hypothesis":
            m["phase4_hypothesis_count"] += 1
        if phase4.get("source") == "ContextualAmbiguityResolver":
            m["contextual_resolver_applications"] += 1
        if phase4.get("unresolved_ambiguous"):
            m["unresolved_ambiguous_count"] += 1
        if tok.get("qa_zero"):
            m["qa_zeros"] += 1
        if tok.get("is_interrogative_marker"):
            m["interrogative_markers"] += 1
        if tok.get("segmentation_leak"):
            m["segmentation_leak_count"] += 1

    m["total_analyzed_ayahs"] = len(seen_ayahs)

    for _ayah, ev in _iter_events(payload):
        m["event_count"] += 1
        head = (ev.get("head") or {}).get("surface") or ev.get("surface") or ""
        if "ئك" in head:
            m["event_ik_count"] += 1
        if ev.get("is_fragment"):
            m["fragment_event_count"] += 1

    for _ayah, rel in _iter_relations(payload):
        m["relation_count"] += 1
        kind = rel.get("kind") or rel.get("type")
        if kind == "unresolved":
            m["unresolved_edges"] += 1
        elif kind == "relative":
            m["relative_edges"] += 1
        elif kind == "conditional":
            m["conditional_edges"] += 1
    return m


# ============================================================================
# DRY-RUN ENVIRONMENT VERIFIER
# ============================================================================

def _check(label: str, ok: bool, detail: str = "") -> tuple[str, bool, str]:
    marker = "OK " if ok else "FAIL"
    print(f"  [{marker}] {label}" + (f" — {detail}" if detail else ""))
    return label, ok, detail


def dry_run(out_root: Path) -> int:
    print("[A0] dry-run — verifying environment, not running sweep")
    results: list[tuple[str, bool, str]] = []

    cwd = Path.cwd().resolve()
    results.append(_check("current working directory", True, str(cwd)))

    repo_detected = PROJECT_ROOT.exists() and PROJECT_ROOT.is_dir()
    results.append(_check("project root exists", repo_detected, str(PROJECT_ROOT)))

    if EXPECTED_PROJECT_FILES:
        missing = [f for f in EXPECTED_PROJECT_FILES
                   if not (PROJECT_ROOT / f).exists()]
        results.append(_check(
            "expected project files present",
            not missing,
            "missing: " + ", ".join(missing) if missing else "all listed files found",
        ))
    else:
        results.append(_check(
            "expected project files present",
            False,
            "EXPECTED_PROJECT_FILES is empty — fill it in for stronger repo detection",
        ))

    runner_ok = RUNNER_CONFIGURED
    runner_detail = "RUNNER_CONFIGURED is False" if not runner_ok else "sentinel set"
    if runner_ok:
        try:
            import dis
            instrs = list(dis.get_instructions(run_pipeline))
            raises_notimpl = any(
                i.opname == "RAISE_VARARGS" for i in instrs
            ) and any(
                "NotImplementedError" in repr(getattr(i, "argval", ""))
                for i in instrs
            )
            if raises_notimpl:
                runner_ok = False
                runner_detail = "run_pipeline() still raises NotImplementedError"
        except Exception as exc:  # noqa: BLE001
            runner_detail = f"introspection failed: {exc}"
    results.append(_check("sweep runner configured", runner_ok, runner_detail))

    # Verify every spec: module imports, attribute chain walks, final is callable.
    specs = _all_specs()
    if not specs:
        results.append(_check(
            "callable specs listed", False,
            "both CANDIDATE_CALLABLES and CANDIDATE_MODULES are empty — fill EDIT POINT #2",
        ))
    else:
        for spec in specs:
            try:
                parent, attr_name, raw = _resolve_spec(spec)
            except Exception as exc:  # noqa: BLE001
                results.append(_check(f"resolve {spec}", False, str(exc)))
                continue
            parent_kind = "class" if isinstance(parent, type) else "module"
            results.append(_check(
                f"resolve {spec}", True, f"parent={parent_kind}"))
            final_attr = getattr(parent, attr_name, None)
            is_call = callable(final_attr)
            if isinstance(raw, staticmethod):
                desc = "staticmethod"
            elif isinstance(raw, classmethod):
                desc = "classmethod"
            elif isinstance(parent, type) and callable(raw):
                desc = "method"
            elif not isinstance(parent, type):
                desc = "module-fn"
            else:
                desc = "inherited"
            results.append(_check(f"{spec} callable ({desc})", is_call))

    try:
        out_root.mkdir(parents=True, exist_ok=True)
        probe = out_root / ".write_probe"
        probe.write_text("ok")
        probe.unlink()
        results.append(_check("output directory writable", True, str(out_root)))
    except Exception as exc:  # noqa: BLE001
        results.append(_check("output directory writable", False, str(exc)))

    all_ok = all(r[1] for r in results)
    print("")
    print(f"[A0] dry-run verdict: {'READY' if all_ok else 'NOT READY'}")
    return 0 if all_ok else 2


# ============================================================================
# REAL RUN — OFF then ON
# ============================================================================

def _reset_counters() -> None:
    CALL_COUNTERS.clear()
    FIRST_TRACES.clear()


def _safe_run(flag_value: str, run_dir: Path) -> dict[str, int]:
    _set_flag(flag_value)
    _reset_counters()
    uninstall = _install_tracer()
    try:
        t0 = time.time()
        payload = run_pipeline()
        elapsed = time.time() - t0
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "sweep.json").write_text(
            json.dumps(payload, ensure_ascii=False, default=str))
        metrics = extract_metrics(payload)
        metrics["wall_seconds"] = round(elapsed, 2)
        (run_dir / "metrics.json").write_text(
            json.dumps(metrics, indent=2, ensure_ascii=False))
        trace_lines: list[str] = []
        for key, frames in FIRST_TRACES.items():
            trace_lines.append(f"==== {key} (first observed call) ====\n")
            trace_lines.extend(frames)
            trace_lines.append("\n")
        (run_dir / "call_trace.txt").write_text("".join(trace_lines))
        return metrics
    finally:
        uninstall()


def _verdict(m_off: dict[str, int], m_on: dict[str, int]) -> str:
    if m_on["classify_with_context_call_count"] == 0:
        return "FIX_LAYER1_HOOK"
    if m_on["phase4_selected_function_count"] == 0:
        return "WIRE_PHASE4_INTO_L6_L7"
    return "RESOLVER_EFFECT_DOWNSTREAM_OK"


def _markdown_report(m_off: dict[str, int], m_on: dict[str, int],
                     verdict: str) -> str:
    rows = ["| metric | OFF | ON | delta |", "|---|---:|---:|---:|"]
    for k in REQUIRED_METRICS:
        off = m_off.get(k, 0)
        on = m_on.get(k, 0)
        rows.append(f"| {k} | {off} | {on} | {on - off:+d} |")
    return (
        "# A0 — Phase 4 Pipeline ON/OFF Comparison\n\n"
        f"Verdict: **{verdict}**\n\n"
        "## Metrics\n\n" + "\n".join(rows) + "\n"
    )


def real_run(out_root: Path) -> int:
    if not RUNNER_CONFIGURED:
        msg = "A0_NOT_EXECUTED: real pipeline runner is not configured"
        print(msg, file=sys.stderr)
        out_root.mkdir(parents=True, exist_ok=True)
        (out_root / "A0_STATUS.json").write_text(json.dumps({
            "a0_executed": False,
            "repo_detected": PROJECT_ROOT.exists(),
            "pipeline_runner_configured": False,
            "flag_off_completed": False,
            "flag_on_completed": False,
            "classify_call_count": 0,
            "classify_with_context_call_count": 0,
            "verdict": "A0_NOT_EXECUTED",
        }, indent=2))
        return 3

    off_dir = out_root / "a0_flag_off"
    on_dir = out_root / "a0_flag_on"
    status: dict[str, Any] = {
        "a0_executed": False,
        "repo_detected": PROJECT_ROOT.exists(),
        "pipeline_runner_configured": True,
        "flag_off_completed": False,
        "flag_on_completed": False,
        "classify_call_count": 0,
        "classify_with_context_call_count": 0,
        "verdict": "A0_NOT_EXECUTED",
    }

    print("[A0] running OFF ...")
    m_off = _safe_run("0", off_dir)
    status["flag_off_completed"] = True

    print("[A0] running ON  ...")
    m_on = _safe_run("1", on_dir)
    status["flag_on_completed"] = True

    verdict = _verdict(m_off, m_on)
    (out_root / "A0_PHASE4_PIPELINE_ON_OFF_COMPARISON.md").write_text(
        _markdown_report(m_off, m_on, verdict))

    status.update({
        "a0_executed": True,
        "classify_call_count": m_on["classify_call_count"],
        "classify_with_context_call_count": m_on["classify_with_context_call_count"],
        "verdict": verdict,
    })
    (out_root / "A0_STATUS.json").write_text(
        json.dumps(status, indent=2, ensure_ascii=False))

    print(f"[A0] done -> {out_root}/A0_PHASE4_PIPELINE_ON_OFF_COMPARISON.md")
    print(f"[A0] verdict = {verdict}")
    return 0


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="verify environment without running the sweep")
    parser.add_argument("--out", default="audit_outputs",
                        help="output root (default: audit_outputs)")
    args = parser.parse_args()
    out_root = Path(args.out).resolve()
    if args.dry_run:
        return dry_run(out_root)
    return real_run(out_root)


if __name__ == "__main__":
    sys.exit(main())
