"""Bridge to fractal unified segmenter + normalization.

Primary (Step 0a):
  fractal/segmenter — canonical wazn-validated conservative segmenter

Fallback:
  salehan/Salehan19-6-67/src/analyzer/segmentation/segmenter.py

Normalizer (Step −1):
  fractal/segmenter.normalize_text, with alef-madda alif restoration patch
  (NAA maps آ → ءَ without following ا; we restore ءَا when needed).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_FRACTAL_ROOT = Path(__file__).resolve().parents[3]

_NORMALIZER_CANDIDATES = [
    _FRACTAL_ROOT / "new_arabic_analyzer" / "src" / "standalone_segmenter" / "normalize.py",
    Path("/sessions/nice-epic-cannon/mnt/new_arabic_analyzer/src/standalone_segmenter/normalize.py"),
]
_SEGMENTER_SRC_CANDIDATES = [
    _FRACTAL_ROOT / "salehan" / "Salehan19-6-67" / "src",
    Path("/sessions/nice-epic-cannon/mnt/salehan/Salehan19-6-67/src"),
]

_UNIFIED_SEGMENTER = None
_UNIFIED_AVAILABLE = False
_LEGACY_SEGMENTER = None
_LEGACY_AVAILABLE = False
_LEGACY_SRC: Path | None = None
_NORMALIZE_MOD = None
_NORMALIZE_AVAILABLE = False


def _ensure_fractal_on_path() -> None:
    root = str(_FRACTAL_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _load_unified_segmenter():
    global _UNIFIED_SEGMENTER, _UNIFIED_AVAILABLE
    if _UNIFIED_SEGMENTER is not None:
        return _UNIFIED_SEGMENTER
    _ensure_fractal_on_path()
    try:
        import segmenter as mod  # noqa: WPS433 — intentional package load

        _UNIFIED_SEGMENTER = mod
        _UNIFIED_AVAILABLE = True
        return mod
    except ImportError:
        _UNIFIED_AVAILABLE = False
        return None


def _first_existing_file(candidates: list[Path]) -> Path | None:
    for p in candidates:
        if p.is_file():
            return p
    return None


def _first_existing_dir(candidates: list[Path]) -> Path | None:
    for p in candidates:
        if p.is_dir():
            return p
    return None


def _restore_alef_after_hamza_fatha(text: str) -> str:
    """Insert ا after ءَ when madda decomposition omitted the alif."""
    if "ءَ" not in text:
        return text
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        if i + 1 < n and text[i] == "ء" and text[i + 1] == "َ":
            out.append(text[i])
            out.append(text[i + 1])
            if i + 2 >= n or text[i + 2] != "ا":
                out.append("ا")
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _load_normalize_module():
    global _NORMALIZE_MOD, _NORMALIZE_AVAILABLE
    if _NORMALIZE_MOD is not None:
        return _NORMALIZE_MOD
    unified = _load_unified_segmenter()
    if unified is not None:
        _NORMALIZE_MOD = unified
        _NORMALIZE_AVAILABLE = True
        return unified
    path = _first_existing_file(_NORMALIZER_CANDIDATES)
    if path is None:
        _NORMALIZE_AVAILABLE = False
        return None
    name = "naa_normalize_architecture_test"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    _NORMALIZE_MOD = mod
    _NORMALIZE_AVAILABLE = True
    return mod


def normalize_text_pre_pipeline(text: str) -> str:
    mod = _load_normalize_module()
    base = mod.normalize_text(text) if mod is not None else (text or "")
    return _restore_alef_after_hamza_fatha(base)


def _load_legacy_segmenter():
    global _LEGACY_SEGMENTER, _LEGACY_AVAILABLE, _LEGACY_SRC
    if _LEGACY_SEGMENTER is not None:
        return _LEGACY_SEGMENTER
    src = _first_existing_dir(_SEGMENTER_SRC_CANDIDATES)
    if src is None:
        _LEGACY_AVAILABLE = False
        return None
    _LEGACY_SRC = src
    src_str = str(src)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
    try:
        from analyzer.segmentation import segmenter as seg  # type: ignore

        _LEGACY_SEGMENTER = seg
        _LEGACY_AVAILABLE = True
        return seg
    except ImportError:
        _LEGACY_AVAILABLE = False
        return None


def _active_segmenter_source() -> str:
    if _UNIFIED_AVAILABLE:
        return str(_FRACTAL_ROOT / "segmenter" / "core.py")
    if _LEGACY_SRC:
        return str(_LEGACY_SRC / "analyzer" / "segmentation" / "segmenter.py")
    return "(segmenter not loaded)"


def segment_one(surface: str) -> dict[str, Any]:
    unified = _load_unified_segmenter()
    if unified is not None:
        try:
            return unified.segment_token(surface)
        except Exception as exc:  # pragma: no cover
            return _trivial_segment(surface, f"segmenter_error: {type(exc).__name__}: {exc}")

    legacy = _load_legacy_segmenter()
    if legacy is not None:
        try:
            return legacy.segment_token(surface)
        except Exception as exc:  # pragma: no cover
            return _trivial_segment(surface, f"segmenter_error: {type(exc).__name__}: {exc}")

    return _trivial_segment(surface, "segmenter_unavailable")


def _trivial_segment(surface: str, note: str) -> dict[str, Any]:
    return {
        "original": surface,
        "prefixes": [],
        "stem": surface,
        "suffixes": [],
        "segmented": False,
        "notes": [note],
    }


def segment_tokens(tokens: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _load_unified_segmenter()
    _load_legacy_segmenter()
    enriched: list[dict[str, Any]] = []
    counts: dict[str, int] = {"segmented": 0, "unchanged": 0}
    per_token: list[dict[str, Any]] = []

    for tok in tokens:
        surf = tok["surface"]
        seg = segment_one(surf)
        if seg.get("segmented"):
            counts["segmented"] += 1
        else:
            counts["unchanged"] += 1
        enriched.append({**tok, "segmentation": seg})
        per_token.append(
            {
                "index": tok.get("index"),
                "surface": surf,
                "prefixes": seg.get("prefixes", []),
                "stem": seg.get("stem", surf),
                "suffixes": seg.get("suffixes", []),
                "segmented": seg.get("segmented", False),
            }
        )

    summary = {
        "source": _active_segmenter_source(),
        "available": _UNIFIED_AVAILABLE or _LEGACY_AVAILABLE,
        "engine": "fractal/segmenter" if _UNIFIED_AVAILABLE else (
            "salehan/legacy" if _LEGACY_AVAILABLE else "none"
        ),
        "counts": counts,
        "per_token": per_token,
    }
    return enriched, summary


def normalize_summary() -> dict[str, Any]:
    mod = _load_normalize_module()
    if _UNIFIED_AVAILABLE:
        source = str(_FRACTAL_ROOT / "segmenter" / "normalize.py")
    else:
        source = str(_first_existing_file(_NORMALIZER_CANDIDATES) or "(not found)")
    return {
        "source": source,
        "available": _NORMALIZE_AVAILABLE,
        "engine": "fractal/segmenter" if _UNIFIED_AVAILABLE else "naa/standalone",
    }
