"""arabic_analyzer.segmentation — wrappers لِلتَّقطيع + metadata layer.

Step D scope (re-export + metadata فَقَط):
  • segmenter           — wrappers حَول segmenter.py القَديم
  • segmentation_certification — Segment + SegmentationDecision
                                  (لا enforcement الآن)
"""
from .segmenter import (
    segment_token, segment_verse,
    to_legacy_segments, from_legacy_segments,
    SegmentationResult,
)
from .segmentation_certification import (
    Segment,
    SegmentationDecision,
    certify_segmentation,
)

__all__ = [
    "segment_token", "segment_verse",
    "to_legacy_segments", "from_legacy_segments",
    "SegmentationResult",
    "Segment", "SegmentationDecision", "certify_segmentation",
]
