"""resolution_schema.py — Phase E: schemas لِأَنواع التَّعيين الـ5.

Per `Distinction_Q3_Language_vs_Perception.md`:
  • Anaphora — حَلّ الضَّمائر
  • Deixis — حَلّ الإِشارَة
  • Relative — حَلّ المَوصول
  • Bridging — حَلّ الإِشارَة الضِّمنيَّة
  • Identity-through-Transformation — تَتَبُّع الكِيان عَبر التَّحَوُّل

MC-COMPLIANT: كُلّ تَعيين بِـ kind + contract + alternatives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

ResolutionKind = Literal["Certificate", "Hypothesis", "Zero"]
ResolutionType = Literal["anaphora", "deixis", "relative", "bridging", "identity_transformation", "cross_sentence_coref"]


@dataclass
class Candidate:
    """مُرَشَّح واحِد لِتَعيين."""
    entity_id: str
    entity_surface: str
    score: float
    matches_gender: bool = False
    matches_number: bool = False
    proximity: int = 0  # عَدَد الـ tokens بَين المُرَشَّح وَ المُشير
    reason: str = ""

    def __str__(self) -> str:
        flags = []
        if self.matches_gender: flags.append("G")
        if self.matches_number: flags.append("N")
        return f"{self.entity_surface}[{self.entity_id}] score={self.score:.2f} ({''.join(flags)})"


@dataclass
class Resolution:
    """تَعيين واحِد — ضَمير/إِشارَة/مَوصول → كِيان."""
    resolution_id: str
    resolution_type: ResolutionType
    referent: str               # الكَلِمَة المُشيرَة (ضَمير، إِشارَة...)
    referent_position: int
    target: Optional[str] = None    # entity_id المُختار (أَفضَل candidate)
    target_surface: str = ""
    candidates: list[Candidate] = field(default_factory=list)
    # MC
    kind: ResolutionKind = "Zero"
    contract: str = ""
    blockers: list = field(default_factory=list)

    @property
    def has_target(self) -> bool:
        return self.target is not None

    def __str__(self) -> str:
        sym = {"Certificate": "✓", "Hypothesis": "?", "Zero": "✗"}[self.kind]
        if self.has_target:
            return f"{sym} {self.resolution_type}[{self.referent}] → {self.target_surface}[{self.target}]"
        return f"{sym} {self.resolution_type}[{self.referent}] → بِلا مَرجِع"


@dataclass
class ResolutionGraph:
    """مَجموع التَّعيينات في نَصّ."""
    source_text: str
    resolutions: list[Resolution] = field(default_factory=list)
    contract: str = "ResolutionGraph:v1"

    def add(self, r: Resolution):
        self.resolutions.append(r)

    @property
    def certificates(self) -> list[Resolution]:
        return [r for r in self.resolutions if r.kind == "Certificate"]

    @property
    def hypotheses(self) -> list[Resolution]:
        return [r for r in self.resolutions if r.kind == "Hypothesis"]

    @property
    def zeros(self) -> list[Resolution]:
        return [r for r in self.resolutions if r.kind == "Zero"]

    def by_type(self, rtype: ResolutionType) -> list[Resolution]:
        return [r for r in self.resolutions if r.resolution_type == rtype]
