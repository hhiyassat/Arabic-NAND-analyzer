"""master_token_lookup.py — LookupClassifier فَوق master_token_table.csv.

الهَدَف: 95%+ مِن tokens القُرآن يُصَنَّفون مِن lookup مُباشِر (مَصدَر MASAQ)،
الـheuristics تَبقى لِلـOOV فَقَط (5%- مِن النَّصّ + كُلّ النُّصوص خارِج القُرآن).

API:
  lookup(token: str) → dict | None
    إِن وُجِد، يُرجِع:
      {
        "word_class": "FIIL" / "ISM_MUARAB" / "ISM_MABNI" / "JAMID" / "HARF" / "ISM_MAWSOOL",
        "lemma", "root", "wazn", "aspect", "case", "role",
        "source": "MASAQ:<row_id>",
        "confidence": "Certificate" / "Hypothesis",
        "first_seen_at": "<sura>:<verse>:<word>",
      }
    إِن لَم يوجَد، يُرجِع None وَ يَترُك المَجال لِلـheuristics.

الـlookup بِـ 3 مُستَويات:
  1. exact surface (التَّشكيل كامِل)
  2. plain (بِلا تَشكيل، ٱ→ا)
  3. None — caller يُكمِل بِـ heuristics
"""
from __future__ import annotations

import csv
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_TABLE_PATH = _HERE / "data" / "master_token_table.csv"

_DIACRITICS = set("ًٌٍَُِّْٰـ")
_SUBLETTERS = set("ٰۭٓۚۖۗۘۙۛۜ۝ۥۦ۠")


def _strip_diac(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIACRITICS)


def _strip_all(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIACRITICS and c not in _SUBLETTERS)


def _normalize(s: str) -> str:
    """تَطبيع شامِل: ٱ/آ/إ/أ/ٰ → ا، ـ → حَذف.

    Step C Part 1/2 (2026-05-29): also strip the Quranic small high
    alif madd marker ٓ (U+0653). This combining mark is a recitation
    annotation indicating that an adjacent long vowel is to be
    prolonged; it carries no morphological / lexical value and is
    NOT stored in the MASAQ CSV surface column. Without this strip,
    corpus tokens like وَأَوْحَيْنَآ (ending in ا + ٓ) fail both
    `_EXACT_INDEX` (CSV has وَأَوْحَيْنَا without the marker) AND the
    `_NORMALIZED_INDEX` (the normalize step previously preserved
    the marker). Effect is LOOKUP-ONLY — the engine still stores
    the original surface for display.
    """
    return ((s or "")
            .replace("ٱ", "ا")
            .replace("آ", "ا")
            .replace("ٰ", "ا")
            .replace("ٓ", ""))


def _normalize_strong(s: str) -> str:
    """تَطبيع أَقوى: + إ/أ → ا (لِلـlexicon lookup)."""
    return (_normalize(s)
            .replace("إ", "ا")
            .replace("أ", "ا"))


# Lazy loading
_EXACT_INDEX: dict | None = None
_PLAIN_INDEX: dict | None = None


