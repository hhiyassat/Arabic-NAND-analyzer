"""evidence.py — Evidence: قِطعَة دَليل واحِدَة تَدعَم أَو تَنفي candidate.

Evidence يَحمِل:
  • النَّوع (positive/negative/blocker)
  • القُوَّة (1-10)
  • المَصدَر (SourceRecord)
  • شَرح (reason)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from .sources import SourceRecord


@dataclass
class Evidence:
    """دَليل واحِد لِصالِح أَو ضِدّ تَصنيف.

    kind:
      positive — يَدعَم candidate
      negative — يَرفُض candidate
      blocker  — مانِع صَريح (مَثَل tanwin → لَيس فِعل)
    """
    kind: Literal["positive", "negative", "blocker"]
    reason: str
    source: SourceRecord
    strength: int = 5  # 1-10
    targets: tuple[str, ...] = ()  # candidate classes هَذا الدَّليل يُؤَثِّر فيها

    def __str__(self) -> str:
        sign = {"positive": "+", "negative": "-", "blocker": "✗"}[self.kind]
        return f"{sign}{self.strength} {self.reason} [{self.source}]"
