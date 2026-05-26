"""segmentation_certification.py — metadata layer لِشَهادَة التَّقطيع.

تَوصيَة المُستَخدِم 2026-05-26 (Step D):
  هَذا الـmodule **يُجَهِّز** البِنيَة فَقَط. لا يَفرِض حَجبًا الآن.

  enforcement لِلـrelations/events مِن fragments يُؤَجَّل إلى Step E+.

البِنيَة:
  Segment              — صَرف واحِد (prefix/stem/suffix)
  SegmentationDecision — كامِل القرار لِـtoken (مَع status + blockers)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from ..core.certainty import Certainty


@dataclass
class Segment:
    """صَرف واحِد (prefix/stem/suffix)."""
    surface: str                 # السَّطح بِالتَّشكيل
    tag: str = ""                # DET / CONJ / PREP / Stem / IMPERF_PREF / NSUFF...
    position: Literal["prefix","stem","suffix"] = "stem"
    parent_token: str = ""       # الـtoken الأَصليّ قَبل التَّقطيع
    is_fragment: bool = False    # true لَو الـsegment لَيس كَلِمَة مُستَقِلَّة


@dataclass
class SegmentationDecision:
    """قَرار التَّقطيع الكامِل لِـtoken.

    حاليًّا (Step D): يُحمَل كَ metadata. لا يَتَدَخَّل في relations/events.
    """
    surface: str
    normalized: str = ""
    segments: list[Segment] = field(default_factory=list)
    segmentation_status: Certainty = "Certificate"
    source: str = ""             # "legacy_segmenter" / "registry_locked" / etc.
    blockers: list[str] = field(default_factory=list)
    parent_token: Optional[str] = None
    is_fragment: bool = False
    confidence: float = 1.0
    # raw legacy SegmentationResult لِلتَّوافُق
    _legacy: object = None

    @classmethod
    def from_legacy_result(cls, legacy_result, *, parent_token: str | None = None,
                          status: Certainty = "Certificate"):
        """يُنشِئ SegmentationDecision مِن SegmentationResult القَديم.

        لا يُغَيِّر النَّتيجَة. مُجَرَّد wrapper.
        """
        if legacy_result is None:
            return cls(surface="", segmentation_status="Zero")

        segs: list[Segment] = []
        surf = legacy_result.original
        # prefixes
        for i, p in enumerate(legacy_result.prefixes or []):
            tag = (legacy_result.prefix_tags or [])[i] if i < len(legacy_result.prefix_tags or []) else ""
            segs.append(Segment(surface=p, tag=tag, position="prefix",
                                parent_token=surf, is_fragment=True))
        # stem
        if legacy_result.stem:
            segs.append(Segment(surface=legacy_result.stem, tag="Stem",
                                position="stem", parent_token=surf,
                                is_fragment=bool(legacy_result.prefixes or legacy_result.suffixes)))
        # suffixes
        for i, s in enumerate(legacy_result.suffixes or []):
            tag = (legacy_result.suffix_tags or [])[i] if i < len(legacy_result.suffix_tags or []) else ""
            segs.append(Segment(surface=s, tag=tag, position="suffix",
                                parent_token=surf, is_fragment=True))

        return cls(
            surface=surf,
            normalized=legacy_result.normalized,
            segments=segs,
            segmentation_status=status,
            source="legacy_segmenter",
            blockers=[],
            parent_token=parent_token,
            is_fragment=False,  # الـtoken كامِل، الـsegments داخِله fragments
            confidence=legacy_result.confidence,
            _legacy=legacy_result,
        )

    # ─────────────────────────────────────────────────────────────
    # Safe predicates (لا enforcement الآن — مُجَرَّد accessors)
    # ─────────────────────────────────────────────────────────────

    def is_certified(self) -> bool:
        return self.segmentation_status == "Certificate"

    def is_hypothesis(self) -> bool:
        return self.segmentation_status == "Hypothesis"

    def is_zero(self) -> bool:
        return self.segmentation_status == "Zero"

    def has_prefixes(self) -> bool:
        return any(s.position == "prefix" for s in self.segments)

    def has_suffixes(self) -> bool:
        return any(s.position == "suffix" for s in self.segments)

    def has_fragments(self) -> bool:
        return any(s.is_fragment for s in self.segments)

    def stem_surface(self) -> str:
        for s in self.segments:
            if s.position == "stem":
                return s.surface
        return ""

    def to_legacy_dict(self) -> dict:
        """تَحويل إِلى dict مُتَوافِق مَع SegmentationResult.to_dict()."""
        if self._legacy is not None:
            return self._legacy.to_dict()
        # ابنِ يَدَويًّا
        prefixes = [s.surface for s in self.segments if s.position == "prefix"]
        prefix_tags = [s.tag for s in self.segments if s.position == "prefix"]
        suffixes = [s.surface for s in self.segments if s.position == "suffix"]
        suffix_tags = [s.tag for s in self.segments if s.position == "suffix"]
        return {
            "original": self.surface,
            "normalized": self.normalized,
            "prefixes": prefixes,
            "prefix_tags": prefix_tags,
            "stem": self.stem_surface(),
            "suffixes": suffixes,
            "suffix_tags": suffix_tags,
            "audit": [],
            "confidence": self.confidence,
        }


def certify_segmentation(legacy_result, *, parent_token: str | None = None,
                         status: Certainty = "Certificate") -> SegmentationDecision:
    """API entry: حَوِّل legacy result إلى SegmentationDecision.

    Step D: status دائِمًا Certificate (تَحفَظ السُّلوك القَديم).
    Step E+ سَيَستَخدِم blockers/Hypothesis لِمَنع relation/event from fragments.
    """
    return SegmentationDecision.from_legacy_result(
        legacy_result, parent_token=parent_token, status=status,
    )


__all__ = [
    "Segment",
    "SegmentationDecision",
    "certify_segmentation",
]
