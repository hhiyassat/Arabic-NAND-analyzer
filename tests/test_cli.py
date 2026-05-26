"""Tests for architecture test CLI (no full pipeline run)."""

from __future__ import annotations

import pytest

from architecture_test.cli import (
    build_parser,
    has_explicit_input,
    pipeline_kwargs,
    positional_is_ayah_ref,
    resolve_ayah_reference,
    resolve_input,
    validate_args,
)


def test_build_parser_ayah_flag() -> None:
    args = build_parser().parse_args(["--ayah", "2:185"])
    assert args.ayah == "2:185"
    assert has_explicit_input(args)


def test_positional_2_185_is_ayah_ref() -> None:
    args = build_parser().parse_args(["2:185"])
    assert positional_is_ayah_ref(args)
    assert has_explicit_input(args)


def test_mutual_exclusion_ayah_and_text() -> None:
    args = build_parser().parse_args(["--ayah", "94:6", "--text", "نص"])
    with pytest.raises(ValueError, match="--ayah"):
        validate_args(args)


def test_resolve_ayah_reference_2_185() -> None:
    resolved = resolve_ayah_reference("2:185", quran_text=None)
    assert resolved.reference == "Quran 2:185"
    assert resolved.quran_ayah is not None
    assert resolved.quran_ayah["surah"] == 2
    assert len(resolved.text) > 50


def test_resolve_input_from_positional_2_185() -> None:
    args = build_parser().parse_args(["2:185"])
    resolved = resolve_input(args)
    assert resolved is not None
    assert resolved.reference == "Quran 2:185"
    assert "رَمَضَان" in resolved.text or "رَمَضَانَ" in resolved.text


def test_pipeline_kwargs_defaults() -> None:
    args = build_parser().parse_args(["--ayah", "94:6"])
    kw = pipeline_kwargs(args)
    assert kw["skip_diacritize"] is False
    assert kw["skip_analyze_word"] is False
