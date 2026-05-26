"""sources.py — تَعريف SourceRecord (تَتَبُّع مَصدَر كُلّ ادِّعاء — MC).

SourceRecord يُسَجِّل مَن قال ماذا وَلِماذا.
كُلّ Evidence/Candidate يُشير إلى SourceRecord واحِد أَو أَكثَر.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SourceRecord:
    """تَسجيل واحِد لِمَصدَر مَعرفيّ.

    الحُقول:
      source_id    — مُعَرِّف فَريد (مَثَل "MASAQ:123" أَو
                     "registry:02_mabniyat/demonstratives.json#5")
      source_type  — نَوع المَصدَر:
                     • benchmark  — MASAQ, MEEMAR (ground truth)
                     • closed_class — registry CSVs (مَبنيّات، حُروف)
                     • rule        — heuristic contract
                     • pattern     — وَزن صَرفيّ
                     • lexicon     — explicit verbs/proper nouns
      authority    — درجَة سُلطَة المَصدَر (1-10، أَعلى = أَقوى)
      ref          — مَرجِع داخِليّ (rowid, line, etc.)
      note         — تَوضيح اختياريّ
    """
    source_id: str
    source_type: str
    authority: int = 5
    ref: str = ""
    note: str = ""

    def __str__(self) -> str:
        return f"{self.source_type}:{self.source_id}"
