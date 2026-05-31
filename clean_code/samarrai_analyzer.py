"""samarrai_analyzer.py — مُحَلِّل مُوَحَّد فَوق مَعاني السَّامَرّائيّ (المُجَلَّدات 1-4).

يَأخُذ نَصًّا عَرَبيًّا مُشَكَّلًا وَ يُرجِع كُلّ المَعاني النَّحويَّة/الدَّلاليَّة
المُمكِنَة لِكُلّ كَلِمَة حَسَب مُجَلَّدات السَّامَرّائيّ الأَربَعَة.

CONSTITUTIONAL:
  • لا inline rules — كُلّ شَيء عَبر volume{1,2,3,4}_loader
  • التَّشكيل مَطلوب — الفَرق بَين «إِنْ» وَ «إِنَّ» يَحسِم المَعنى
  • source_part + source_page لِكُلّ ادِّعاء (ProofObject pattern)
  • المُخرَجات بِالعَرَبيَّة

CLI:
  python3 samarrai_analyzer.py "إِنَّ اللَّهَ غَفُورٌ"
  python3 samarrai_analyzer.py --file my_text.txt
  python3 samarrai_analyzer.py --verse 1:5     # يَأخُذ آية مِن القُرآن
  python3 samarrai_analyzer.py --stats          # إِحصاءات الـ KB
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from samarrai_loaders import (
    volume1_loader,
    volume2_loader,
    volume3_loader,
    volume4_loader,
)
from samarrai_proof_contracts import (
    ProofKind,
    kind_for_match_type,
    blockers_for_match_type,
    confidence_for_match_type,
)

CONTRACT_NAME = "SamarraiAnalyzer:v2"  # v2 = MC compliant (ProofObject + CSV-driven constructions)

DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _normalize(s: str) -> str:
    s = _strip_diac(s)
    return s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")


# ─────────────────────────────────────────────────────────────────
# مُوَحِّد الـ loaders
# ─────────────────────────────────────────────────────────────────

VOLUME_LABELS = {
    1: "مُجَلَّد 1 (المَعارِف + الإِسناد)",
    2: "مُجَلَّد 2 (الأَفعال + المَفاعيل)",
    3: "مُجَلَّد 3 (حُروف الجَرّ + التَّضمين)",
    4: "مُجَلَّد 4 (الجَزم + الشَّرط + التَّوكيد + القَسَم + التَّقديم)",
}


@dataclass
class SamarraiClaim:
    """ادِّعاء واحِد عَن كَلِمَة بِنَصّ السَّامَرّائيّ.

    MC-compliant (v2): يَحوي ProofKind + contract + blockers + alternatives.
    """
    word: str
    vocalized_form: str
    volume: int
    topic_id: str
    meaning_id: str
    meaning_ar: str
    syntactic_effect: str
    semantic_field: str
    operator: str
    example_quran: str
    surah_ayah: str
    source_part: str
    source_page: str
    confidence: float
    author_position: str
    # ─── حُقول MC الجَديدَة ──────────────────────────────────
    proof_kind: ProofKind = "Certificate"   # Certificate | Hypothesis | Zero
    contract: str = ""                       # اسم العَقد المُصدِر
    blockers: list = field(default_factory=list)
    match_type: str = "exact_vocalized"     # exact_vocalized | prefix_stripped | prefix_as_operator | plain_fallback | pattern_construction

    @property
    def source_of_claim(self) -> str:
        return f"السَّامَرّائيّ ج{self.source_part}/ص{self.source_page} [{VOLUME_LABELS[self.volume]}]"

    @property
    def proof_symbol(self) -> str:
        return {"Certificate": "✓", "Hypothesis": "?", "Zero": "✗"}.get(self.proof_kind, "·")


def _lookup_in_volume(volume_module, word: str, volume_num: int,
                        match_type: str = "exact_vocalized") -> list[SamarraiClaim]:
    """يَبحَث في مُحَمِّل واحِد + يُسَنِّد ProofKind بِحَسَب match_type."""
    results = volume_module.lookup_word(word)
    claims = []
    proof_kind, contract = kind_for_match_type(match_type)
    blockers = blockers_for_match_type(match_type)
    base_confidence = confidence_for_match_type(match_type)

    for rec in results:
        try:
            csv_conf = float(rec.get("confidence", "0") or 0)
        except (ValueError, TypeError):
            csv_conf = 0.0
        # الثِّقَة النِّهائيَّة = الأَدنى بَين ثِقَة الـ CSV وَ ثِقَة نَوع المُطابَقَة
        final_conf = min(csv_conf, base_confidence) if csv_conf > 0 else base_confidence

        # مَصدَر العَقد + الصَّفّ
        source_row = f"volume{volume_num}/{rec.get('source_file', '')}:topic={rec.get('topic_id', '')}"

        # MAANI Batch B (2026-05-29) — AuthorPositionToProofKind.
        # Exact-match downgrade only: when Samarrai explicitly marks a row
        # as a view he *reports* (does not endorse), emit the claim as
        # Hypothesis rather than Certificate. Every other value of
        # author_position — "preferred", empty, em-dash, or any corruption
        # (e.g. a surah:ayah string that landed in the wrong column) —
        # falls through to the match-type's default proof_kind (fail-open).
        # No fuzzy matching. No prose parsing. No data repair.
        row_author = (rec.get("author_position", "") or "").strip()
        row_proof_kind = "Hypothesis" if row_author == "reported" else proof_kind

        claims.append(SamarraiClaim(
            word=word,
            vocalized_form=rec.get("vocalized_form", ""),
            volume=volume_num,
            topic_id=rec.get("topic_id", ""),
            meaning_id=rec.get("meaning_id", ""),
            meaning_ar=rec.get("meaning_ar", ""),
            syntactic_effect=rec.get("syntactic_effect", ""),
            semantic_field=rec.get("semantic_field", ""),
            operator=rec.get("operator", ""),
            example_quran=rec.get("example_quran", ""),
            surah_ayah=rec.get("surah_ayah", ""),
            source_part=rec.get("source_part", ""),
            source_page=rec.get("source_page", ""),
            confidence=final_conf,
            author_position=rec.get("author_position", ""),
            # MC fields
            proof_kind=row_proof_kind,
            contract=contract,
            blockers=list(blockers),
            match_type=match_type,
        ))
    return claims


def lookup_word_all_volumes(word: str, match_type: str = "exact_vocalized") -> list[SamarraiClaim]:
    """يَبحَث في كُلّ المُجَلَّدات الأَربَعَة + يَحفَظ match_type."""
    out = []
    for loader, num in [(volume1_loader, 1), (volume2_loader, 2),
                          (volume3_loader, 3), (volume4_loader, 4)]:
        out.extend(_lookup_in_volume(loader, word, num, match_type))
    return out


# ─────────────────────────────────────────────────────────────────
# تَقطيع النَّصّ
# ─────────────────────────────────────────────────────────────────

# MC: البَوادِئ الشَّائِعَة مُحَمَّلَة مِن CSV لا inline
_COMMON_PREFIXES_CACHE: list | None = None


def _load_common_prefixes() -> list[str]:
    global _COMMON_PREFIXES_CACHE
    if _COMMON_PREFIXES_CACHE is not None:
        return _COMMON_PREFIXES_CACHE
    import csv as _csv
    path = Path(__file__).resolve().parent / "data" / "contracts" / "lists" / "samarrai_common_prefixes.csv"
    prefixes = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            rows = sorted(_csv.DictReader(f), key=lambda r: int(r.get("priority", "99") or 99))
            for row in rows:
                p = row.get("prefix", "").strip()
                if p:
                    prefixes.append(p)
    if not prefixes:
        raise RuntimeError(
            "Zero: لَم نَجِد samarrai_common_prefixes.csv. MC: لا inline fallback."
        )
    _COMMON_PREFIXES_CACHE = prefixes
    return prefixes


# يُحَمَّل lazily في _try_strip_prefix
_COMMON_PREFIXES = None  # placeholder, replaced at first call


def _try_strip_prefix(word: str) -> list[tuple[str, str]]:
    """يُرجِع قائِمَة مُحاوَلات: (الجُزء، نَوع).

    nَوع: 'full' (الكَلِمَة كامِلَة)، 'prefix' (الحَرف البادِئ)،
            'stripped' (بَعد نَزع البادِئَة).
    عِندَ نَزع البادِئَة نَحذِف الحُروف + الحَرَكات التَّابِعَة لَها.
    """
    candidates = [(word, "full")]
    plain = _normalize(word)
    for pfx in _load_common_prefixes():
        plain_pfx = _normalize(pfx)
        if plain.startswith(plain_pfx) and len(plain) > len(plain_pfx) + 1:
            i = 0
            cnt = 0
            target_len = len(_strip_diac(pfx))
            while i < len(word) and cnt < target_len:
                if word[i] not in DIACRITICS:
                    cnt += 1
                i += 1
            # البادِئَة المُشَكَّلَة كَما وَرَدَت في الكَلِمَة
            prefix_voc = word[:i]
            # نَزع التَّشكيل المُتَبَقّي بَعد آخِر حَرف مَنزوع
            while i < len(word) and word[i] in DIACRITICS:
                i += 1
            stripped_word = word[i:]
            if stripped_word and stripped_word != word:
                if prefix_voc:
                    candidates.append((prefix_voc, "prefix"))
                candidates.append((stripped_word, "stripped"))
    return candidates


def tokenize(text: str) -> list[str]:
    """تَقطيع بَسيط بِالمَسافات + الفَواصِل."""
    text = text.strip()
    tokens = re.split(r"[\s،,؛.؟!:\(\)«»\"۔\n]+", text)
    return [t for t in tokens if t]


# ─────────────────────────────────────────────────────────────────
# المُحَلِّل الرَّئيس
# ─────────────────────────────────────────────────────────────────

@dataclass
class WordAnalysis:
    word: str
    position: int
    claims: list[SamarraiClaim] = field(default_factory=list)

    @property
    def has_match(self) -> bool:
        return len(self.claims) > 0

    @property
    def best_claim(self) -> Optional[SamarraiClaim]:
        if not self.claims:
            return None
        preferred = [c for c in self.claims if c.author_position == "preferred"]
        pool = preferred or self.claims
        return max(pool, key=lambda c: c.confidence)


@dataclass
class ConstructionMatch:
    """تَركيب نَحويّ مَكشوف بِنَمَط (لا بِكَلِمَة واحِدَة)."""
    construction_id: str
    span_words: list[int]            # مَواضِع الكَلِمات في الجُملَة
    claim: SamarraiClaim              # القاعِدَة المُطلَقَة
    trigger_word: str                 # الكَلِمَة الَّتي بَدَأ بِها التَّركيب
    pattern_name: str                 # وَصف النَّمَط


@dataclass
class TextAnalysis:
    text: str
    words: list[WordAnalysis] = field(default_factory=list)
    constructions: list[ConstructionMatch] = field(default_factory=list)

    @property
    def total_words(self) -> int:
        return len(self.words)

    @property
    def words_with_match(self) -> int:
        return sum(1 for w in self.words if w.has_match)

    @property
    def total_claims(self) -> int:
        return sum(len(w.claims) for w in self.words) + len(self.constructions)

    @property
    def coverage(self) -> float:
        return self.words_with_match / self.total_words if self.total_words else 0.0


def _has_topic(wa: WordAnalysis, *topics: str) -> bool:
    return any(c.topic_id in topics for c in wa.claims)


def _get_claim_by_meaning(meaning_id: str) -> Optional[SamarraiClaim]:
    """يَجلِب SamarraiClaim مِن الـ KB بِالـ meaning_id (لِبِناء ConstructionMatch)."""
    for vol_num, loader in [(1, volume1_loader), (2, volume2_loader),
                              (3, volume3_loader), (4, volume4_loader)]:
        for rec in loader._load()["all_records"]:
            if rec.get("meaning_id") == meaning_id:
                try:
                    conf = float(rec.get("confidence", "0") or 0)
                except (ValueError, TypeError):
                    conf = 0.0
                return SamarraiClaim(
                    word="",
                    vocalized_form=rec.get("vocalized_form", ""),
                    volume=vol_num,
                    topic_id=rec.get("topic_id", ""),
                    meaning_id=meaning_id,
                    meaning_ar=rec.get("meaning_ar", ""),
                    syntactic_effect=rec.get("syntactic_effect", ""),
                    semantic_field=rec.get("semantic_field", ""),
                    operator=rec.get("operator", ""),
                    example_quran=rec.get("example_quran", ""),
                    surah_ayah=rec.get("surah_ayah", ""),
                    source_part=rec.get("source_part", ""),
                    source_page=rec.get("source_page", ""),
                    confidence=conf,
                    author_position=rec.get("author_position", ""),
                )
    return None


def _starts_with_waw(word: str) -> bool:
    """هَل الكَلِمَة تَبدَأ بِواو (مُشَكَّلَة أَو لا)؟"""
    if not word:
        return False
    first = word[0]
    return first == "و" or first == "وَ"


# ── مُحَمِّل قَواعِد التَّراكيب مِن CSV (Contract B — MC compliant) ──
_CONSTRUCTIONS_CACHE: list[dict] | None = None


def _load_construction_patterns() -> list[dict]:
    """يُحَمِّل قَواعِد التَّراكيب مِن CSV — لا inline data."""
    global _CONSTRUCTIONS_CACHE
    if _CONSTRUCTIONS_CACHE is not None:
        return _CONSTRUCTIONS_CACHE
    import csv as _csv
    path = Path(__file__).resolve().parent / "data" / "contracts" / "maani" / "constructions" / "patterns.csv"
    patterns = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            reader = _csv.DictReader(f)
            for row in reader:
                patterns.append({
                    "construction_id": row.get("construction_id", "").strip(),
                    "trigger_topic": row.get("trigger_topic", "").strip(),
                    "next_word_condition": row.get("next_word_condition", "").strip(),
                    "fires_meaning_id": row.get("fires_meaning_id", "").strip(),
                    "pattern_description_ar": row.get("pattern_description_ar", "").strip(),
                    "source_part": row.get("source_part", "").strip(),
                    "source_page": row.get("source_page", "").strip(),
                })
    _CONSTRUCTIONS_CACHE = patterns
    return patterns


def _check_condition(condition: str, next_word: str) -> bool:
    """يَفحَص الشَّرط النَّحويّ مِن construction_predicates.csv — لا inline."""
    from predicate_engine import get_construction_predicate_engine
    pe = get_construction_predicate_engine()
    ctx = {"next_word": next_word}
    return pe.evaluate(condition, ctx)


def detect_constructions(ta: TextAnalysis) -> list[ConstructionMatch]:
    """يَكشِف التَّراكيب الَّتي تَحتاج نَمَطًا لا lookup كَلِمَة.

    Contract B (MC-compliant): يَقرَأ القَواعِد مِن
    `data/contracts/maani/constructions/patterns.csv` بَدَل inline.
    """
    matches: list[ConstructionMatch] = []
    n = len(ta.words)
    patterns = _load_construction_patterns()

    for i, wa in enumerate(ta.words):
        if i + 1 >= n:
            continue
        next_wa = ta.words[i + 1]

        # تَطبيق كُلّ نَمَط مِن CSV
        for pattern in patterns:
            if not _has_topic(wa, pattern["trigger_topic"]):
                continue
            if not _check_condition(pattern["next_word_condition"], next_wa.word):
                continue
            # النَّمَط يَنطَلِق
            claim = _get_claim_by_meaning(pattern["fires_meaning_id"])
            if claim:
                # تَعليم الـ claim كَ pattern_construction
                claim.proof_kind = "Hypothesis"
                claim.contract = "PatternConstructionContract:v1"
                claim.match_type = "pattern_construction"
                claim.blockers = ["النَّمَط heuristic — قَد يُخطِئ في حالات نادِرَة"]

                pattern_name = pattern["pattern_description_ar"].format(
                    trigger=wa.word, next=next_wa.word
                )
                matches.append(ConstructionMatch(
                    construction_id=pattern["construction_id"],
                    span_words=[i, i + 1],
                    claim=claim,
                    trigger_word=wa.word,
                    pattern_name=pattern_name,
                ))

    return matches


def analyze(text: str, *, try_prefix_strip: bool = True) -> TextAnalysis:
    """يُحَلِّل النَّصّ كَلِمَة كَلِمَة عَبر المُجَلَّدات الأَربَعَة + كَشف التَّراكيب."""
    tokens = tokenize(text)
    result = TextAnalysis(text=text)
    # خَريطَة ctype (مِن _try_strip_prefix) → match_type (لِـ ProofKind)
    ctype_to_match = {
        "full": "exact_vocalized",
        "prefix": "prefix_as_operator",
        "stripped": "prefix_stripped",
    }
    for i, tok in enumerate(tokens):
        wa = WordAnalysis(word=tok, position=i)
        candidates = _try_strip_prefix(tok) if try_prefix_strip else [(tok, "full")]
        seen_keys = set()
        for cand, ctype in candidates:
            match_type = ctype_to_match.get(ctype, "exact_vocalized")
            for claim in lookup_word_all_volumes(cand, match_type=match_type):
                key = (claim.volume, claim.meaning_id)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                wa.claims.append(claim)
        # MC: Zero ProofObject صَريح عِندَ عَدَم التَّطابُق
        if not wa.claims:
            wa.claims.append(SamarraiClaim(
                word=tok, vocalized_form="", volume=0,
                topic_id="ZERO", meaning_id="NO_MATCH",
                meaning_ar="لا تَطابُق في KB — الكَلِمَة خارِج مَجال عَوامِل السَّامَرّائيّ",
                syntactic_effect="", semantic_field="", operator="",
                example_quran="", surah_ayah="",
                source_part="-", source_page="-",
                confidence=0.0, author_position="",
                proof_kind="Zero",
                contract="NoMatchSamarraiContract:v1",
                blockers=[f"«{tok}» لَم يَتَطابَق مَع أَيّ مُجَلَّد (مَع نَزع البَوادِئ)"],
                match_type="no_match",
            ))
        result.words.append(wa)
    # ── كَشف التَّراكيب فَوق word-level analysis ──
    result.constructions = detect_constructions(result)
    # ── حَسم الواو بِالسِّياق (post-pass) ──
    _disambiguate_waw(result)
    return result


# ─────────────────────────────────────────────────────────────────
# حَسم الواو بِالسِّياق (Context Disambiguator)
# ─────────────────────────────────────────────────────────────────

_WAW_DISAMBIGUATION_CACHE: list | None = None


def _load_waw_disambiguation_rules() -> list:
    """يُحَمِّل قَواعِد حَسم الواو مِن CSV."""
    global _WAW_DISAMBIGUATION_CACHE
    if _WAW_DISAMBIGUATION_CACHE is not None:
        return _WAW_DISAMBIGUATION_CACHE
    import csv as _csv
    path = Path(__file__).resolve().parent / "data" / "contracts" / "rules" / "waw_disambiguation.csv"
    rows = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            reader = _csv.DictReader(f)
            for row in reader:
                rows.append(row)
    rows.sort(key=lambda r: int(r.get("priority", "99") or 99))
    _WAW_DISAMBIGUATION_CACHE = rows
    return rows


def _waw_starts_word(word: str) -> bool:
    """هَل الكَلِمَة تَبدَأ بِـ و/وَ كَ بادِئَة؟"""
    if not word:
        return False
    # نَزع الـ NFC قَبل المُقارَنَة
    return word.startswith("و") or word.startswith("وَ")


def _looks_like_verb_pattern(wa: WordAnalysis) -> bool:
    """هَل WordAnalysis يُشبِه فِعلًا (مُضارِع أَو ماضٍ)؟ heuristic."""
    word = wa.word
    # heuristic: يَبدَأ بِـ يَ/تَ/نَ/أَ (مُضارِع) أَو يَنتَهي بِـ تُ/تَ/نا (ماضٍ)
    return (word[:1] in {"ي", "ت", "ن", "أ", "يَ", "تَ", "نَ", "أَ"}
            or word.endswith(("تُ", "تَ", "تِ", "نا", "وا")))


# PATCH 5.7 (2026-05-28) — WawQasamDisambiguationGuard.
# Short Quranic imperatives whose plain form (after وَ-strip) doesn't
# match any of the structural verb-pattern heuristics below. Examples:
#   قُل (3-letter root with damma on first, sukun on last) — extremely
#   frequent in Quran but doesn't start with يَ/تَ/نَ/أَ or end with a
#   verbal suffix.
_SHORT_IMPERATIVES_WAW_GUARD = {
    "قُل", "قُلْ", "خُذْ", "خُذ", "كُلْ", "كُل",
    "قِفْ", "قِف", "رِدْ", "رِد", "نَمْ", "نَم",
    "هَبْ", "هَب", "عِدْ", "عِد",
}


def _waw_word_residue_is_verb(wa: WordAnalysis) -> bool:
    """PATCH 5.7 — return True iff the وَ-prefixed token's residue
    (after stripping the leading وَ/و) looks like a verb form.

    Triggers on:
      • imperfect prefix (يَ/يُ/تَ/تُ/نَ/نُ/أَ/أُ)
      • lam-al-amr (residue starts with لْ)
      • form-VIII / I imperative with hamzat-wasl (ٱ/ا) — but NOT the
        definite article (residue[1] == 'ل' is whitelisted)
      • past verb suffixes (ـوا / ـتُمْ / ـتُمَا / ـنَا / ...)
      • short Quranic imperatives lexicon (قُل، خُذ، كُل، ...)

    Used by `is_sentence_start_with_majroor` to reject false-positive
    qasam injection on verb-headed verses like وَقُل / وَٱتَّقُوا /
    وَأَشْهِدُوا / وَٱسْتَشْهِدُوا. Does NOT block real qasam: residues
    like ٱلشَّمْسِ / الشَّمسِ / ضُحَاهَا fall through (definite-article
    whitelist or no verb-pattern match).
    """
    word = wa.word or ""
    if word.startswith("وَ"):
        residue = word[2:]
    elif word.startswith("و"):
        residue = word[1:]
    else:
        residue = word
    if not residue:
        return False

    # Imperfect prefix (mudāriʿ)
    if residue[:2] in ("يَ","يُ","تَ","تُ","نَ","نُ","أَ","أُ"):
        return True
    if residue[:1] in ("ي","ت","ن"):
        return True
    # Lam-al-amr verb form
    if residue.startswith(("لْ",)):
        return True
    # Form VIII / I imperative with hamzat-wasl, EXCLUDING definite article ٱل
    if residue[:1] in ("ٱ","ا") and len(residue) >= 3 and residue[1:2] != "ل":
        return True
    # Past-tense person suffixes
    if residue.endswith(("تُ","تَ","تِ","نا","وا","تُمْ","تُمَا","تُنَّ","تَا","نَ")):
        return True
    # Short imperative lexicon
    if residue in _SHORT_IMPERATIVES_WAW_GUARD:
        return True
    return False


_WAW_TOPIC_PREFIXES = ("PREP_WAW", "QASAM", "WAW_", "و")


def _is_waw_claim(claim: "SamarraiClaim") -> bool:
    tid = claim.topic_id or ""
    return any(tid.startswith(p) for p in _WAW_TOPIC_PREFIXES)


def _disambiguate_waw(ta: TextAnalysis) -> None:
    """يَفحَص كُلّ كَلِمَة تَبدَأ بِواو + يَحسِم المَعنى بِالسِّياق.

    إِذا تَتَطابَق قَواعِد waw_disambiguation.csv:
      • إِذا الِادِّعاء المُختار مَوجود في claims → نَرفَعه إِلى صَدرها كَ Certificate
      • وَ إِلّا → نَحقِن SamarraiClaim جَديد لِلواو المُختارَة
      • نَخفِض ادِّعاءات الواو الأُخرى إِلى Hypothesis
    """
    rules = _load_waw_disambiguation_rules()
    if not rules:
        return

    for i, wa in enumerate(ta.words):
        if not _waw_starts_word(wa.word):
            continue
        # نَجمَع ادِّعاءات الواو
        waw_claims = [c for c in wa.claims if _is_waw_claim(c)]
        if not waw_claims:
            continue  # ليس واو حَرف

        # نَفحَص كُلّ قاعِدَة بِالتَّرتيب
        chosen_topic = None
        chosen_meaning = None
        chosen_rule = None
        for rule in rules:
            check = rule.get("context_check", "")
            preferred = rule.get("preferred_topic_id", "").strip()
            if not preferred:
                continue

            if check == "prev_is_verb_pattern_match":
                if i + 1 < len(ta.words) and i >= 1:
                    next_wa = ta.words[i + 1]
                    if _looks_like_verb_pattern(next_wa):
                        chosen_topic = preferred
                        chosen_meaning = rule.get("preferred_meaning_ar", "")
                        chosen_rule = rule.get("rule_id", "")
                        break

            elif check == "prev_clause_complete":
                if i >= 2 and i + 1 < len(ta.words):
                    next_wa = ta.words[i + 1]
                    if _looks_like_verb_pattern(next_wa):
                        chosen_topic = preferred
                        chosen_meaning = rule.get("preferred_meaning_ar", "")
                        chosen_rule = rule.get("rule_id", "")
                        break

            elif check == "is_sentence_start_with_majroor":
                if i == 0 and i + 1 < len(ta.words):
                    # PATCH 5.7 (2026-05-28) — WawQasamDisambiguationGuard.
                    # Reject qasam injection when the وَ-word itself is a
                    # verb. وَ here is عَطف/استئناف, not قَسَم. Targets
                    # verses like 24:31 «وَقُل لِّلْمُؤْمِنَٰتِ» where the
                    # next-word kasra (لِّلْمُؤْمِنَٰتِ) was falsely treated
                    # as a majroor noun signalling qasam.
                    if _waw_word_residue_is_verb(wa):
                        continue
                    next_word = ta.words[i + 1].word
                    if next_word.endswith(("ِ", "ٍ", "ي")):
                        chosen_topic = preferred
                        chosen_meaning = rule.get("preferred_meaning_ar", "")
                        chosen_rule = rule.get("rule_id", "")
                        break

        if chosen_topic is None:
            continue

        # هَل الِادِّعاء المُختار مَوجود؟
        found = False
        for c in wa.claims:
            if c.topic_id == chosen_topic:
                c.proof_kind = "Certificate"
                c.contract = "WawDisambiguationContract:v1"
                c.match_type = "context_disambiguated"
                c.confidence = max(c.confidence, 0.85)
                wa.claims.remove(c)
                wa.claims.insert(0, c)
                found = True
                break
        # لَو غَير مَوجود — نَحقِن claim جَديد (مَع المَصدَر: قاعِدَة سِياقيَّة)
        if not found:
            injected = SamarraiClaim(
                word=wa.word,
                vocalized_form="وَ",
                volume=3,
                topic_id=chosen_topic,
                meaning_id=f"INJECTED:{chosen_rule}",
                meaning_ar=chosen_meaning,
                syntactic_effect="عَطف عَلى ما قَبلها — يَتبَع المَعطوف عَليه في الإِعراب",
                semantic_field="conjunction",
                operator="و",
                example_quran="",
                surah_ayah="",
                source_part="3",
                source_page="-",
                confidence=0.85,
                author_position="contextual",
                proof_kind="Certificate",
                contract="WawDisambiguationContract:v1",
                blockers=[],
                match_type="context_disambiguated",
            )
            wa.claims.insert(0, injected)

        # نَخفِض ادِّعاءات الواو الأُخرى إِلى Hypothesis
        for c in wa.claims:
            if _is_waw_claim(c) and c.topic_id != chosen_topic:
                if c.proof_kind != "Zero":
                    c.proof_kind = "Hypothesis"
                    c.blockers = list(c.blockers) + [
                        f"مَرفوض بِـ context: rule={chosen_rule} → {chosen_topic}"
                    ]


# ─────────────────────────────────────────────────────────────────
# عَرض النَّتائِج
# ─────────────────────────────────────────────────────────────────

def format_analysis(ta: TextAnalysis, *, verbose: bool = False) -> str:
    out = []
    out.append(f"contract: {CONTRACT_NAME}")
    out.append(f"النَّصّ: {ta.text}")
    out.append("")
    out.append(f"=== تَحليل عَبر المُجَلَّدات الأَربَعَة ===")
    out.append("")
    for wa in ta.words:
        if not wa.has_match:
            if verbose:
                out.append(f"  [{wa.position+1}] «{wa.word}» — لا مَعانٍ مَعروفَة")
            continue
        out.append(f"  [{wa.position+1}] «{wa.word}» → {len(wa.claims)} ادِّعاء:")
        for c in wa.claims:
            tag = "★" if c.author_position == "preferred" else "○"
            out.append(
                f"    {tag} {c.proof_symbol} [ج{c.source_part}] {c.meaning_ar[:65]}"
            )
            if verbose:
                out.append(f"        kind={c.proof_kind} | contract={c.contract} | conf={c.confidence:.2f}")
                out.append(f"        topic={c.topic_id} | match={c.match_type}")
                if c.blockers:
                    out.append(f"        blockers: {' | '.join(c.blockers)}")
                if c.example_quran:
                    out.append(f"        مَثَل: {c.example_quran} [{c.surah_ayah}]")
        out.append("")
    # ── التَّراكيب المَكشوفَة ──
    if ta.constructions:
        out.append(f"=== التَّراكيب النَّحويَّة المَكشوفَة ===")
        out.append("")
        for cm in ta.constructions:
            c = cm.claim
            tag = "★" if c.author_position == "preferred" else "○"
            out.append(f"  ▸ {cm.construction_id}")
            out.append(f"      النَّمَط: {cm.pattern_name}")
            out.append(f"    {tag} [ج{c.source_part}] {c.meaning_ar}")
            if verbose:
                out.append(f"        topic={c.topic_id} | {c.syntactic_effect}")
                if c.example_quran:
                    out.append(f"        مَثَل: {c.example_quran} [{c.surah_ayah}]")
        out.append("")

    out.append(f"=== الإِحصاءات ===")
    out.append(f"  الكَلِمات: {ta.total_words}")
    out.append(f"  لَها مَعانٍ: {ta.words_with_match} ({ta.coverage*100:.1f}%)")
    out.append(f"  إِجماليّ الِادِّعاءات الكَلِميَّة: {sum(len(w.claims) for w in ta.words)}")
    out.append(f"  التَّراكيب المَكشوفَة: {len(ta.constructions)}")
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────
# إِحصاءات الـ KB
# ─────────────────────────────────────────────────────────────────

def kb_stats() -> str:
    out = ["=== إِحصاءات Samarrai KB ==="]
    total_records = 0
    total_topics = 0
    for vol_num, loader in [(1, volume1_loader), (2, volume2_loader),
                              (3, volume3_loader), (4, volume4_loader)]:
        s = loader.stats()
        out.append(f"\n{VOLUME_LABELS[vol_num]}:")
        out.append(f"  السِّجِلّات: {s['total_records']}")
        out.append(f"  الأَبواب: {s['topics_count']}")
        total_records += s['total_records']
        total_topics += s['topics_count']
    out.append(f"\n=== المَجموع ===")
    out.append(f"  السِّجِلّات: {total_records}")
    out.append(f"  الأَبواب: {total_topics}")
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

def _load_quran_verse(ref: str) -> Optional[str]:
    """يَجِب آية مِن مَلَفّ القُرآن المُشَكَّل لَو مَوجود."""
    surah, ayah = ref.split(":")
    base = Path(__file__).resolve().parent.parent
    candidates = [
        base / "data" / "quran-uthmani-with-pause-mark.txt",
        base / "data" / "quran_uthmani.txt",
        base / "data" / "quran.txt",
        Path(__file__).parent / "data" / "quran_uthmani.txt",
    ]
    for p in candidates:
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) >= 3 and parts[0] == str(int(surah)) and parts[1] == str(int(ayah)):
                    return parts[2]
    return None


def main():
    parser = argparse.ArgumentParser(description="مُحَلِّل السَّامَرّائيّ — مَعاني النَّحو الأَربَعَة")
    parser.add_argument("text", nargs="?", help="النَّصّ المُشَكَّل المُراد تَحليله")
    parser.add_argument("--file", help="مَلَفّ نَصّيّ")
    parser.add_argument("--verse", help="آية مِن القُرآن (سُورة:آية)")
    parser.add_argument("--stats", action="store_true", help="إِحصاءات الـ KB فَقَط")
    parser.add_argument("--verbose", "-v", action="store_true", help="عَرض تَفصيليّ")
    parser.add_argument("--no-prefix", action="store_true", help="لا تَجَرِّب نَزع البَوادِئ")

    args = parser.parse_args()

    if args.stats:
        print(kb_stats())
        return

    if args.text:
        text = args.text
    elif args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    elif args.verse:
        text = _load_quran_verse(args.verse)
        if not text:
            print(f"⚠ لَم نَجِد الآية {args.verse}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    ta = analyze(text, try_prefix_strip=not args.no_prefix)
    print(format_analysis(ta, verbose=args.verbose))


if __name__ == "__main__":
    main()
