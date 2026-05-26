"""Load generated past-tense conjugation tables.

Source: hussein/data/extracted/verb_conjugations_past.csv
        Generated from hussein/data/audited_roots.csv by applying classical
        Arabic conjugation rules to sound triliteral verbs only.

Coverage:
  - 2,981 sound triliteral roots
  - 13 past-tense conjugations per root (38,753 total verb forms)
  - Does NOT cover: weak verbs (mu'tall), hamza-containing, geminate verbs
  - Does NOT cover: present tense (مضارع) or imperative (أمر)

Computational-level loader. Per 11_Abstraction_Levels.md: serves the
LINGUISTIC level by providing inflectional paradigms.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONJ_CSV = (
    _REPO_ROOT / "data" / "extracted" / "verb_conjugations_past.csv"
)

_DIACRITICS = set("ًٌٍَُِّْٰٓٔ")
_TATWEEL = "ـ"

# All 13 past-tense conjugation columns (Arabic person/number labels)
PAST_PERSONS = [
    "هو_3sg_m", "هي_3sg_f", "هما_3du_m", "هما_3du_f",
    "هم_3pl_m", "هن_3pl_f",
    "أنتَ_2sg_m", "أنتِ_2sg_f", "أنتما_2du",
    "أنتم_2pl_m", "أنتن_2pl_f",
    "أنا_1sg", "نحن_1pl",
]

PERSON_AR = {
    "هو_3sg_m": "هو (مفرد مذكر غائب)",
    "هي_3sg_f": "هي (مفرد مؤنث غائبة)",
    "هما_3du_m": "هما (مثنى مذكر غائب)",
    "هما_3du_f": "هما (مثنى مؤنث غائب)",
    "هم_3pl_m": "هم (جمع مذكر غائب)",
    "هن_3pl_f": "هن (جمع مؤنث غائب)",
    "أنتَ_2sg_m": "أنتَ (مفرد مذكر مخاطب)",
    "أنتِ_2sg_f": "أنتِ (مفرد مؤنث مخاطبة)",
    "أنتما_2du": "أنتما (مثنى مخاطب)",
    "أنتم_2pl_m": "أنتم (جمع مذكر مخاطب)",
    "أنتن_2pl_f": "أنتن (جمع مؤنث مخاطب)",
    "أنا_1sg": "أنا (مفرد متكلم)",
    "نحن_1pl": "نحن (جمع متكلم)",
}


def _strip_d(s: str) -> str:
    return ''.join(c for c in str(s or "") if c not in _DIACRITICS and c != _TATWEEL)


@dataclass(frozen=True)
class VerbParadigm:
    root: str
    past_3sg_m: str  # the surface form of 3sg-m (e.g., كَتَبَ)
    bab: str
    transitivity: str  # لازم / متعدي / مشترك
    masdar: str
    conjugations: dict[str, str]  # PAST_PERSONS → vocalized form

    def get(self, person: str) -> Optional[str]:
        return self.conjugations.get(person)

    def all_forms(self) -> list[str]:
        return [self.conjugations[p] for p in PAST_PERSONS if p in self.conjugations]


@dataclass
class ConjugationIndex:
    """In-memory index for verb-form lookup → paradigm + person info."""

    paradigms: list[VerbParadigm] = field(default_factory=list)
    _by_root: dict[str, VerbParadigm] = field(default_factory=dict)
    # plain_form → list of (paradigm, person_label) matches
    _by_form_plain: dict[str, list[tuple[VerbParadigm, str]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for p in self.paradigms:
            if p.root and p.root not in self._by_root:
                self._by_root[p.root] = p
            for person, form in p.conjugations.items():
                key = _strip_d(form).strip()
                if key:
                    self._by_form_plain.setdefault(key, []).append((p, person))

    def lookup_by_form(self, form: str) -> list[dict]:
        """Given a verb form (vocalized or plain), return matching paradigms + person."""
        key = _strip_d(form).strip()
        hits = self._by_form_plain.get(key, [])
        return [
            {
                "root": p.root,
                "past_3sg_m": p.past_3sg_m,
                "bab": p.bab,
                "masdar": p.masdar,
                "matched_form": p.conjugations[person],
                "person": person,
                "person_ar": PERSON_AR.get(person, person),
            }
            for p, person in hits
        ]

    def lookup_by_root(self, root: str) -> Optional[VerbParadigm]:
        return self._by_root.get(root)

    def total_paradigms(self) -> int:
        return len(self.paradigms)

    def total_forms_indexed(self) -> int:
        return sum(len(v) for v in self._by_form_plain.values())


def load_conjugation_index(path: Path | None = None) -> ConjugationIndex:
    csv_path = path or DEFAULT_CONJ_CSV
    if not csv_path.is_file():
        raise FileNotFoundError(f"Conjugation dataset not found: {csv_path}")

    import csv as _csv
    paradigms: list[VerbParadigm] = []
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = _csv.DictReader(f)
        for row in reader:
            root = (row.get("root") or "").strip()
            past_3sg_m = (row.get("past_3sg_m") or "").strip()
            if not root or not past_3sg_m:
                continue
            conjugations = {}
            for person in PAST_PERSONS:
                val = (row.get(person) or "").strip()
                if val:
                    conjugations[person] = val
            paradigms.append(
                VerbParadigm(
                    root=root,
                    past_3sg_m=past_3sg_m,
                    bab=(row.get("bab") or "").strip(),
                    transitivity=(row.get("transitivity") or "").strip(),
                    masdar=(row.get("masdar") or "").strip(),
                    conjugations=conjugations,
                )
            )
    return ConjugationIndex(paradigms=paradigms)
