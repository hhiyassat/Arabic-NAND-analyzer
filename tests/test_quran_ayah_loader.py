"""Tests for Quran ayah reference parsing and lookup."""

from __future__ import annotations

import pytest

from architecture_test.quran_ayah_loader import (
    format_ayah_reference,
    get_ayah_text,
    looks_like_ayah_ref,
    parse_ayah_ref,
    resolve_ayah_input,
)


@pytest.mark.parametrize(
    "ref,expected",
    [
        ("94:6", (94, 6)),
        ("2:185", (2, 185)),
        ("Quran 2:185", (2, 185)),
        ("2-185", (2, 185)),
        ("سورة 94 آية 6", (94, 6)),
    ],
)
def test_parse_ayah_ref_valid(ref: str, expected: tuple[int, int]) -> None:
    assert parse_ayah_ref(ref) == expected
    assert looks_like_ayah_ref(ref)


@pytest.mark.parametrize(
    "ref",
    ["", "abc", "999:1", "1:9999", "إِنَّ"],
)
def test_parse_ayah_ref_invalid(ref: str) -> None:
    assert parse_ayah_ref(ref) is None
    assert not looks_like_ayah_ref(ref)


def test_get_ayah_text_2_185() -> None:
    text = get_ayah_text(2, 185)
    assert text is not None
    assert "رَمَضَانَ" in text or "رَمَضَان" in text
    assert len(text.split()) > 10


def test_resolve_ayah_input_2_185() -> None:
    text, ref, meta = resolve_ayah_input("2:185")
    assert ref == format_ayah_reference(2, 185)
    assert meta["surah"] == 2
    assert meta["ayah"] == 185
    assert "رَمَضَان" in text or "رَمَضَانَ" in text
