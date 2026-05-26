"""regression_runner.py — wrapper حَول full_quran_audit و regression_harness.

Step F: نَقل/تَغليف فَقَط. لا يُغَيِّر شَيئًا في analyzer runtime.

API:
  • run_regression_sample(n=1000) -> dict     # عَيِّنَة سَريعَة
  • run_regression_full(start=0, end=None) -> dict
  • load_regression_summary(path=None) -> dict
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

# مَسار الجِذر
_HERE = Path(__file__).resolve().parent.parent.parent  # → clean_code/
_AUDIT_OUT = _HERE / "audit_outputs"


def load_regression_summary(path: Optional[Path] = None) -> dict:
    """يَقرأ full_quran_regression_summary.txt إلى dict مُنَظَّم.

    يُرجِع keys: total_tokens, matched_masaq, mismatched, alignment_pct,
                 by_class (dict: wc -> (correct, total, pct)),
                 source_dist (dict: source -> (count, pct)).
    """
    if path is None:
        path = _AUDIT_OUT / "full_quran_regression_summary.txt"
    if not path.exists():
        raise FileNotFoundError(f"Summary not found: {path}")

    out: dict = {"by_class": {}, "source_dist": {}}
    section = None
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("="): continue
        if "Total tokens evaluated" in s:
            out["total_tokens"] = int(s.split(":")[1].strip())
        elif "Matched MASAQ" in s:
            out["matched_masaq"] = int(s.split(":")[1].strip())
        elif "Mismatched" in s:
            out["mismatched"] = int(s.split(":")[1].strip())
        elif "MASAQ-alignment" in s:
            out["alignment_pct"] = float(s.split(":")[1].strip().rstrip("%"))
        elif "ACCURACY BY CLASS" in s:
            section = "class"
        elif "SOURCE DISTRIBUTION" in s:
            section = "src"
        elif "TOP CONFUSION" in s:
            section = None
        elif section == "class" and "=" in s:
            # e.g. "FIIL            19105/19130 = 99.87%"
            parts = s.split()
            wc = parts[0]
            try:
                num, den = parts[1].split("/")
                pct = float(parts[3].rstrip("%"))
                out["by_class"][wc] = (int(num), int(den), pct)
            except (ValueError, IndexError):
                pass
        elif section == "src" and "(" in s and "%" in s:
            # e.g. "MASAQ                          61637 (82.37%)"
            parts = s.split()
            src = parts[0]
            try:
                cnt = int(parts[1])
                pct = float(parts[2].strip("(%").rstrip(")%"))
                out["source_dist"][src] = (cnt, pct)
            except (ValueError, IndexError):
                pass
    return out


def run_regression_sample(n: int = 1000) -> dict:
    """يُشَغِّل audit عَلى أَوَّل n token. يُرجِع المُلَخَّص."""
    script = _HERE / "full_quran_audit.py"
    if not script.exists():
        raise FileNotFoundError(f"Audit script missing: {script}")
    # تَنظيف checkpoint لِضَمان sample نَقي
    ckpt = _AUDIT_OUT / "audit_checkpoint_sample.json"
    cmd = [sys.executable, str(script),
           "--start", "0", "--end", str(n),
           "--checkpoint", str(ckpt),
           "--skip-events"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(_HERE))
    if r.returncode != 0:
        raise RuntimeError(f"audit failed: {r.stderr[:500]}")
    return load_regression_summary()


def run_regression_full(start: int = 0, end: Optional[int] = None,
                        skip_events: bool = False) -> dict:
    """يُشَغِّل audit عَلى كُلّ القُرآن (أَو نِطاق)."""
    script = _HERE / "full_quran_audit.py"
    cmd = [sys.executable, str(script), "--start", str(start)]
    if end is not None:
        cmd += ["--end", str(end)]
    if skip_events:
        cmd.append("--skip-events")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(_HERE))
    if r.returncode != 0:
        raise RuntimeError(f"audit failed: {r.stderr[:500]}")
    return load_regression_summary()


__all__ = ["run_regression_sample", "run_regression_full", "load_regression_summary"]
