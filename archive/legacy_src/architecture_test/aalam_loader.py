"""Load the Aalam (proper names) dataset extracted from MASAQ Quranic corpus.

Source: hussein/data/extracted/aalam_from_masaq.csv
        Built from new_arabic_analyzer/data/MASAQ.csv by filtering Morph_Tag
        IN (NOUN_PROP, NOUN_PROP_FOREIGN), stripping clitic prefixes, and
        classifying into categories.

Computational-level loader. Per 11_Abstraction_Levels.md: serves the
LINGUISTIC level by providing closed-class proper-noun classification, NOT
a final philosophical statement on Entity-hood.

Coverage caveats (from data/extracted/README.md):
  - 193 unique proper nouns
  - Some prefix stripping is wrong (e.g., فرعون → رعون due to ف being stripped)
  - 85 entries currently in "other" category need manual review
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AALAM_CSV = _REPO_ROOT / "data" / "extracted" / "aalam_from_masaq.csv"

_DIACRITICS = set("ًٌٍَُِّْٰٓٔ")
_TATWEEL = "ـ"


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", str(text or "").strip())


def _strip_diacritics(text: str) -> str:
    d = unicodedata.normalize("NFD", _nfc(text))
    return unicodedata.normalize(
        "NFC",
        "".join(c for c in d if c not in _DIACRITICS and unicodedata.category(c) != "Mn"),
    )


def _normalize_lookup_key(text: str) -> str:
    """Strip diacritics + hamza variants + alif maqsurah for fuzzy match."""
    s = _strip_diacritics(text).replace(_TATWEEL, "")
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    s = s.replace("ى", "ي").replace("ة", "ه")
    return s.strip()


@dataclass(frozen=True)
class AalamEntry:
    canonical_plain: str
    canonical_vocalized: str
    count: int
    is_foreign: bool
    glosses: str
    surface_variants: str
    category: str  # divine_name / prophet / place / tribe_or_people / foreign_proper / other


@dataclass
class AalamIndex:
    """In-memory index for proper noun lookup with category."""

    entries: list[AalamEntry] = field(default_factory=list)
    _by_plain: dict[str, list[AalamEntry]] = field(default_factory=dict)
    _by_norm: dict[str, list[AalamEntry]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for e in self.entries:
            # Index by plain (Without_Diacritics from MASAQ)
            plain = _strip_diacritics(e.canonical_plain).strip()
            if plain:
                self._by_plain.setdefault(plain, []).append(e)
            # Also index by aggressively-normalized key
            norm = _normalize_lookup_key(e.canonical_plain)
            if norm:
                self._by_norm.setdefault(norm, []).append(e)
            # Index every surface variant the same way
            for surf in e.surface_variants.split(" / "):
                surf = surf.strip()
                if not surf:
                    continue
                splain = _strip_diacritics(surf)
                if splain and splain not in self._by_plain:
                    self._by_plain[splain] = [e]
                snorm = _normalize_lookup_key(surf)
                if snorm and snorm not in self._by_norm:
                    self._by_norm[snorm] = [e]

    def lookup(self, surface: str) -> list[AalamEntry]:
        """Return matching entries (could be multiple if the form is ambiguous).

        Tries: (1) exact plain match, (2) aggressive normalized key, then
        (3) progressively strips common clitic prefixes (و، ف، ل، ب، ت + ال)
        so لِلَّهِ → لله → الله, بِاللَّهِ → بالله → الله, etc.
        Quranic forms with assimilated ل (لِلَّه = لِـ + الله) are also handled
        by accepting both لله and لاله normalizations.
        """
        plain = _strip_diacritics(surface).strip()
        if plain and plain in self._by_plain:
            return list(self._by_plain[plain])
        norm = _normalize_lookup_key(surface)
        if norm and norm in self._by_norm:
            return list(self._by_norm[norm])

        # Progressively strip clitic prefixes — try most common combinations.
        # Order matters: longer/compound prefixes first, then single-letter.
        prefix_chains = [
            "وَفَ", "وَبِ", "وَلِ", "فَبِ", "فَلِ",
            "وَ", "فَ", "بِ", "لِ", "تَ", "كَ",
            # Plain (no harakah) variants for tolerant matching:
            "و", "ف", "ب", "ل", "ت", "ك",
        ]
        for prefix in prefix_chains:
            if surface.startswith(prefix):
                stripped = surface[len(prefix):]
                if stripped:
                    # Two attempts: as-is, and with ا inserted if the form is
                    # لله/بالله pattern (لِـ + الله = لِلَّه where two ل collide).
                    candidates = [stripped]
                    p_stripped = _strip_diacritics(stripped)
                    if prefix.startswith("ل") and p_stripped.startswith("له"):
                        # لله → الله reconstruction
                        candidates.append("الله")
                        candidates.append("اللَّه")
                    if prefix.startswith("ل") and p_stripped.startswith("لله"):
                        candidates.append("الله")
                    if p_stripped.startswith("ال"):
                        candidates.append(stripped)
                    for c in candidates:
                        p = _strip_diacritics(c).strip()
                        if p in self._by_plain:
                            return list(self._by_plain[p])
                        n = _normalize_lookup_key(c)
                        if n in self._by_norm:
                            return list(self._by_norm[n])

        # Direct check for لله/بالله-style surfaces that didn't strip cleanly:
        # if the form normalizes to a key containing "الله", look up "الله".
        norm_full = _normalize_lookup_key(surface)
        if "الله" in norm_full or norm_full.endswith("لله"):
            key = _normalize_lookup_key("الله")
            if key in self._by_norm:
                return list(self._by_norm[key])
        return []

    def is_aalam(self, surface: str) -> bool:
        return len(self.lookup(surface)) > 0

    def category_for(self, surface: str) -> Optional[str]:
        hits = self.lookup(surface)
        if not hits:
            return None
        # Prefer non-"other" categories
        for h in hits:
            if h.category != "other":
                return h.category
        return hits[0].category

    def stats(self) -> dict[str, int]:
        from collections import Counter
        c = Counter(e.category for e in self.entries)
        return dict(c)


def load_aalam_index(path: Path | None = None) -> AalamIndex:
    csv_path = path or DEFAULT_AALAM_CSV
    if not csv_path.is_file():
        raise FileNotFoundError(f"Aalam dataset not found: {csv_path}")

    import csv as _csv
    entries: list[AalamEntry] = []
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = _csv.DictReader(f)
        for row in reader:
            try:
                count = int(row.get("count") or 0)
            except (TypeError, ValueError):
                count = 0
            is_foreign_raw = str(row.get("is_foreign") or "").strip().lower()
            is_foreign = is_foreign_raw in ("true", "1", "yes")
            entries.append(
                AalamEntry(
                    canonical_plain=row.get("canonical_plain", "").strip(),
                    canonical_vocalized=row.get("canonical_vocalized", "").strip(),
                    count=count,
                    is_foreign=is_foreign,
                    glosses=row.get("glosses", "").strip(),
                    surface_variants=row.get("surface_variants", "").strip(),
                    category=row.get("category", "other").strip() or "other",
                )
            )
    return AalamIndex(entries=entries)
