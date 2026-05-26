"""decision.py — Decision object: المُخرَج المُعَيار مِن كُلّ tokenization.

تَوصيَة المُستَخدِم 2026-05-26 (Refactor Step A):
  كُلّ token classification يَجِب أَن يُرجِع Decision بِالـschema الواحِد.

  الـmethods الآمِنَة (بَدَل `word_class == "FIIL"`):
    decision.is_certified_fiil()
    decision.allows_event_emission()
    decision.allows_relation_emission()
    decision.is_ambiguous()
    decision.has_blockers()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .certainty import Certainty, is_certified, is_hypothesis, is_zero
from .evidence import Evidence
from .sources import SourceRecord


@dataclass
class Candidate:
    """مُرَشَّح صَنف واحِد مَع features."""
    word_class: str            # FIIL / ISM_MUARAB / ISM_MABNI / ISM_MAWSOOL / JAMID / HARF
    confidence: float = 1.0    # 0.0 - 1.0
    features: dict = field(default_factory=dict)
    source_ids: tuple[str, ...] = ()  # SourceRecord.source_id


@dataclass
class Decision:
    """المُخرَج المُعَيار لِكُلّ token.

    الـschema الَّذي يَتَطَلَّبه المُستَخدِم (Refactor Step 4):
      surface, normalized, class, candidates, certainty, source, source_ids,
      proof_kind, priority, needs_context, blockers, features, segmentation_status
    """
    surface: str
    normalized: str = ""
    word_class: str = "UNKNOWN"   # الـpreferred candidate
    candidates: list[str] = field(default_factory=list)  # كُلّ المُرَشَّحات
    certainty: Certainty = "Zero"
    source: str = ""               # SourceRecord str (مُجَمَّع)
    source_ids: list[str] = field(default_factory=list)
    proof_kind: str = ""           # alias لِـcertainty (legacy)
    priority: int = 0
    needs_context: bool = False
    blockers: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    features: dict = field(default_factory=lambda: {
        "root": None, "wazn": None, "tense": None, "voice": None,
        "person": None, "number": None, "gender": None, "case": None,
    })
    segmentation_status: Certainty = "Zero"
    # Compatibility: legacy fields
    masaq_tag: str = ""
    role: str = ""

    # ─────────────────────────────────────────────────────────────
    # Safe predicates (يَستَبدِل direct equality checks)
    # ─────────────────────────────────────────────────────────────

    def is_certified(self) -> bool:
        return is_certified(self.certainty)

    def is_hypothesis(self) -> bool:
        return is_hypothesis(self.certainty)

    def is_zero(self) -> bool:
        return is_zero(self.certainty)

    def is_certified_fiil(self) -> bool:
        return self.is_certified() and self.word_class == "FIIL"

    def is_certified_noun(self) -> bool:
        return (self.is_certified()
                and self.word_class in ("ISM_MUARAB","ISM_MABNI","JAMID","ISM_MAWSOOL"))

    def is_certified_harf(self) -> bool:
        return self.is_certified() and self.word_class == "HARF"

    def is_ambiguous(self) -> bool:
        """مُلتَبِس = أَكثَر مِن candidate أَو needs_context."""
        return len(self.candidates) > 1 or self.needs_context

    def has_blockers(self) -> bool:
        return bool(self.blockers)

    # ─────────────────────────────────────────────────────────────
    # Emission permissions (per user spec)
    # ─────────────────────────────────────────────────────────────

    def allows_event_emission(self) -> bool:
        """Event لا يَجوز إِصدارُه مِن:
          - fragment بِلا segmentation Certificate
          - Hypothesis مُلتَبِس
          - candidates مُتَناقِضَة
          - registry needs_context غَير مَحلول
        """
        if self.is_zero():
            return False
        if self.segmentation_status == "Zero":
            return False
        if self.is_ambiguous() and not self.is_certified():
            return False
        if self.needs_context:
            return False
        if "conflicting_candidates" in self.blockers:
            return False
        return self.is_certified_fiil()

    def allows_relation_emission(self) -> bool:
        """Relation: نَفس قُيود Event لَكِن أَخفّ — نَسمَح بِالـHypothesis
        لَو لَدَينا candidate رَئيسيّ واضِح وَ لا blockers قاطِعَة."""
        if self.is_zero():
            return False
        if self.segmentation_status == "Zero":
            return False
        if "conflicting_candidates" in self.blockers:
            return False
        return self.word_class not in ("UNKNOWN", "")

    # ─────────────────────────────────────────────────────────────
    # Legacy compatibility (لِلكود القَديم الَّذي يَتَوَقَّع dict)
    # ─────────────────────────────────────────────────────────────

    def to_legacy_dict(self) -> dict:
        """تَحويل إِلى dict تَوافُقيّ مَع الـAPI القَديم."""
        return {
            "word_class": self.word_class,
            "source": self.source,
            "verb_aspect": self.features.get("aspect") or "",
            "root": self.features.get("root") or "",
            "wazn": self.features.get("wazn") or "",
            "proof_kind": self.certainty,
            "proof_contract": self.source.split(":")[0] if self.source else "",
            "proof_blockers": self.blockers,
            "proof_alternatives": [c for c in self.candidates if c != self.word_class],
            "registry_candidates": self.candidates,
            "registry_certainty": self.certainty,
            "registry_source": self.source,
            "registry_blockers": self.blockers,
            "registry_requires_context": self.needs_context,
            "masaq_tag": self.masaq_tag,
            "role": self.role,
        }

    @classmethod
    def from_legacy_dict(cls, d: dict, surface: str = "") -> "Decision":
        """بِناء Decision مِن dict قَديم (لِلانتِقال التَّدريجيّ)."""
        cands = d.get("registry_candidates") or [d.get("word_class", "UNKNOWN")]
        cands = [c for c in cands if c and c != "UNKNOWN"]
        return cls(
            surface=surface or d.get("surface", ""),
            word_class=d.get("word_class", "UNKNOWN"),
            candidates=cands,
            certainty=d.get("proof_kind", "Zero"),
            source=d.get("source", ""),
            blockers=d.get("proof_blockers") or [],
            needs_context=d.get("registry_requires_context", False),
            features={
                "root": d.get("root") or None,
                "wazn": d.get("wazn") or None,
                "tense": None, "voice": None, "person": None,
                "number": None, "gender": None,
                "case": d.get("case") or None,
            },
            masaq_tag=d.get("masaq_tag", ""),
            role=d.get("role", ""),
        )
