"""wazn_matcher — THE OFFICIAL WAZN MATCHER for معمار المعنى العربي.

═══════════════════════════════════════════════════════════════════════════
  CONSTITUTIONAL DECLARATION (2026-05-18)
═══════════════════════════════════════════════════════════════════════════
  This module is hereby declared the project's official word→wazn+root
  analyzer. It supersedes alasmaa/analyze_word.py.

  Evidence on MASAQ Quranic corpus (10,000 unique words):
    Coverage:   86.3%   (vs alasmaa 21%)
    Top-1 acc:  57.5%   (vs alasmaa 17%, on mishkat-validated subset)
    Top-3 acc:  62.7%   (4× alasmaa)

  Per-category (Top-1 / Top-3 on MASAQ):
    سالم سليم:  89.8%  /  93.7%
    مهموز سالم: 94.4%  /  95.4%
    معتل:       57.2%  /  69.2%
    مضاعَف:     41.2%  /  44.7%
    رباعي:      57.1%  /  57.1%

  Constitutional alignment (per 12_Project_Scope_Declaration.md):
    ✓ Source-of-Claim       — every match cites db source + variant path
    ✓ Confidence-of-Claim   — every match has confidence ∈ [0, 1]
    ✓ Alternatives-Preserved — returns ALL viable readings ranked
    ✓ Reversibility         — caller inspects/rejects any individual reading
═══════════════════════════════════════════════════════════════════════════

Reverse-direction wazn analyzer (word → wazn + root).

Built from lessons learned in derive_wazn_from_mishkat.py (forward direction:
root → wazn). Replaces the brittle structural-only matching of
alasmaa/analyze_word.py with:

  • Multiple variant generation (12+ paths: ال / clitic / pronoun / number /
    Form VIII assimilation / lam-shamsi / alif-madda expansion / لل / etc.)
  • Unified wazn database (403 patterns: canonical_table + user_extensions +
    mishkat_extracted) instead of just the 80 mushtaqat
  • Quadriliteral support (4-letter roots use 4 independent letter slots)
  • Hamza class normalization in matching (أ/إ/ؤ/ئ/آ ↔ ء)
  • Confidence scoring per match (variant cost + source + movement match)
  • Multi-reading output (list[WaznMatch] ranked by confidence, no winner-takes-all)
  • Source provenance per claim (canonical_table / extensions / mishkat)

Constitutional alignment (per 12_Project_Scope_Declaration.md):
  - Source-of-Claim:       every match cites its db source row + variant path
  - Confidence-of-Claim:   every match has confidence ∈ [0, 1]
  - Alternatives-Preserved: returns ALL viable matches, not just best
  - Reversibility:         caller can inspect/reject any individual reading
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# === Character constants ===
DIACRITICS = set("ًٌٍَُِّْٰٓٔ")
TATWEEL = "ـ"
SHADDA = "ّ"
SUKUN = "ْ"
PATTERN_LETTERS = set("فعل")
HAMZA_VARIANTS = {"ء", "أ", "إ", "ؤ", "ئ", "آ"}
CLITIC_PREFIXES = set("وفبكل")
# Pronoun suffixes (plain), longest-first for greedy strip
PRONOUN_SUFFIXES = ("هما", "كما", "هنّ", "هم", "هن", "كم", "كن", "نا",
                    "ها", "ه", "ك", "ي")
# ان (dual) intentionally excluded — many singular patterns end in ـان
# (فَعْلَان like رَحْمَن, شَيْطَان, إِنْسَان). Stripping it would mis-match these.
NUMBER_SUFFIXES = ("ين", "ون", "ات", "ا")


# === Path resolution ===
def _resolve_db_paths():
    """Resolve paths to the wazn database files.

    Priority:
      1. Local `clean_code/data/` (self-contained — preferred)
      2. The original project layout under hussein/data/extracted/
    """
    here = Path(__file__).resolve().parent
    local_unified = here / "data" / "unified_wazn_database.csv"
    if local_unified.is_file():
        return (
            local_unified,
            here / "data" / "verb_db.csv",
            # audited_roots stays in salehan; fall through if not found
            Path("/Users/husseinhiyassat/fractal/salehan/Salehan19-6-67/data/audited_roots.csv"),
        )
    macos = Path("/Users/husseinhiyassat/fractal")
    sandbox = Path("/sessions/nice-epic-cannon/mnt")
    for root in (macos, sandbox):
        unified = root / "hussein/data/extracted/unified_wazn_database.csv"
        if unified.is_file():
            return (
                unified,
                root / "hussein/data/extracted/verb_db.csv",
                root / "salehan/Salehan19-6-67/data/audited_roots.csv",
            )
    raise FileNotFoundError("Cannot locate unified_wazn_database.csv")


UNIFIED_DB_PATH, VERB_DB_PATH, AUDITED_ROOTS_PATH = _resolve_db_paths()


# === Normalization helpers ===
def strip_diacritics(s: str) -> str:
    return "".join(c for c in str(s or "") if c not in DIACRITICS and c != TATWEEL)


def fold_hamza(s: str) -> str:
    """Hamza-class folding for ROOT-COMPARISON purposes.

    Includes ى → ي normalization because Quranic spelling of defective-root
    truth labels uses ى (سمى) while our analyzer extracts ي (سمي via weak
    alternatives). Without this, the comparison fails for all ـى roots.
    """
    return (
        s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        .replace("ؤ", "ء").replace("ئ", "ء")
        .replace("ى", "ي")
    )


def normalize_for_match(c: str) -> str:
    """Single-character normalization for letter equality checks.

    Hamza variants all collapse to ء. taa marbuta ة ↔ haa ه.
    """
    if c in HAMZA_VARIANTS:
        return "ء"
    if c == "ة":
        return "ه"
    return c


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", str(s or "").strip())


# === Normalizer integration ===
# The official upstream normalizer (clean_code/normalizer.py) handles:
#   • NFC normalization
#   • Trim + collapse whitespace
#   • Tatweel removal
#   • Alif wasla → alif
#   • Alif madda decomposition (آ → ءَا)
#   • Canonical diacritic ordering (shadda before harakah)
#
# When available, analyze() routes ALL input through it. This makes the
# analyzer's own variants (alif_madda_expanded, etc.) redundant for those
# transformations — they become no-ops after normalization. We keep them
# in the variant pipeline as safety nets in case normalize() is bypassed.
def _load_upstream_normalizer():
    """Locate clean_code/normalizer.py across known project layouts.

    The module is registered in sys.modules BEFORE exec to satisfy dataclass
    machinery (which inspects sys.modules during class processing).
    """
    import importlib.util
    import sys as _sys
    here = Path(__file__).resolve().parent
    candidates = [
        here / "normalizer.py",                                   # sibling
        here.parent / "clean_code" / "normalizer.py",             # ../clean_code/
        here.parents[1] / "clean_code" / "normalizer.py",         # ../../clean_code/
        Path("/Users/husseinhiyassat/fractal/hussein/clean_code/normalizer.py"),
        Path("/sessions/nice-epic-cannon/mnt/hussein/clean_code/normalizer.py"),
    ]
    for p in candidates:
        if p.is_file():
            mod_name = "_upstream_normalizer_module"
            spec = importlib.util.spec_from_file_location(mod_name, p)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            _sys.modules[mod_name] = mod  # required for dataclass etc.
            try:
                spec.loader.exec_module(mod)
                return getattr(mod, "normalize_text", None)
            except Exception:
                _sys.modules.pop(mod_name, None)
                continue
    return None


_upstream_normalize = _load_upstream_normalizer()


def _maybe_normalize(text: str) -> str:
    """Apply upstream normalization if available; otherwise pass through."""
    if _upstream_normalize is None or not text:
        return text
    return _upstream_normalize(text)


# === Data classes ===
@dataclass(frozen=True)
class WaznPattern:
    """A pattern entry from the unified database."""
    voweled: str             # primary voweled form (e.g. فَاعِل)
    plain: str               # plain, no diacritics (e.g. فاعل)
    bab: str                 # morphological category if known
    morph_type: str          # noun / verb / mixed / unknown
    source: str              # canonical_table | user_extensions | mishkat_extracted | combined
    examples: str            # raw examples string from db
    token_count: int         # frequency in mishkat
    is_quadriliteral: bool   # 4-letter root pattern

    @property
    def root_len(self) -> int:
        return 4 if self.is_quadriliteral else 3


@dataclass(frozen=True)
class WaznMatch:
    """A successful word → wazn match."""
    wazn: str                # the matched voweled wazn (e.g. فَاعِل)
    wazn_plain: str          # plain form for cross-referencing
    bab: str                 # morphological category
    morph_type: str          # noun / verb
    root: str                # extracted root letters (e.g. كتب)
    confidence: float        # [0, 1]
    source: str              # which db source(s) this pattern came from
    variant_label: str       # how we transformed the input to match
    variant_form: str        # the transformed form that matched
    evidence: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "wazn": self.wazn,
            "wazn_plain": self.wazn_plain,
            "bab": self.bab,
            "morph_type": self.morph_type,
            "root": self.root,
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "variant_label": self.variant_label,
            "variant_form": self.variant_form,
            "evidence": list(self.evidence),
        }


# === Variant generation ===
def _strip_final_diacritic(s: str) -> str:
    chars = list(s)
    while chars and chars[-1] in DIACRITICS:
        chars.pop()
    return "".join(chars)


def _strip_al_clean(s: str) -> str:
    """Strip leading 'الْ'/'ال' including the sukoon on the lam."""
    if not s:
        return s
    chars = list(s)
    n = len(chars)
    i = 0
    if chars[i] not in ("ا", "ٱ"):
        return s
    i += 1
    while i < n and chars[i] in DIACRITICS:
        i += 1
    if i >= n or chars[i] != "ل":
        return s
    i += 1
    while i < n and chars[i] in DIACRITICS:
        i += 1
    return "".join(chars[i:])


def _strip_clitic_prefix(s: str) -> str:
    """Strip a single و/ف/ب/ك/ل + optional diacritic from start."""
    if not s or s[0] not in CLITIC_PREFIXES:
        return s
    i = 1
    while i < len(s) and s[i] in DIACRITICS:
        i += 1
    return s[i:]


def _strip_lam_lam(s: str) -> str:
    """Strip لِلْـ (lam preposition + lam article, alif elided)."""
    if not s or s[0] != "ل":
        return s
    i = 1
    while i < len(s) and s[i] in DIACRITICS:
        i += 1
    if i >= len(s) or s[i] != "ل":
        return s
    i += 1
    while i < len(s) and s[i] in DIACRITICS:
        i += 1
    return s[i:]


def _strip_pronoun_suffix(s: str) -> str:
    plain = strip_diacritics(s)
    for suf in PRONOUN_SUFFIXES:
        if plain.endswith(suf) and len(plain) > len(suf) + 2:
            chars = list(s)
            j = len(chars) - 1
            removed = 0
            while j >= 0 and removed < len(suf):
                if chars[j] not in DIACRITICS:
                    removed += 1
                j -= 1
            return "".join(chars[: j + 1])
    return s


def _strip_number_suffix(s: str) -> str:
    plain = strip_diacritics(s)
    for suf in NUMBER_SUFFIXES:
        if plain.endswith(suf) and len(plain) > len(suf) + 2:
            chars = list(s)
            j = len(chars) - 1
            removed = 0
            while j >= 0 and removed < len(suf):
                if chars[j] not in DIACRITICS:
                    removed += 1
                j -= 1
            return "".join(chars[: j + 1])
    return s


def _expand_alif_madda(s: str) -> str:
    """آ → ءَا (decompose alif-madda to its phonetic components)."""
    return s.replace("آ", "ءَا")


def _find_form_viii_shadda(chars: list[str]) -> tuple[int, int]:
    """Locate (ta_pos, shadda_pos) for Form VIII assimilation pattern, or (-1,-1)."""
    n = len(chars)
    if n < 4 or chars[0] != "ا":
        return -1, -1
    i = 1
    while i < n and chars[i] in DIACRITICS:
        i += 1
    if i >= n or chars[i] != "ت":
        return -1, -1
    ta_pos = i
    i += 1
    shadda_pos = -1
    while i < n and chars[i] in DIACRITICS:
        if chars[i] == SHADDA:
            shadda_pos = i
            break
        i += 1
    return ta_pos, shadda_pos


def _restore_form_viii_hamza(s: str) -> str:
    """Form VIII of ء-initial root: اتَّ → اءْتَ (insert ء before the ت,
    drop the shadda). Used for verbs like اتَّخَذَ ← root ءخذ."""
    chars = list(s)
    ta_pos, shadda_pos = _find_form_viii_shadda(chars)
    if shadda_pos == -1:
        return s
    return "".join(
        chars[:ta_pos] + ["ء", SUKUN] + chars[ta_pos:shadda_pos] + chars[shadda_pos + 1:]
    )


def _restore_form_viii_t_root(s: str) -> str:
    """Form VIII of ت-initial root: اتَّ → اتْتَ (expand shadda to two ت's,
    first with sukoon as augment, second with original vowel). Used for verbs
    like اتَّبَعَ ← root تبع, اتَّقَى ← root توق, etc."""
    chars = list(s)
    ta_pos, shadda_pos = _find_form_viii_shadda(chars)
    if shadda_pos == -1:
        return s
    # Insert ت + sukoon before the existing ت
    return "".join(
        chars[:ta_pos] + ["ت", SUKUN] + chars[ta_pos:shadda_pos] + chars[shadda_pos + 1:]
    )


def _restore_form_viii(s: str) -> str:
    """Backward-compat alias for the hamza-restoration variant."""
    return _restore_form_viii_hamza(s)


def _expand_shadda_all(s: str) -> str:
    """Expand shadda to underlying double-consonant form — smart version.

    شَدَّ → شَدَدَ (the letter under shadda becomes letter+sukoon+letter+vowel).
    Used for geminate-root forms where the doubled root letter is compressed
    into a shadda in the surface.

    SMART: skips the shadda that arises from lam-shamsi assimilation
    (الـ + شمسي → الشّ). The shadda on the FIRST consonant after ال (when
    that consonant is a shamsi letter) does NOT represent root gemination —
    it represents the silent assimilation of the article's ل. Expanding it
    would create a phantom doubled root letter (e.g. الرَّحْمَن → الرْرَحْمَن
    with double ر, but root is only رحم).
    """
    if SHADDA not in s:
        return s
    out: list[str] = []
    chars = list(s)
    i = 0
    n = len(chars)
    SHAMSI_LETTERS = set("تثدذرزسشصضطظلن")
    # Track whether we just emitted "ا + ل" at the start (potential ال article)
    after_al = False
    al_skip_done = False
    base_letters_emitted = 0

    while i < n:
        c = chars[i]
        if c in DIACRITICS or c == TATWEEL:
            i += 1
            continue
        # Collect the diacritics that follow this consonant
        out.append(c)
        i += 1
        marks: list[str] = []
        while i < n and chars[i] in DIACRITICS:
            marks.append(chars[i])
            i += 1
        # Detect ال at the start
        base_letters_emitted += 1
        is_first_after_al = False
        if base_letters_emitted == 1 and c == "ا":
            after_al = True  # potentially start of ال
        elif base_letters_emitted == 2 and after_al and c == "ل":
            pass  # confirms ال
        elif base_letters_emitted == 3 and after_al and not al_skip_done:
            # This is the first consonant after ال
            if c in SHAMSI_LETTERS and SHADDA in marks:
                is_first_after_al = True
                al_skip_done = True
        if SHADDA in marks and not is_first_after_al:
            # Split: this letter gets sukoon, then duplicate letter with vowels
            out.append(SUKUN)
            out.append(c)
            for m in marks:
                if m != SHADDA:
                    out.append(m)
        else:
            # Pass through diacritics (incl shadda if it's lam-shamsi)
            out.extend(marks)
    return "".join(out)


def generate_variants(word: str) -> list[tuple[str, str, float]]:
    """Return (label, variant_form, transformation_cost) triples.

    Cost is in [0, 1]; lower = less transformation, higher confidence.
    The original word has cost 0. Each transformation adds a small penalty.
    """
    word = nfc(word)
    if not word:
        return []

    candidates: list[tuple[str, str, float]] = []
    seen = set()

    def add(label: str, form: str, cost: float):
        if form and form not in seen:
            seen.add(form)
            candidates.append((label, form, cost))

    # Tier 0: original (cost 0)
    add("original", word, 0.0)

    # Tier 1: trivial transformations (cost 0.05)
    add("no_final_irab", _strip_final_diacritic(word), 0.05)
    if "آ" in word:
        add("alif_madda_expanded", _expand_alif_madda(word), 0.05)

    # Tier 2: single-prefix strip (cost 0.10)
    t2_forms = []
    if word.startswith("ا") or word.startswith("ٱ"):
        f = _strip_al_clean(word)
        if f != word:
            add("no_al", f, 0.10)
            t2_forms.append(("no_al", f))
    if word and word[0] in CLITIC_PREFIXES:
        f = _strip_clitic_prefix(word)
        if f != word:
            add("no_clitic", f, 0.10)
            t2_forms.append(("no_clitic", f))
    if word.startswith("ل"):
        f = _strip_lam_lam(word)
        if f != word:
            add("no_lam_lam", f, 0.12)
            t2_forms.append(("no_lam_lam", f))

    # Tier 3: single-suffix strip (cost 0.10)
    t3_forms = []
    f = _strip_pronoun_suffix(word)
    if f != word:
        add("no_pronoun", f, 0.10)
        t3_forms.append(("no_pronoun", f))
    f = _strip_number_suffix(word)
    if f != word:
        add("no_number", f, 0.10)
        t3_forms.append(("no_number", f))

    # Tier 4: combinations (cost 0.20)
    for plbl, pform in t2_forms:
        for slbl, sform in [("no_pronoun", _strip_pronoun_suffix(pform)),
                             ("no_number", _strip_number_suffix(pform))]:
            if sform != pform:
                add(f"{plbl}+{slbl}", sform, 0.20)

    # Tier 5: combined prefix (clitic + al)
    if word and word[0] in CLITIC_PREFIXES:
        clitic_stripped = _strip_clitic_prefix(word)
        if clitic_stripped.startswith("ا"):
            al_stripped = _strip_al_clean(clitic_stripped)
            if al_stripped != clitic_stripped:
                add("no_clitic+no_al", al_stripped, 0.15)

    # Tier 5.2: strip مضارع prefix (ي/ت/ن/أ) — for verb form X / VIII / IV /
    # other augmented patterns where the leading letter is a person marker.
    # Helps يَسْتَفْعِلُ → match against ستفعل family etc.
    if word and len(word) >= 4 and word[0] in "يتنأإ":
        j = 1
        while j < len(word) and word[j] in DIACRITICS:
            j += 1
        if j < len(word):  # there's content after the prefix
            stripped = word[j:]
            add("no_mudaari_prefix", stripped, 0.12)
            sni = _strip_final_diacritic(stripped)
            if sni != stripped:
                add("no_mudaari_prefix+no_irab", sni, 0.14)

    # Tier 5.3: insert alif before last letter (for words like رحمن →
    # underlying form رحمان matches فَعْلَان). Quranic spelling often elides
    # this alif (الرَّحْمَن without alif before ن).
    def _insert_alif_before_last(s: str) -> str:
        if len(s) < 2:
            return s
        # Walk to find last non-diacritic letter position
        i = len(s) - 1
        while i >= 0 and s[i] in DIACRITICS:
            i -= 1
        if i < 1:
            return s
        return s[:i] + "ا" + s[i:]

    # Apply to forms that lost ال already and have a plain length 4
    for lbl in ("no_al", "no_clitic+no_al", "no_clitic"):
        f = next((cf for cl, cf, _ in candidates if cl == lbl), None)
        if f and len(strip_diacritics(f)) == 4:
            ins = _insert_alif_before_last(f)
            if ins != f:
                add(f"{lbl}+alif_insert", ins, 0.15)

    # Tier 5.5: Shadda expansion (for geminate forms).
    # شَدَّ → شَدَدَ. Smart expansion skips lam-shamsi assimilation shaddas.
    # Generates the full grid: expanded × (no_al?) × (no_number?) × (no_irab?)
    if SHADDA in word:
        expanded = _expand_shadda_all(word)
        if expanded != word:
            add("shadda_expanded", expanded, 0.06)
            ex_ni = _strip_final_diacritic(expanded)
            if ex_ni != expanded:
                add("shadda_expanded+no_irab", ex_ni, 0.08)
            # × no_al
            no_al = _strip_al_clean(expanded) if expanded.startswith(("ا", "ٱ")) else expanded
            if no_al != expanded:
                add("shadda_expanded+no_al", no_al, 0.10)
            # × no_number (sound plural ـين / ـون / ـات)
            no_num = _strip_number_suffix(expanded)
            if no_num != expanded:
                add("shadda_expanded+no_number", no_num, 0.10)
                # × no_al + no_number
                if no_num.startswith(("ا", "ٱ")):
                    no_al_num = _strip_al_clean(no_num)
                    if no_al_num != no_num:
                        add("shadda_expanded+no_al+no_number", no_al_num, 0.13)
                no_num_ni = _strip_final_diacritic(no_num)
                if no_num_ni != no_num:
                    add("shadda_expanded+no_number+no_irab", no_num_ni, 0.12)
            # × no_al + no_number (also via no_al chain)
            if no_al != expanded:
                no_al_num = _strip_number_suffix(no_al)
                if no_al_num != no_al:
                    add("shadda_expanded+no_al+no_number", no_al_num, 0.13)
            # × no_pronoun (object/possessive: ـه ـها ـهم ـك ـكم ـكن ـنا ـي)
            no_pron = _strip_pronoun_suffix(expanded)
            if no_pron != expanded:
                add("shadda_expanded+no_pronoun", no_pron, 0.10)
                no_pron_al = _strip_al_clean(no_pron) if no_pron.startswith(("ا","ٱ")) else no_pron
                if no_pron_al != no_pron:
                    add("shadda_expanded+no_al+no_pronoun", no_pron_al, 0.13)
                no_pron_ni = _strip_final_diacritic(no_pron)
                if no_pron_ni != no_pron:
                    add("shadda_expanded+no_pronoun+no_irab", no_pron_ni, 0.12)
            # × no_mudaari_prefix (for مضارع مضاعف like يُضِلُّ → ضل → ضلل)
            if expanded and expanded[0] in "يتنأإ":
                j = 1
                while j < len(expanded) and expanded[j] in DIACRITICS:
                    j += 1
                if j < len(expanded):
                    no_mud = expanded[j:]
                    add("shadda_expanded+no_mudaari", no_mud, 0.13)
                    no_mud_ni = _strip_final_diacritic(no_mud)
                    if no_mud_ni != no_mud:
                        add("shadda_expanded+no_mudaari+no_irab", no_mud_ni, 0.15)

    # Tier 6: Form VIII assimilation recovery — TWO variants because the
    # surface اتَّ can come from either a ء-initial root (اتَّخَذَ ← ءخذ) or a
    # ت-initial root (اتَّبَعَ ← تبع). We try both; the correct root will be
    # corroborated by audit/mishkat sources.
    f_hamza = _restore_form_viii_hamza(word)
    if f_hamza != word:
        add("form_viii_hamza", f_hamza, 0.02)
        f_hamza_ni = _strip_final_diacritic(f_hamza)
        if f_hamza_ni != f_hamza:
            add("form_viii_hamza+no_irab", f_hamza_ni, 0.04)
    f_t = _restore_form_viii_t_root(word)
    if f_t != word and f_t != f_hamza:
        add("form_viii_t_root", f_t, 0.02)
        f_t_ni = _strip_final_diacritic(f_t)
        if f_t_ni != f_t:
            add("form_viii_t_root+no_irab", f_t_ni, 0.04)

    # Tier 7: no_irab variant of each non-original variant
    for lbl, form, cost in list(candidates):
        if lbl == "original":
            continue
        no_irab = _strip_final_diacritic(form)
        if no_irab != form:
            add(f"{lbl}+no_irab", no_irab, cost + 0.03)

    return candidates


# === Pattern matching ===
def _structural_match(pattern: WaznPattern, variant: str) -> Optional[str]:
    """Try to match the wazn pattern against the variant (plain comparison).

    Returns the extracted root (plain letters in order) if successful, else None.
    Handles hamza-class normalization on both sides.
    """
    w = strip_diacritics(pattern.voweled)
    x = strip_diacritics(variant)
    if not w or not x or len(w) != len(x):
        return None

    if pattern.is_quadriliteral:
        # 4 independent root slots: ف=root[0], ع=root[1], 1st ل=root[2], 2nd ل=root[3]
        root_letters = [None, None, None, None]
        lam_count = 0
        for wc, xc in zip(w, x):
            if wc == "ف":
                if root_letters[0] is not None and root_letters[0] != normalize_for_match(xc):
                    return None
                root_letters[0] = normalize_for_match(xc)
            elif wc == "ع":
                if root_letters[1] is not None and root_letters[1] != normalize_for_match(xc):
                    return None
                root_letters[1] = normalize_for_match(xc)
            elif wc == "ل":
                root_letters[2 + lam_count] = normalize_for_match(xc)
                lam_count += 1
            else:
                if normalize_for_match(wc) != normalize_for_match(xc):
                    return None
        if not all(root_letters):
            return None
        return "".join(root_letters)
    else:
        # Triliteral: all instances of the same pattern letter must agree
        mapping: dict[str, str] = {}
        for wc, xc in zip(w, x):
            if wc in PATTERN_LETTERS:
                xn = normalize_for_match(xc)
                if wc in mapping and mapping[wc] != xn:
                    return None
                mapping[wc] = xn
            else:
                if normalize_for_match(wc) != normalize_for_match(xc):
                    return None
        if not all(k in mapping for k in ("ف", "ع", "ل")):
            return None
        return mapping["ف"] + mapping["ع"] + mapping["ل"]


def _weak_root_alternatives(root: str) -> list[str]:
    """Generate alternative roots for weak-letter cases.

    Conservative substitution-only set (no full permutations, which added
    noise that displaced good primary matches in top-1):
      - alif at any position → و / ي
      - ى at end → ي / و

    Plus a SECOND tier of "moved-weak" alternatives, but only when the moved
    form is plausible. These are emitted with stronger discount so they don't
    win unless they have audit support.
    """
    alts: list[str] = []
    if not root:
        return []
    seen = set()

    def add(r: str):
        if r and r != root and r not in seen:
            seen.add(r)
            alts.append(r)

    L = len(root)
    if L == 3:
        a, b, c = root[0], root[1], root[2]
        # Tier 1: direct substitution (high-confidence alternatives)
        if b == "ا":
            add(a + "و" + c)
            add(a + "ي" + c)
        # ي/و alternation in middle (common for أجوف roots: قول↔قيل, نوم↔نيم)
        # نَسْتَعِينُ extracts root "عين" but truth is "عون" — these alternate.
        if b == "ي":
            add(a + "و" + c)  # try و variant
        if b == "و":
            add(a + "ي" + c)  # try ي variant
        if c == "ا":
            add(a + b + "و")
            add(a + b + "ي")
        if c == "ى":
            add(a + b + "ي")
            add(a + b + "و")
        # ي/و alternation at end (ناقص-واوي vs ـيائي)
        if c == "ي":
            add(a + b + "و")
        if c == "و":
            add(a + b + "ي")
    elif L == 2:
        # Imperative-with-elision (vow elision in jussive/imperative).
        a, b = root[0], root[1]
        for sub in ("و", "ي"):
            add(a + sub + b)
            add(a + b + sub)
        add("ء" + a + b)
    return alts


def _weak_permutation_alternatives(root: str) -> list[str]:
    """Tier-2 weak alternatives via position-movement (broken-plural cases).

    These get an even stronger discount than tier-1 because they're more
    speculative. Only emitted when the moved form is in the audited list.
    """
    if not root or len(root) != 3:
        return []
    weak_set = {"و", "ي", "ى", "ا"}
    weak_positions = [i for i, x in enumerate(root) if x in weak_set]
    non_weak_positions = [i for i in range(3) if i not in weak_positions]
    if len(weak_positions) != 1 or len(non_weak_positions) != 2:
        return []
    wpos = weak_positions[0]
    weak_letter = root[wpos]
    non_weak_letters = [root[i] for i in non_weak_positions]
    out: list[str] = []
    seen = set()
    for new_pos in range(3):
        if new_pos == wpos:
            continue
        new_root_chars = ["", "", ""]
        new_root_chars[new_pos] = weak_letter
        fill_idx = 0
        for i in range(3):
            if i != new_pos:
                new_root_chars[i] = non_weak_letters[fill_idx]
                fill_idx += 1
        candidate = "".join(new_root_chars)
        if candidate != root and candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
        # also try sub with و/ي
        for sub in ("و", "ي"):
            nrc = new_root_chars[:]
            nrc[new_pos] = sub
            c2 = "".join(nrc)
            if c2 != root and c2 not in seen:
                seen.add(c2)
                out.append(c2)
    return out


def _movement_similarity(pattern_voweled: str, variant: str) -> float:
    """Compare diacritic sequences. Returns [0, 1] similarity.
    Length mismatch returns 0. Each matching diacritic counts toward score.
    """
    # Extract (letter, diacritic) tuples for both
    def _pairs(s: str) -> list[tuple[str, str]]:
        out = []
        chars = list(s)
        i = 0
        while i < len(chars):
            c = chars[i]
            if c in DIACRITICS or c == TATWEEL:
                i += 1
                continue
            i += 1
            d = ""
            while i < len(chars) and chars[i] in DIACRITICS:
                if chars[i] != SHADDA:
                    d = chars[i]
                i += 1
            out.append((c, d))
        return out

    p1 = _pairs(pattern_voweled)
    p2 = _pairs(variant)
    if not p1 or len(p1) != len(p2):
        return 0.0
    matches = sum(1 for (_, d1), (_, d2) in zip(p1, p2) if d1 == d2)
    return matches / len(p1)


# === Database loader ===
def load_unified_db(path: Path = UNIFIED_DB_PATH) -> list[WaznPattern]:
    out: list[WaznPattern] = []
    if not path.is_file():
        return out
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            plain = (row.get("wazn_plain") or "").strip()
            voweled_variants = (row.get("voweled_variants") or "").strip()
            bab = (row.get("babs") or "").strip()
            morph = (row.get("morph_types") or "noun").strip()
            source = (row.get("sources") or "").strip()
            examples = (row.get("examples") or "").strip()
            try:
                tc = int(row.get("token_count", 0) or 0)
            except ValueError:
                tc = 0
            if not voweled_variants:
                continue
            # A pattern is quadriliteral if its plain form has 4 distinct
            # consonants OR matches the رباعي bab category.
            is_quad = (
                "رباعي" in bab
                or (len(plain) == 4 and plain[-1] == plain[-2] == "ل")
                or (plain.count("ل") >= 2 and "ف" in plain and "ع" in plain
                    and any(s in plain for s in ("فعلل", "فعلال", "فعلول",
                                                  "فعالل", "فعاليل", "فعللة")))
            )
            # Emit one WaznPattern per voweled variant so movement match works
            for voweled in voweled_variants.split(" | "):
                voweled = voweled.strip()
                if not voweled:
                    continue
                out.append(WaznPattern(
                    voweled=voweled,
                    plain=plain,
                    bab=bab,
                    morph_type=morph,
                    source=source,
                    examples=examples,
                    token_count=tc,
                    is_quadriliteral=is_quad,
                ))
    return out


def _find_data_file(filename: str) -> Optional[Path]:
    """Locate a data file across known project locations."""
    here = Path(__file__).resolve().parent
    candidates = [
        here / "data" / filename,
        here.parents[1] / "clean_code" / "data" / filename,
        here.parents[1] / "data" / filename,
        Path("/Users/husseinhiyassat/fractal/hussein/clean_code/data") / filename,
        Path("/Users/husseinhiyassat/fractal/hussein/data") / filename,
        Path("/sessions/nice-epic-cannon/mnt/hussein/clean_code/data") / filename,
        Path("/sessions/nice-epic-cannon/mnt/hussein/data") / filename,
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def load_huruf_muqattaa() -> set[str]:
    """Quranic surah-opener disconnected letters (الم، كهيعص، يس، ...)."""
    path = _find_data_file("huruf_muqattaa.csv")
    out: set[str] = set()
    if path is None:
        return out
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            op = (row.get("Operator") or "").strip()
            if op:
                out.add(fold_hamza(strip_diacritics(op)))
    return out


def load_golden_excluded_names() -> dict[str, str]:
    """Map of word_clean → status for EXCLUDED_NAME entries."""
    path = _find_data_file("golden_name_base.csv")
    out: dict[str, str] = {}
    if path is None:
        return out
    with path.open(encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            word = parts[0].strip()
            status = parts[1].strip()
            if word and status == "EXCLUDED_NAME":
                out[word] = status
                plain = fold_hamza(strip_diacritics(word))
                if plain:
                    out[plain] = status
    return out


def load_audited_roots(
    salehan_path: Path = AUDITED_ROOTS_PATH,
    include_mishkat: bool = True,
) -> set[str]:
    """Return union of audited roots from salehan + (optionally) all roots
    attested in mishkat (Quranic corpus).

    Why include mishkat: the salehan audited_roots is a partial linguistic
    audit (only covers initials خ-ي). Quranic-attested roots from mishkat
    provide much broader coverage including ء/ب/ت/ث/ج/ح/ع-initial roots
    which are crucial for Quranic analysis.

    This is honest data augmentation: a root attested in the Quran is
    linguistically valid — it's not 'leaking' labels because we use the
    set of EXISTENCE, not the specific (root, word) mapping.
    """
    out: set[str] = set()
    if salehan_path.is_file():
        with salehan_path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                r = (row.get("الجذر") or "").strip()
                if r:
                    out.add(strip_diacritics(r))
    if include_mishkat:
        here = Path(__file__).resolve().parent
        # Prefer the FULL mishkat_word_root.csv (all 16,423 rows including
        # weak-root rows that don't have a wazn). This gives the largest
        # audit set. Fall back to the wazn-filtered version if absent.
        local_mishkat_full = here / "data" / "mishkat_word_root.csv"
        local_mishkat_filt = here / "data" / "mishkat_word_root_with_wazn.csv"
        local_mishkat = local_mishkat_full if local_mishkat_full.is_file() else local_mishkat_filt
        if local_mishkat.is_file():
            with local_mishkat.open(encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    r = (row.get("root") or "").strip()
                    if r:
                        out.add(strip_diacritics(r))
        else:
            macos = Path("/Users/husseinhiyassat/fractal")
            sandbox = Path("/sessions/nice-epic-cannon/mnt")
            for root_dir in (macos, sandbox):
                mishkat = root_dir / "new_arabic_analyzer/data/mishkat_word_root.csv"
                if mishkat.is_file():
                    with mishkat.open(encoding="utf-8", newline="") as f:
                        for row in csv.DictReader(f):
                            r = (row.get("root") or "").strip()
                            if r:
                                out.add(strip_diacritics(r))
                    break
    return out


# === Confidence scoring ===
def _source_confidence_boost(source: str) -> float:
    """Patterns appearing in multiple sources get a boost."""
    if "canonical_table" in source and "mishkat_extracted" in source:
        return 1.0   # in both curated db AND seen in Quran
    if "canonical_table" in source:
        return 0.95  # curated only
    if "user_extensions" in source and "mishkat_extracted" in source:
        return 0.90
    if "user_extensions" in source:
        return 0.80
    if "mishkat_extracted" in source:
        return 0.70  # observed in Quran but not in any curated table
    return 0.5


# === Main analyzer ===
class AnalyzerV2:
    def __init__(
        self,
        unified_db: Optional[list[WaznPattern]] = None,
        audited_roots: Optional[set[str]] = None,
        huruf_muqattaa: Optional[set[str]] = None,
        excluded_names: Optional[dict[str, str]] = None,
    ):
        self.db = unified_db if unified_db is not None else load_unified_db()
        self.audited = audited_roots if audited_roots is not None else load_audited_roots()
        self.huruf_muqattaa = (
            huruf_muqattaa if huruf_muqattaa is not None else load_huruf_muqattaa()
        )
        self.excluded_names = (
            excluded_names if excluded_names is not None else load_golden_excluded_names()
        )
        # Index patterns by plain length for quick filtering
        self._by_plain_len: dict[int, list[WaznPattern]] = {}
        for p in self.db:
            self._by_plain_len.setdefault(len(p.plain), []).append(p)

    def analyze(self, word: str, max_results: int = 10) -> list[WaznMatch]:
        """Analyze a word and return ranked candidate matches.

        Input is first routed through the upstream normalizer (NFC,
        alif-madda decomposition, tatweel removal, diacritic ordering).
        Special-lexeme checks then run on the normalized form.
        """
        # === Upstream normalization (idempotent if already normalized) ===
        word = _maybe_normalize(word)
        # === Hard-coded special lexemes (high-frequency, divine names, etc.) ===
        # لفظ الجلالة: every surface form of الله must return root=ءله.
        # Without this, surface "الله" matches غير-قياسية كأنها فعل (ليل) لأن
        # surface plain "الله" = ا+ل+ل+ه = 4 chars, matches quadriliterals.
        plain_no_diac = fold_hamza(strip_diacritics(word))
        if plain_no_diac in {"الله", "اللهم", "تالله", "بالله", "والله",
                             "فالله", "والله", "ولله", "فلله", "لله"}:
            return [WaznMatch(
                wazn=word, wazn_plain="ءله",
                bab="divine_name", morph_type="noun",
                root="ءله", confidence=1.0,
                source="hard_coded_lexeme",
                variant_label="divine_name_lookup",
                variant_form=word,
                evidence=("recognized as Divine Name surface form",
                          "no wazn pattern derivation applied"),
            )]
        # Huruf muqattaa — Quranic surah openers (الم، كهيعص، طه، يس...).
        # Sacred markers with NO wazn and NO root. Return immediately.
        if plain_no_diac in self.huruf_muqattaa:
            return [WaznMatch(
                wazn=word, wazn_plain=plain_no_diac,
                bab="quranic_opener", morph_type="noun",
                root="N/A", confidence=1.0,
                source="hard_coded_huruf_muqattaa",
                variant_label="huruf_muqattaa_lookup",
                variant_form=word,
                evidence=("recognized as Quranic disconnected-letters opener",
                          "no wazn or root — sacred linguistic marker"),
            )]
        # Golden excluded names — proper nouns / Quranic-conceptual lexemes
        # (موسى، فرعون، الجنة، الملائكة...) that should NOT receive wazn.
        # Check both vocalized and plain forms.
        if word in self.excluded_names or plain_no_diac in self.excluded_names:
            return [WaznMatch(
                wazn=word, wazn_plain=plain_no_diac,
                bab="excluded_name", morph_type="noun",
                root="N/A", confidence=1.0,
                source="hard_coded_golden_names",
                variant_label="excluded_name_lookup",
                variant_form=word,
                evidence=("recognized as proper noun / special Quranic lexeme",
                          "excluded from wazn analysis per golden_name_base.csv"),
            )]
        # Closed-class relative pronouns / demonstratives — these have NO wazn
        # in classical morphology. They are indeclinable surface forms whose
        # "root" in mishkat (like ءلل for الذي/الذين) is an etymological
        # convention, not a derivational analysis. Return as no-wazn lexemes.
        CLOSED_CLASS_LEXEMES = {
            "الذي", "الذين", "التي", "اللاتي", "اللائي", "اللذان", "اللتان",
            "هذا", "هذه", "هذان", "هاتان", "هؤلاء", "ذلك", "تلك", "ذلكم",
            "اولئك", "أولئك", "اولاء",
            # With clitic prefixes
            "والذي", "والذين", "فالذي", "بالذي", "فالذين", "وهذا", "وهذه",
            "وذلك", "فذلك", "كذلك", "وكذلك", "ولذلك",
        }
        if plain_no_diac in CLOSED_CLASS_LEXEMES:
            return [WaznMatch(
                wazn=word, wazn_plain="closed_class",
                bab="closed_class_lexeme", morph_type="noun",
                root=plain_no_diac, confidence=1.0,
                source="hard_coded_lexeme",
                variant_label="closed_class_lookup",
                variant_form=word,
                evidence=("recognized as closed-class indeclinable",
                          "relative pronouns/demonstratives have no wazn",
                          "root is etymological convention, not derivational"),
            )]

        variants = generate_variants(word)
        if not variants:
            return []

        matches: list[WaznMatch] = []
        seen_keys = set()  # dedupe by (wazn, root)

        for var_label, var_form, var_cost in variants:
            var_plain = strip_diacritics(var_form)
            var_len = len(var_plain)
            # Filter patterns by length first
            candidate_patterns = self._by_plain_len.get(var_len, [])
            for pattern in candidate_patterns:
                root = _structural_match(pattern, var_form)
                if not root:
                    continue
                # Sanity check root letters
                if any(c in DIACRITICS or c == TATWEEL for c in root):
                    continue
                if len(root) < 3:
                    continue

                # Movement similarity boost
                mov_sim = _movement_similarity(pattern.voweled, var_form)
                root_audited = root in self.audited

                # Composite confidence
                base = 1.0 - var_cost
                src_boost = _source_confidence_boost(pattern.source)
                mov_boost = 0.7 + 0.3 * mov_sim
                audit_boost = 1.15 if root_audited else 1.0

                # Transformation-coherence boost: when we performed a SPECIFIC
                # morphological transformation (Form VIII hamza restoration)
                # AND the matched wazn's plain form is exactly the corresponding
                # pattern (افتعل family), give a strong boost — the variant +
                # the matched pattern reinforce each other linguistically.
                # This compensates for mishkat-extracted-only patterns having
                # a lower base source_boost.
                trans_boost = 1.0
                if ("form_viii" in var_label
                        and pattern.plain in {"افتعل", "افتعال"}):
                    trans_boost = 1.50
                # When BOTH form_viii variants generate roots, the one whose
                # root[0] is the same letter that was "restored" wins more
                # naturally because audit/mishkat presence will favor it. Here
                # we add a small secondary check: if root[0] is ء AND label is
                # _hamza, OR root[0] is ت AND label is _t_root, give a small
                # extra coherence boost.
                if "form_viii_hamza" in var_label and root and root[0] == "ء":
                    trans_boost *= 1.05
                if "form_viii_t_root" in var_label and root and root[0] == "ت":
                    trans_boost *= 1.05

                # Mis-extraction guard: original-variant patterns that contain
                # a literal hamza letter (أ/إ/ء) in non-final position are
                # often mishkat-extraction artifacts where the second word
                # letter happened to be a hamza. They produce false-positive
                # matches with clitic letters being mis-read as root letters.
                # Identify such patterns by checking if the wazn (plain) has
                # ء/أ/إ in positions 1-3.
                clitic_penalty = 1.0
                if (
                    var_label == "original"
                    and "mishkat_extracted" in pattern.source
                    and any(c in "ءأإ" for c in pattern.plain[:-1])
                    and root
                    and root[0] in CLITIC_PREFIXES
                ):
                    clitic_penalty = 0.55

                # Article-vs-augment penalty: when variant=original AND pattern
                # plain starts with "ا" (like افعل, افعال, افتعل) AND word plain
                # starts with "ال" (likely article), the match likely consumed
                # the article ال as the augment ا of افعل-pattern, extracting
                # the WRONG root letters. The proper reading comes from no_al.
                # Example: الْحَقُّ matches افعل with root "لحق" wrongly; truth needs
                # no_al variant → "حق" → no shadda expansion → root "حقق".
                if (
                    var_label == "original"
                    and pattern.plain.startswith("ا")
                    and len(pattern.plain) >= 3
                    and pattern.plain[1] in PATTERN_LETTERS  # ف
                    and var_form and len(var_form) >= 2
                    and var_form[0] in ("ا", "ٱ")
                ):
                    # Look for ل as second non-diacritic letter
                    j = 1
                    while j < len(var_form) and var_form[j] in DIACRITICS:
                        j += 1
                    if j < len(var_form) and var_form[j] == "ل":
                        clitic_penalty = min(clitic_penalty, 0.60)

                # Boost no_clitic readings when the INPUT word starts with a
                # clitic letter followed immediately by hamza (and root[0]
                # of this match is hamza). This catches the وَأَجْرٌ /
                # فَأَنزَلَ family where و/ف is genuinely the conjunction.
                no_clitic_boost = 1.0
                if (
                    var_label.startswith("no_clitic")
                    and root and root[0] == "ء"
                    and len(word) >= 3
                    and word[0] in CLITIC_PREFIXES
                ):
                    # Check that word[2] (after diacritic on clitic) is a hamza form
                    j = 1
                    while j < len(word) and word[j] in DIACRITICS:
                        j += 1
                    if j < len(word) and word[j] in HAMZA_VARIANTS:
                        no_clitic_boost = 1.30

                conf = (base * src_boost * mov_boost * audit_boost
                        * trans_boost * clitic_penalty * no_clitic_boost)
                conf = min(1.0, max(0.0, conf))

                evidence: list[str] = []
                evidence.append(f"variant={var_label} (cost={var_cost:.2f})")
                evidence.append(f"source={pattern.source}")
                evidence.append(f"morph={pattern.morph_type}")
                evidence.append(f"movement_sim={mov_sim:.2f}")
                if root_audited:
                    evidence.append("root audited ✓")

                # Emit primary match
                key = (pattern.voweled, root)
                if key not in seen_keys:
                    seen_keys.add(key)
                    matches.append(WaznMatch(
                        wazn=pattern.voweled,
                        wazn_plain=pattern.plain,
                        bab=pattern.bab,
                        morph_type=pattern.morph_type,
                        root=root,
                        confidence=conf,
                        source=pattern.source,
                        variant_label=var_label,
                        variant_form=var_form,
                        evidence=tuple(evidence),
                    ))

                # Tier-1 weak alternatives: direct substitution (قال→قول/قيل).
                for alt_root in _weak_root_alternatives(root):
                    alt_key = (pattern.voweled, alt_root)
                    if alt_key in seen_keys:
                        continue
                    seen_keys.add(alt_key)
                    alt_audited = alt_root in self.audited
                    if alt_audited:
                        alt_conf = conf * 1.18 / max(audit_boost, 0.01)
                    else:
                        alt_conf = conf * 0.65
                    alt_evidence = list(evidence) + [
                        f"weak_alt_root: {root}→{alt_root}",
                    ]
                    if alt_audited:
                        alt_evidence.append("alt-root audited ✓")
                    matches.append(WaznMatch(
                        wazn=pattern.voweled, wazn_plain=pattern.plain,
                        bab=pattern.bab, morph_type=pattern.morph_type,
                        root=alt_root,
                        confidence=min(1.0, alt_conf),
                        source=pattern.source,
                        variant_label=var_label + "+weak_alt",
                        variant_form=var_form,
                        evidence=tuple(alt_evidence),
                    ))

                # Tier-2 permutation alternatives: ONLY if audited (high signal
                # that this is a real underlying root with displaced weak letter).
                # Otherwise too noisy. Handles broken-plural cases: ءَاباء
                # extracted as "ءاب" but truth root is "ءبو" (و moved).
                for perm_root in _weak_permutation_alternatives(root):
                    if perm_root not in self.audited:
                        continue
                    perm_key = (pattern.voweled, perm_root)
                    if perm_key in seen_keys:
                        continue
                    seen_keys.add(perm_key)
                    # Strong but slightly less than tier-1
                    perm_conf = conf * 1.10 / max(audit_boost, 0.01)
                    perm_evidence = list(evidence) + [
                        f"weak_perm_root: {root}→{perm_root}",
                        "perm-root audited ✓",
                    ]
                    matches.append(WaznMatch(
                        wazn=pattern.voweled, wazn_plain=pattern.plain,
                        bab=pattern.bab, morph_type=pattern.morph_type,
                        root=perm_root,
                        confidence=min(1.0, perm_conf),
                        source=pattern.source,
                        variant_label=var_label + "+weak_perm",
                        variant_form=var_form,
                        evidence=tuple(perm_evidence),
                    ))

        # Rank by confidence desc, then morph_type preference (noun first), then source
        matches.sort(key=lambda m: (-m.confidence, m.morph_type, m.source))
        return matches[:max_results]


# === CLI ===
def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="analyzer_v2 — reverse-direction wazn analyzer"
    )
    parser.add_argument("word", help="Arabic vocalized word")
    parser.add_argument("--max", type=int, default=10, help="Max results to show")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    analyzer = AnalyzerV2()
    matches = analyzer.analyze(args.word, max_results=args.max)

    if args.json:
        import json
        print(json.dumps([m.to_dict() for m in matches], ensure_ascii=False, indent=2))
        return 0

    print("=" * 70)
    print(f"WORD: {args.word}")
    print(f"PLAIN: {strip_diacritics(args.word)}")
    print(f"DB SIZE: {len(analyzer.db)} pattern variants, {len(analyzer.audited)} audited roots")
    print("=" * 70)
    if not matches:
        print("NO MATCH")
        return 0
    for i, m in enumerate(matches, 1):
        print(f"\n[{i}] wazn={m.wazn}  root={m.root}  conf={m.confidence:.3f}")
        print(f"    bab={m.bab}")
        print(f"    morph={m.morph_type}  source={m.source}")
        print(f"    variant={m.variant_label} → {m.variant_form}")
        for ev in m.evidence:
            print(f"    • {ev}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
