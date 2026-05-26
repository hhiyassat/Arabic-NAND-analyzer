"""Load Semantic Fields seed data.

Source: hussein/data/extracted/semantic_fields/*.json
        Hand-curated seed of 8 lexical fields: kinship, body_parts, colors,
        animals, plants, weather, celestial, professions. ~200 members total.

Computational-level loader. Per 11_Abstraction_Levels.md: serves the
LINGUISTIC level by providing membership in lexical sets, NOT a final
philosophical statement on conceptual structure.

Note: This is a SEED, NOT a closed lexicon. Negative lookup means
'not in the seed', NOT 'not in the field'.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIELDS_DIR = _REPO_ROOT / "data" / "extracted" / "semantic_fields"

_DIACRITICS = set("ًٌٍَُِّْٰٓٔ")
_TATWEEL = "ـ"


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", str(text or "").strip())


def _strip_diacritics(text: str) -> str:
    return ''.join(c for c in _nfc(text) if c not in _DIACRITICS and c != _TATWEEL)


def _normalize_lookup_key(text: str) -> str:
    """Diacritics off + hamza/alif-maqsurah variants normalized."""
    raw = str(text or "")
    has_tanwin = any(c in raw for c in "ًٌٍ")
    s = _strip_diacritics(raw)
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    s = s.replace("ى", "ي").replace("ة", "ه")
    s = s.strip()
    # Strip trailing alif from tanwin-fath.
    if has_tanwin and s.endswith("ا") and len(s) > 3:
        s = s[:-1]
    return s


# Common attached pronoun suffixes (clitics) — longest-first.
_PRONOUN_SUFFIXES_PLAIN = (
    "كما", "هما", "كم", "كن", "هم", "هن", "نا", "ها", "ني",
    "ك", "ه", "ي",
)


def _candidates_with_suffix_strip(text: str) -> list[str]:
    """Generate lookup candidates by stripping common pronoun suffixes."""
    base = _normalize_lookup_key(text)
    out = [base]
    for suf in _PRONOUN_SUFFIXES_PLAIN:
        if base.endswith(suf) and len(base) - len(suf) >= 2:
            cand = base[: -len(suf)]
            # Also try variant with ه → ة restored (هاء التأنيث)
            if cand not in out:
                out.append(cand)
            if cand.endswith("ت") and cand + "ه" not in out:
                # e.g., تفاحت + ها → تفاحت → restore تفاحة
                pass
    return out


@dataclass(frozen=True)
class FieldMember:
    field_name_ar: str  # e.g., "القرابة"
    field_name_en: str  # e.g., "Kinship"
    word: str  # vocalized
    plain: str  # diacritic-free
    metadata: dict  # field-specific (gender, type, etc.)


@dataclass
class SemanticFieldsIndex:
    """In-memory index for semantic-field lookup."""

    members: list[FieldMember] = field(default_factory=list)
    fields_ar: dict[str, str] = field(default_factory=dict)  # ar → en name
    _by_plain: dict[str, list[FieldMember]] = field(default_factory=dict)
    _by_norm: dict[str, list[FieldMember]] = field(default_factory=dict)
    _by_field: dict[str, list[FieldMember]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for m in self.members:
            # Primary keys: plain + word
            keys = [m.plain, m.word]
            # Also index any string metadata value (feminine forms, alternate words, etc.)
            for v in m.metadata.values():
                if isinstance(v, str) and v.strip():
                    keys.append(v)
            for key in keys:
                pkey = _strip_diacritics(key).strip()
                if pkey:
                    self._by_plain.setdefault(pkey, []).append(m)
                nkey = _normalize_lookup_key(key)
                if nkey:
                    self._by_norm.setdefault(nkey, []).append(m)
            self._by_field.setdefault(m.field_name_ar, []).append(m)
            if m.field_name_ar not in self.fields_ar:
                self.fields_ar[m.field_name_ar] = m.field_name_en

    def lookup(self, surface: str) -> list[FieldMember]:
        """Return members matching the surface (could be in multiple fields).

        Tries (in order):
          1. Exact plain (diacritics stripped only).
          2. Normalized (hamza, alif maqsurah, tanwin-alif).
          3. Normalized with each common pronoun suffix stripped.
        """
        pkey = _strip_diacritics(surface).strip()
        if pkey and pkey in self._by_plain:
            return list(self._by_plain[pkey])
        for cand in _candidates_with_suffix_strip(surface):
            if cand and cand in self._by_norm:
                return list(self._by_norm[cand])
        return []

    def fields_for(self, surface: str) -> list[str]:
        """Return Arabic field names containing this surface."""
        hits = self.lookup(surface)
        seen = []
        for h in hits:
            if h.field_name_ar not in seen:
                seen.append(h.field_name_ar)
        return seen

    def members_of(self, field_name_ar: str) -> list[FieldMember]:
        return list(self._by_field.get(field_name_ar, []))

    def all_fields(self) -> list[str]:
        return sorted(self.fields_ar.keys())

    def stats(self) -> dict[str, int]:
        return {
            "total_members": len(self.members),
            "total_fields": len(self.fields_ar),
            **{name: len(members) for name, members in self._by_field.items()},
        }


def load_semantic_fields_index(directory: Path | None = None) -> SemanticFieldsIndex:
    fields_dir = directory or DEFAULT_FIELDS_DIR
    if not fields_dir.is_dir():
        raise FileNotFoundError(f"Semantic fields directory not found: {fields_dir}")

    members: list[FieldMember] = []
    for json_path in sorted(fields_dir.glob("*.json")):
        with json_path.open(encoding="utf-8") as f:
            doc = json.load(f)
        name_ar = doc.get("field_name_ar", json_path.stem)
        name_en = doc.get("field_name_en", json_path.stem.replace("_", " ").title())
        for row in doc.get("members", []):
            word = row.get("word", "")
            plain = row.get("plain") or _strip_diacritics(word)
            # All non-word/plain fields go into metadata
            metadata = {k: v for k, v in row.items() if k not in ("word", "plain")}
            members.append(
                FieldMember(
                    field_name_ar=name_ar,
                    field_name_en=name_en,
                    word=word,
                    plain=plain,
                    metadata=metadata,
                )
            )
    return SemanticFieldsIndex(members=members)
