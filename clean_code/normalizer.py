"""normalizer — THE OFFICIAL ARABIC NORMALIZER for معمار المعنى العربي.

═══════════════════════════════════════════════════════════════════════════
  CONSTITUTIONAL DECLARATION (2026-05-18)
═══════════════════════════════════════════════════════════════════════════
  This module is the project's official Arabic text normalizer.
  It supersedes the NAA standalone_segmenter normalize.py.

  Tested against: MASAQ Quranic corpus (17,619 unique words).

  Normalization scope:
    1. NFC Unicode normalization
    2. Alif madda decomposition (آ → ءَا) — preserves phonetic content
    3. Stray whitespace cleanup (trim, collapse internal)
    4. Tatweel/kashida removal (ـ)
    5. Alif wasla normalization (ٱ → ا)
    6. Dagger alif normalization (ٰ → ا) — when configured
    7. Diacritic ordering canonicalization (shadda before harakah)

  Preservation policy:
    • Hamza variants (أ/إ/ؤ/ئ/ء) preserved — they carry phonetic distinction
    • Alif maqsura (ى) preserved — different from ي in classical
    • Taa marbuta (ة) preserved — different from ه in surface
    • All diacritics preserved in canonical order

  For ROOT-MATCHING purposes, downstream consumers (wazn_matcher) apply
  hamza-folding / ى→ي / ة→ه on top of this normalized output.

  Constitutional alignment (per 12_Project_Scope_Declaration.md):
    ✓ Source-of-Claim       — every transformation logs its rule name
    ✓ Confidence-of-Claim   — N/A (deterministic, conf=1.0 always)
    ✓ Alternatives-Preserved — N/A (single canonical form, by design)
    ✓ Reversibility         — original input recoverable via diff log
═══════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Optional


# === Character constants ===
DIACRITICS = set("ًٌٍَُِّْٰٓٔ")
TATWEEL = "ـ"  # U+0640
SHADDA = "ّ"  # U+0651
SUKUN = "ْ"  # U+0652
DAGGER_ALIF = "ٰ"  # U+0670
ALIF_WASLA = "ٱ"  # U+0671
ALIF = "ا"  # U+0627
ALIF_MADDA = "آ"  # U+0622
ALIF_MAQSURA = "ى"  # U+0649
HAMZA = "ء"  # U+0621
FATHA = "َ"  # U+064E

# Non-shadda diacritics (the ones that can follow shadda)
NON_SHADDA_DIACRITICS = DIACRITICS - {SHADDA}


@dataclass
class NormalizationResult:
    """Result of normalizing a string, with audit trail."""
    original: str
    normalized: str
    transformations: tuple[str, ...] = field(default_factory=tuple)

    @property
    def changed(self) -> bool:
        return self.original != self.normalized

    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "normalized": self.normalized,
            "changed": self.changed,
            "transformations": list(self.transformations),
        }


# === Rule implementations ===
def _rule_nfc(s: str) -> tuple[str, bool]:
    """Apply Unicode NFC normalization. Returns (new, changed)."""
    new = unicodedata.normalize("NFC", s)
    return new, new != s


def _rule_trim_and_collapse_ws(s: str) -> tuple[str, bool]:
    """Strip leading/trailing whitespace and collapse internal whitespace."""
    new = " ".join(s.split())
    return new, new != s


def _rule_remove_tatweel(s: str) -> tuple[str, bool]:
    """Remove kashida (ـ)."""
    if TATWEEL not in s:
        return s, False
    return s.replace(TATWEEL, ""), True


def _rule_alif_wasla_to_alif(s: str) -> tuple[str, bool]:
    """Convert alif wasla ٱ to standard alif ا."""
    if ALIF_WASLA not in s:
        return s, False
    return s.replace(ALIF_WASLA, ALIF), True


def _rule_dagger_alif_to_alif(s: str) -> tuple[str, bool]:
    """Convert dagger alif (Quranic superscript alif) ٰ to standard alif ا.

    NOTE: this is OPTIONAL. The dagger alif marks a non-written long /a:/
    in classical orthography. Modern texts often substitute it with regular
    alif. Some workflows want to preserve it. The normalizer flag controls
    this behavior.
    """
    if DAGGER_ALIF not in s:
        return s, False
    return s.replace(DAGGER_ALIF, ALIF), True


def _rule_alif_madda_decompose(s: str) -> tuple[str, bool]:
    """Decompose alif madda آ into its phonetic components ء + ـَ + ا.

    The alif madda represents [ʔ] + long [aː] phonetically. As a single
    Unicode codepoint it bundles hamza + fatha + alif. For morphological
    analysis (especially wazn matching), this needs to be decomposed:
      آلِهَة (alif-madda + lam + ...) → ءَالِهَة → matches فَاعِلَة pattern correctly

    Without this decomposition, the analyzer sees only 3 letters when there
    are really 4 (the leading hamza is invisible inside the madda glyph).
    """
    if ALIF_MADDA not in s:
        return s, False
    out: list[str] = []
    for c in s:
        if c == ALIF_MADDA:
            out.append(HAMZA)
            out.append(FATHA)
            out.append(ALIF)
        else:
            out.append(c)
    return "".join(out), True


def _rule_hamzat_wasl(s: str) -> tuple[str, bool]:
    """Resolve hamzat wasl: bare leading ا → إ or أ based on 3rd letter's vowel.

    Classical rule:
      - If 3rd letter has damma → hamza is damma → أُ
        Example: اكْتُبْ → أُكْتُبْ (uktub)
      - Otherwise (fatha/kasra/sukun) → hamza is kasra → إِ
        Examples:
          اضْرِبْ → إِضْرِبْ (idrib)
          اسْتَخْرَجَ → إِسْتَخْرَجَ
          اعْمَلْ → إِعْمَلْ

    Skipped when:
      - Word doesn't start with bare "ا"
      - Word is too short to have a 3rd letter
      - Word starts with another hamza variant (أ، إ، آ، ٱ) — already explicit
    """
    if not s or s[0] != "ا":
        return s, False
    # Find position of 3rd "letter" (skip diacritics)
    letter_positions = []
    for i, c in enumerate(s):
        if c not in DIACRITICS and c != TATWEEL:
            letter_positions.append(i)
        if len(letter_positions) >= 3:
            break
    if len(letter_positions) < 3:
        return s, False
    # Diacritic on the 3rd letter
    third_idx = letter_positions[2]
    diac_start = third_idx + 1
    third_diacs = ""
    j = diac_start
    while j < len(s) and s[j] in DIACRITICS:
        third_diacs += s[j]
        j += 1
    DAMMA = "ُ"
    if DAMMA in third_diacs:
        return "أُ" + s[1:], True
    # default: kasra
    return "إِ" + s[1:], True


def _rule_lam_shamsi_un_assimilation(s: str) -> tuple[str, bool]:
    """Remove the assimilation shadda from the shamsi letter after ال.

    When ال (definite article) precedes a shamsi (sun) letter, the ل is
    silent and the shamsi letter gets a shadda from the assimilation.
    Examples:
      الشَّمْس  (al-shams)  ← ال + شَمْس with shadda transferred to ش
      الظِّلّ   (al-ẓill)   ← ال + ظِلّ
      التَّوَّاب (al-tawwab) ← ال + تَوَّاب

    For root-extraction purposes, we want the BASE form (without the
    assimilation shadda) so the wazn alignment can match the underlying
    pattern. Rule:
      - If text starts with "ال" (possibly with sukun on ل) and the next
        letter is shamsi WITH shadda, REMOVE that shadda.

    Shamsi letters: ت ث د ذ ر ز س ش ص ض ط ظ ل ن
    """
    SHAMSI_LETTERS = set("تثدذرزسشصضطظلن")
    # Look for "ال" at start: ا (with optional diacritics) + ل (with optional diacritics)
    if len(s) < 4:
        return s, False
    if s[0] != "ا":
        return s, False
    i = 1
    while i < len(s) and s[i] in DIACRITICS:
        i += 1
    if i >= len(s) or s[i] != "ل":
        return s, False
    i += 1
    while i < len(s) and s[i] in DIACRITICS:
        i += 1
    if i >= len(s):
        return s, False
    shamsi_pos = i
    if s[shamsi_pos] not in SHAMSI_LETTERS:
        return s, False
    # Now check if the shamsi letter has a shadda among its diacritics
    j = shamsi_pos + 1
    shadda_pos = -1
    while j < len(s) and s[j] in DIACRITICS:
        if s[j] == SHADDA:
            shadda_pos = j
            break
        j += 1
    if shadda_pos == -1:
        return s, False
    # Remove the assimilation shadda
    return s[:shadda_pos] + s[shadda_pos + 1:], True


def _rule_canonical_diacritic_order(s: str) -> tuple[str, bool]:
    """Ensure shadda precedes other diacritics on the same consonant.

    Some sources emit (letter, harakah, shadda) order while others emit
    (letter, shadda, harakah). The canonical order per Unicode TR is
    (letter, shadda, other-diacritics). We enforce this.

    Also collapses duplicate identical diacritics (rare but happens).
    """
    chars = list(s)
    n = len(chars)
    out: list[str] = []
    i = 0
    changed = False
    while i < n:
        c = chars[i]
        if c in DIACRITICS or c == TATWEEL:
            # Skip — should have been consumed by previous letter
            i += 1
            continue
        out.append(c)
        i += 1
        # Collect ALL diacritics until next consonant
        marks: list[str] = []
        while i < n and chars[i] in DIACRITICS:
            if chars[i] not in marks:  # dedupe
                marks.append(chars[i])
            else:
                changed = True
            i += 1
        if not marks:
            continue
        # Canonical order: shadda first, then other diacritics
        has_shadda = SHADDA in marks
        non_shadda = [m for m in marks if m != SHADDA]
        if has_shadda:
            if marks != [SHADDA] + non_shadda:
                changed = True
            out.append(SHADDA)
        out.extend(non_shadda)
    return "".join(out), changed


# === Pipeline ===
_PIPELINE = [
    ("nfc", _rule_nfc),
    ("trim_ws", _rule_trim_and_collapse_ws),
    ("remove_tatweel", _rule_remove_tatweel),
    ("alif_wasla", _rule_alif_wasla_to_alif),
    # Note: dagger_alif is OFF by default — many Quranic texts intentionally
    # preserve it for correct recitation. Turn on for general MSA processing.
    # ("dagger_alif", _rule_dagger_alif_to_alif),
    ("alif_madda", _rule_alif_madda_decompose),
    ("canonical_diacritics", _rule_canonical_diacritic_order),
]

# Optional rules (off by default — turn on for root-extraction pipeline)
_OPTIONAL_HAMZAT_WASL = ("hamzat_wasl", _rule_hamzat_wasl)
_OPTIONAL_LAM_SHAMSI = ("lam_shamsi", _rule_lam_shamsi_un_assimilation)


def normalize(text: str, *,
              fold_dagger_alif: bool = False,
              decompose_alif_madda: bool = True,
              resolve_hamzat_wasl: bool = False,
              un_assimilate_lam_shamsi: bool = False) -> NormalizationResult:
    """Apply the canonical normalization pipeline.

    Args:
        text: input Arabic text
        fold_dagger_alif: if True, convert ٰ → ا (default off for Quranic)
        decompose_alif_madda: if True, convert آ → ءَا (default on)
        resolve_hamzat_wasl: if True, bare leading ا → إ/أ (root-extraction).
            Default OFF — preserves surface for Quranic display.
        un_assimilate_lam_shamsi: if True, remove the assimilation shadda
            from shamsi letter after ال (e.g., الشَّمْس → الشَمْس).
            Default OFF — preserves surface.

    Returns:
        NormalizationResult with normalized text and audit trail.
    """
    if not text:
        return NormalizationResult(original=text or "", normalized="")

    out = text
    applied: list[str] = []
    for name, rule in _PIPELINE:
        if name == "alif_madda" and not decompose_alif_madda:
            continue
        new, changed = rule(out)
        if changed:
            applied.append(name)
        out = new

    if fold_dagger_alif:
        new, changed = _rule_dagger_alif_to_alif(out)
        if changed:
            applied.append("dagger_alif")
        out = new

    # Optional rules for root-extraction pipeline
    if un_assimilate_lam_shamsi:
        new, changed = _rule_lam_shamsi_un_assimilation(out)
        if changed:
            applied.append("lam_shamsi")
        out = new

    if resolve_hamzat_wasl:
        new, changed = _rule_hamzat_wasl(out)
        if changed:
            applied.append("hamzat_wasl")
        out = new

    return NormalizationResult(
        original=text,
        normalized=out,
        transformations=tuple(applied),
    )


def normalize_for_root_extraction(text: str) -> str:
    """Convenience: full pipeline + root-extraction rules turned ON.

    Use this before wazn alignment in root_by_alignment.py.
    Returns plain normalized string.
    """
    return normalize(
        text,
        decompose_alif_madda=True,
        resolve_hamzat_wasl=True,
        un_assimilate_lam_shamsi=True,
    ).normalized


def normalize_text(text: str) -> str:
    """Convenience: return only the normalized string (no audit trail)."""
    return normalize(text).normalized


# === CLI ===
def main() -> int:
    import argparse
    import json

    p = argparse.ArgumentParser(description="Arabic text normalizer")
    p.add_argument("text", help="Arabic text to normalize")
    p.add_argument("--fold-dagger-alif", action="store_true",
                   help="Convert dagger alif ٰ to ا (default off)")
    p.add_argument("--no-decompose-madda", action="store_true",
                   help="Keep آ as a single codepoint (default decomposes)")
    p.add_argument("--json", action="store_true", help="Output JSON")
    args = p.parse_args()

    result = normalize(
        args.text,
        fold_dagger_alif=args.fold_dagger_alif,
        decompose_alif_madda=not args.no_decompose_madda,
    )

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"original:   {result.original!r}")
        print(f"normalized: {result.normalized!r}")
        print(f"changed:    {result.changed}")
        print(f"rules:      {' → '.join(result.transformations) or '(none)'}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
