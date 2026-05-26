"""Tokenize input Arabic text and attach surface-level structural hints."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

_DIACRITICS = set("ًٌٍَُِّْٰٓٔ")
_TANWEEN = set("ًٌٍ")
_QURAN_WRAPPERS = "﴿﴾「」"
_ARABIC_LETTER_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
_PLACEHOLDER_LITERALS = frozenset({"...", "…", "....", "….", "..", "xxx", "xx", "x"})


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", str(text or "").strip())


def strip_diacritics(text: str) -> str:
    """Remove Arabic tashkil only; keep base letters (incl. hamza carriers)."""
    return "".join(c for c in nfc(text) if c not in _DIACRITICS)


def normalize_input_text(text: str) -> str:
    t = nfc(text)
    for ch in _QURAN_WRAPPERS:
        t = t.replace(ch, "")
    return re.sub(r"\s+", " ", t).strip()


def count_arabic_letters(text: str) -> int:
    return len(_ARABIC_LETTER_RE.findall(text))


def count_diacritic_marks(text: str) -> int:
    return sum(1 for c in nfc(text) if c in _DIACRITICS)


def has_sufficient_diacritics(text: str, *, min_ratio: float = 0.08) -> bool:
    """True when text already has enough tashkil for architecture / wazn heuristics."""
    letters = count_arabic_letters(text)
    if letters < 2:
        return False
    marks = count_diacritic_marks(text)
    return marks >= max(3, int(letters * min_ratio))


def validate_arabic_input(text: str) -> str:
    """
    Normalize and reject placeholders / non-Arabic input.
    Returns cleaned text; raises ValueError with a helpful message.
    """
    clean = normalize_input_text(text)
    if not clean:
        raise ValueError("Input text is empty.")

    if clean in _PLACEHOLDER_LITERALS or re.fullmatch(r"\.{2,}|…+", clean):
        raise ValueError(
            'Input looks like a documentation placeholder ("..."), not Arabic text.\n'
            "Example:\n"
            '  python3 run_architecture_test_sample_01.py -t "إِنَّ مَعَ الْعُسْرِ يُسْرًا" '
            '-r "Quran 94:6" -c "ayah 5 repeats" --json -o output/report.txt'
        )

    letters = count_arabic_letters(clean)
    if letters < 2:
        raise ValueError(
            f"Input has only {letters} Arabic letter(s) in {len(clean.split())} token(s). "
            "Pass real vocalized Arabic (not ASCII placeholders).\n"
            "Example: -t \"إِنَّ مَعَ الْعُسْرِ يُسْرًا\""
        )

    return clean


def infer_case(surface: str) -> str:
    """Rough case hint from final visible haraka (not i3rab authority)."""
    for ch in reversed(surface):
        if ch == "ِ":
            return "kasra"
        if ch in ("ُ", "ٌ"):
            return "rafa"
        if ch in ("َ", "ً"):
            return "nasb"
        if ch in _DIACRITICS:
            continue
        break
    return "unknown"


def infer_definiteness(plain: str, surface: str) -> str:
    s = surface.lstrip()
    if s.startswith(("ال", "ٱل")) or plain.startswith("ال"):
        return "definite"
    if any(c in surface for c in _TANWEEN):
        return "indefinite"
    return "unknown"


def looks_verbal(plain: str, surface: str) -> bool:
    """Heuristic: finite verb / verbal morphology (not authoritative)."""
    if any(c in surface for c in _TANWEEN):
        return False
    if plain.startswith(("ي", "ت", "ن", "أ")) and len(plain) >= 2:
        if any(c in surface for c in "َُِ"):
            return True
    if surface.endswith(("َ", "ْ")) and len(plain) >= 3 and not any(c in surface for c in _TANWEEN):
        if not plain.startswith("ال"):
            return True
    return False


def looks_nasikh(surface: str, huruf_category: str | None) -> bool:
    plain = strip_diacritics(nfc(surface))
    if plain in ("إن", "ان", "انن"):
        return True
    if huruf_category and any(x in huruf_category for x in ("ناسخ", "توكيد")):
        return True
    return False


def tokenize_text(text: str) -> list[dict[str, Any]]:
    normalized = normalize_input_text(text)
    if not normalized:
        return []
    tokens: list[dict[str, Any]] = []
    for i, surface in enumerate(normalized.split()):
        plain = strip_diacritics(nfc(surface))
        tokens.append(
            {
                "index": i,
                "surface": surface,
                "plain": plain,
                "plain_no_al": plain[2:] if plain.startswith("ال") else plain,
                "has_al": plain.startswith("ال"),
                "has_tanwin": any(c in surface for c in _TANWEEN),
                "case_hint": infer_case(surface),
                "definiteness": infer_definiteness(plain, surface),
                "looks_verbal": looks_verbal(plain, surface),
                "is_ma_accompaniment": plain == "مع",
                # word_class filled in by pipeline after lookups:
                # one of: harf / jamid / mushtaq / verb / unknown
                "word_class": "unknown",
            }
        )
    return tokens


def token_sequence_label(tokens: list[dict[str, Any]]) -> str:
    return " • ".join(strip_diacritics(t["surface"]) for t in tokens)