def _load():
    global _EXACT_INDEX, _PLAIN_INDEX, _NORMALIZED_INDEX, _PLAIN_AMBIG
    if _EXACT_INDEX is not None:
        return
    _EXACT_INDEX = {}
    _PLAIN_INDEX = {}
    _NORMALIZED_INDEX = {}
    _PLAIN_AMBIG = set()  # plain forms that have multiple word_classes
    if not _TABLE_PATH.is_file():
        return
    with _TABLE_PATH.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            surf = (row.get("surface") or "").strip()
            plain = (row.get("plain") or "").strip()
            if not surf:
                continue
            entry = {
                "word_class": row.get("word_class", ""),
                "masaq_tag": row.get("masaq_tag", ""),
                "lemma": row.get("lemma", ""),
                "root": row.get("root", ""),
                "wazn": row.get("wazn", ""),
                "aspect": row.get("aspect", ""),
                "case": row.get("case", ""),
                "role": row.get("role", ""),
                "source": row.get("source", "MASAQ"),
                "confidence": row.get("confidence", "Certificate"),
                "first_seen_at": row.get("first_seen_at", ""),
                "ambiguous": row.get("ambiguous", ""),
            }
            _EXACT_INDEX.setdefault(surf, entry)
            # normalized: keep tashkīl but normalize ٱ/آ/ٰ → ا
            norm_with_tash = _normalize(surf)
            existing_norm = _NORMALIZED_INDEX.get(norm_with_tash)
            if existing_norm is None:
                _NORMALIZED_INDEX[norm_with_tash] = entry
            elif existing_norm["word_class"] != entry["word_class"]:
                # تَضارُب — نَحذِف الـnorm entry لِنُجبِر exact-only match
                _NORMALIZED_INDEX[norm_with_tash] = {"_ambig": True}
            # plain: track ambiguity
            if plain:
                existing = _PLAIN_INDEX.get(plain)
                if existing is None:
                    _PLAIN_INDEX[plain] = entry
                elif existing["word_class"] != entry["word_class"]:
                    _PLAIN_AMBIG.add(plain)


_NORMALIZED_INDEX: dict | None = None
_PLAIN_AMBIG: set | None = None


def lookup(token: str) -> dict | None:
    """يَبحَث في الجَدول. يُرجِع entry أَو None.

    تَرتيب البَحث (الأَدَقّ أَوَّلًا):
      1. exact surface (التَّشكيل كامِل)
      2. normalized surface (ٱ/آ/ٰ → ا، التَّشكيل مَحفوظ)
      3. plain (بِلا تَشكيل) — فَقَط إِن لَم يَكُن في قائِمَة الـambiguous

    لَو الـplain مُلتَبِس (نَفس الجِسم لَه أَكثَر مِن word_class)،
    نُرجِع None وَ نَترُك الـheuristics تُقَرِّر.
    """
    if not token:
        return None
    _load()
    if token in _EXACT_INDEX:
        return _EXACT_INDEX[token]
    norm = _normalize(token)
    if norm in _NORMALIZED_INDEX:
        e = _NORMALIZED_INDEX[norm]
        if e.get("_ambig"):
            return None
        return e
    # لا plain-fallback — يُضَيِّع تَمييز التَّشكيل (حَقَّ vs حَقٌّ).
    # الـheuristics في Layer 1 تَتَكَفَّل بِالـtokens الَّتي لَيس لَها
    # تَشكيل كامِل (كالاختِبارات أَو النُّصوص خارِج القُرآن).
    return None


def get_coverage_stats() -> dict:
    """إِحصائيَّات الجَدول."""
    _load()
    from collections import Counter
    wc = Counter()
    for entry in _EXACT_INDEX.values():
        wc[entry["word_class"]] += 1
    return {
        "exact_index_size": len(_EXACT_INDEX),
        "plain_index_size": len(_PLAIN_INDEX),
        "word_class_distribution": dict(wc),
    }


if __name__ == "__main__":
    stats = get_coverage_stats()
    print(f"Master table loaded:")
    print(f"  exact tokens:  {stats['exact_index_size']}")
    print(f"  plain entries: {stats['plain_index_size']}")
    print(f"  word_class:    {stats['word_class_distribution']}")
    print()
    # Test sample tokens
    tests = [
        "كَتَبَ", "كِتَٰبٌ", "يَعْقُوبَ", "إِبْرَٰهِيمَ",
        "ٱلَّذِينَ", "غَيْرَ", "هُوَ", "بِسْمِ", "ٱللَّهِ",
        "أَخَذْنَا", "أَكْبَرُ", "فَمِنْهُم",
    ]
    print("Sample lookups:")
    for t in tests:
        e = lookup(t)
        if e:
            print(f"  ✓ {t:<22s} → {e['word_class']:<14s} tag={e['masaq_tag']:<10s} src={e['source'][:25]}")
        else:
            print(f"  ✗ {t:<22s} → NOT FOUND")
