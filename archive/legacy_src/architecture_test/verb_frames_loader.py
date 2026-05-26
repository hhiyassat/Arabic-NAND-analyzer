"""Load verb Frame Semantics extracted from Quranic i'rab corpus.

Source: hussein/data/extracted/verb_frames_from_quran_i3rab.csv
        Built from new_arabic_analyzer/data/quran/quran_i3rab.csv by tagging
        each i'rab row with a syntactic role and aggregating, for each verb
        surface, the roles that appeared within a 6-word window after it.

Computational-level loader. Per 11_Abstraction_Levels.md: serves the
LINGUISTIC level by providing empirical argument-structure data for verbs,
NOT a philosophical claim about event structure.

Coverage:
  - 6,757 unique verb surfaces (plain, diacritic-stripped)
  - Roles: subject, direct_object, prep_phrase, predicate, subject_nominal,
           state, specifier, purpose, cognate, locative_obj, comitative,
           past_verb, imperf_verb, imper_verb (the verb itself)
  - 19,349 total verb instances
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FRAMES_CSV = (
    _REPO_ROOT / "data" / "extracted" / "verb_frames_from_quran_i3rab.csv"
)

_DIACRITICS = set("ًٌٍَُِّْٰٓٔ")
_TATWEEL = "ـ"


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", str(text or "").strip())


def _strip_diacritics(text: str) -> str:
    return ''.join(c for c in _nfc(text) if c not in _DIACRITICS and c != _TATWEEL)


def _normalize_key(text: str) -> str:
    """Strip diacritics + tatweel for lookup matching."""
    return _strip_diacritics(text).strip()


# Role labels for display (Arabic + English)
ROLE_DISPLAY = {
    "subject": "فاعل",
    "subject_nominal": "مبتدأ",
    "direct_object": "مفعول به",
    "prep_phrase": "جار ومجرور",
    "predicate": "خبر",
    "state": "حال",
    "specifier": "تمييز",
    "purpose": "مفعول لأجله",
    "cognate": "مفعول مطلق",
    "locative_obj": "مفعول فيه",
    "comitative": "مفعول معه",
    "past_verb": "فعل ماضٍ (مجاور)",
    "imperf_verb": "فعل مضارع (مجاور)",
    "imper_verb": "فعل أمر (مجاور)",
    "genitive": "مضاف إليه",
    "attribute": "نعت",
    "particle": "حرف",
}


@dataclass(frozen=True)
class VerbFrame:
    verb_surface: str  # plain (no diacritics)
    occurrences: int  # how many times this surface form appears in the Quran
    total_args: int  # total argument instances observed across all occurrences
    role_counts: dict[str, int]  # role name → count

    def dominant_roles(self, n: int = 5, skip_verbs: bool = True) -> list[tuple[str, int]]:
        """Return top N roles, sorted by count descending. Skip 'verb' meta-roles
        which represent adjacent verbs, not arguments of this verb."""
        items = list(self.role_counts.items())
        if skip_verbs:
            items = [
                (r, c) for r, c in items
                if r not in ("past_verb", "imperf_verb", "imper_verb")
            ]
        items.sort(key=lambda x: x[1], reverse=True)
        return items[:n]

    def has_role(self, role: str) -> bool:
        return self.role_counts.get(role, 0) > 0


@dataclass
class VerbFramesIndex:
    """In-memory index for verb frames."""

    frames: list[VerbFrame] = field(default_factory=list)
    _by_plain: dict[str, VerbFrame] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for f in self.frames:
            key = _normalize_key(f.verb_surface)
            if key and key not in self._by_plain:
                self._by_plain[key] = f

    def lookup(self, surface: str) -> Optional[VerbFrame]:
        """Lookup by surface form (will strip diacritics automatically)."""
        key = _normalize_key(surface)
        if not key:
            return None
        return self._by_plain.get(key)

    def total_verbs(self) -> int:
        return len(self.frames)

    def coverage_stats(self) -> dict[str, int]:
        return {
            "unique_verbs": len(self.frames),
            "total_occurrences": sum(f.occurrences for f in self.frames),
            "total_args": sum(f.total_args for f in self.frames),
        }


def load_verb_frames_index(path: Path | None = None) -> VerbFramesIndex:
    csv_path = path or DEFAULT_FRAMES_CSV
    if not csv_path.is_file():
        raise FileNotFoundError(f"Verb frames dataset not found: {csv_path}")

    import csv as _csv
    frames: list[VerbFrame] = []
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = _csv.DictReader(f)
        for row in reader:
            surface = (row.get("verb_surface") or "").strip()
            if not surface:
                continue
            try:
                occurrences = int(row.get("occurrences") or 0)
                total_args = int(row.get("total_args") or 0)
            except (TypeError, ValueError):
                continue
            role_counts: dict[str, int] = {}
            for key, val in row.items():
                if not key or not key.startswith("role_"):
                    continue
                try:
                    val_i = int(float(val)) if val not in (None, "") else 0
                except (TypeError, ValueError):
                    val_i = 0
                if val_i > 0:
                    role_counts[key[5:]] = val_i  # strip "role_" prefix
            frames.append(
                VerbFrame(
                    verb_surface=surface,
                    occurrences=occurrences,
                    total_args=total_args,
                    role_counts=role_counts,
                )
            )
    return VerbFramesIndex(frames=frames)
