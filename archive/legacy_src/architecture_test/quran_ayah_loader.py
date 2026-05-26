"""Load Quranic ayah text by surah:ayah from quran-uthmani.txt."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_FRACTAL_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_UTHMANI = _FRACTAL_ROOT / "new_arabic_analyzer" / "data" / "quran" / "quran-uthmani.txt"
# 94:6  |  94-6  |  Quran 94:6  |  سورة 94 آية 6
_AYAH_REF_RE = re.compile(
    r"^(?:quran\s+)?(?P<surah>\d{1,3})\s*[:./\-،]\s*(?P<ayah>\d{1,3})\s*$",
    re.IGNORECASE,
)
_AYAH_REF_AR_RE = re.compile(
    r"^سورة\s*(?P<surah>\d{1,3})\s*آية\s*(?P<ayah>\d{1,3})\s*$",
    re.IGNORECASE,
)


def default_quran_text_path() -> Path:
    return _DEFAULT_UTHMANI


def parse_ayah_ref(value: str) -> tuple[int, int] | None:
    """Parse surah:ayah reference string, or None if not a reference."""
    s = (value or "").strip()
    if not s:
        return None
    m = _AYAH_REF_RE.match(s) or _AYAH_REF_AR_RE.match(s)
    if not m:
        return None
    surah = int(m.group("surah"))
    ayah = int(m.group("ayah"))
    if surah < 1 or surah > 114 or ayah < 1:
        return None
    return surah, ayah


def format_ayah_reference(surah: int, ayah: int) -> str:
    return f"Quran {surah}:{ayah}"


def _build_ayah_index(path: Path) -> dict[tuple[int, int], str]:
    out: dict[tuple[int, int], str] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|", 2)
            if len(parts) < 3:
                continue
            try:
                surah = int(parts[0].strip())
                ayah = int(parts[1].strip())
            except ValueError:
                continue
            text = parts[2].strip()
            if text:
                out[(surah, ayah)] = text
    return out


@lru_cache(maxsize=4)
def _cached_ayah_index(path_str: str) -> dict[tuple[int, int], str]:
    return _build_ayah_index(Path(path_str))


def load_ayah_text_index(*, text_path: Path | None = None) -> dict[tuple[int, int], str]:
    p = (text_path or _DEFAULT_UTHMANI).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"Quran ayah text file not found: {p}")
    return _cached_ayah_index(str(p))


def get_ayah_text(
    surah: int,
    ayah: int,
    *,
    text_path: Path | None = None,
) -> str | None:
    idx = load_ayah_text_index(text_path=text_path)
    return idx.get((int(surah), int(ayah)))


def resolve_ayah_input(
    ref: str,
    *,
    text_path: Path | None = None,
) -> tuple[str, str, dict[str, Any]]:
    """
    Resolve surah:ayah reference to (ayah_text, reference_label, metadata).

    Raises ValueError when ref is invalid or ayah not found.
    """
    parsed = parse_ayah_ref(ref)
    if parsed is None:
        raise ValueError(
            f"Invalid ayah reference: {ref!r}\n"
            "Use surah:ayah, e.g. 94:6 or Quran 94:6 or سورة 94 آية 6"
        )
    surah, ayah = parsed
    uthmani = (text_path or _DEFAULT_UTHMANI).expanduser().resolve()
    text = get_ayah_text(surah, ayah, text_path=uthmani)
    if text is None:
        raise ValueError(f"Ayah not found: {format_ayah_reference(surah, ayah)} in {uthmani}")

    meta: dict[str, Any] = {
        "surah": surah,
        "ayah": ayah,
        "reference": format_ayah_reference(surah, ayah),
        "source_file": str(uthmani),
        "lookup": "quran-uthmani",
    }
    return text, meta["reference"], meta


def looks_like_ayah_ref(value: str) -> bool:
    return parse_ayah_ref(value) is not None
