"""Tests for scripts/analyze_clean_code_text.py helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_HUSSEIN = Path(__file__).resolve().parents[1]
if str(_HUSSEIN) not in sys.path:
    sys.path.insert(0, str(_HUSSEIN))

from scripts.analyze_clean_code_text import (  # noqa: E402
    analyze_token,
    build_ayah_text_from_word_rows,
    parse_ayah_ref,
    tokenize_ayah,
)
from clean_code.wazn_matcher import AnalyzerV2


def test_parse_ayah_ref() -> None:
    assert parse_ayah_ref("2:282") == (2, 282)


def test_analyze_token_katib() -> None:
    analyzer = AnalyzerV2()
    row = analyze_token("كَاتِبٌ", analyzer, max_results=2)
    assert row["wazn_stem"]
    assert row["wazn_stem"][0]["root"]


def test_tokenize_ayah() -> None:
    toks = tokenize_ayah("إِنَّ مَعَ الْعُسْرِ")
    assert len(toks) >= 3


@pytest.mark.skipif(
    not (_HUSSEIN.parent / "new_arabic_analyzer" / "data" / "MASAQ.csv").is_file(),
    reason="MASAQ.csv not available",
)
def test_masaq_2_282_reconstruct() -> None:
    import csv

    path = _HUSSEIN.parent / "new_arabic_analyzer" / "data" / "MASAQ.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    grouped: dict[tuple[int, int], list[dict]] = {}
    for row in rows:
        s, a = int(row["Sura_No"]), int(row["Verse_No"])
        if (s, a) == (2, 282):
            grouped.setdefault((s, a), []).append(row)
    text = build_ayah_text_from_word_rows(grouped[(2, 282)])
    assert text
    assert "دَيْن" in text or "دين" in text or len(text.split()) > 20
