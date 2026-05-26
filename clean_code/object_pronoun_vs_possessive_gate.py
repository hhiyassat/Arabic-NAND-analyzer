"""object_pronoun_vs_possessive_gate.py — يَفصِل بَين دَور الضَّمير المُلصَق.

تَوصيَة المُستَخدِم 2026-05-25:

  "لا تُعامِل كُلّ suffix=هُ كَ POSS_PRON.
   افصِل بَين:
     ضَمير مِلكيَّة اسميّ (أَجَلِهِ، رَبِّهِ، كِتَابِهِ)
     ضَمير مَفعول فِعليّ (اكتبوه، عَلَّمَهُ، يُعَلِّمُكُمُ)"

البَوّابَة:
  classify_attached_pronoun(token) → AttachedPronounRole
    ∈ {OBJECT_OF_VERB, POSSESSIVE_OF_NOUN, NONE}

الحُكم:
  • Stem يُشبِه فِعلًا (مَع/بِدون بادِئَة عَطف، مَع/بِدون ٱ هَمزَة وَصل)
    → OBJECT_OF_VERB → اسمَح بِالفِعل
  • Stem يُشبِه اسمًا (يَنتَهي بِكَسرَة، أَو لا يُطابِق نَمَط فِعل)
    → POSSESSIVE_OF_NOUN → امنَع تَصعيد إلى فِعل

تَأكيد المُستَخدِم: "ابدأ بـ ObjectPronounVsPossessivePronounGate.
لأَنّه سَيُعيد فَٱكْتُبُوهُ إلى مَسار الفِعل دون كَسر أَجَلِهِ."
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_DIACRITICS = set("ًٌٍَُِّْٰـ")
_SUBLETTERS = set("ٰۭٓۚۖۗۘۙۛۜ۝ۥۦ")

_HERE = Path(__file__).resolve().parent
_SUFFIXES_CSV = _HERE / "data" / "contracts" / "lists" / "possessive_pronoun_suffixes.csv"


def _strip_diac(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIACRITICS)


def _strip_all(s: str) -> str:
    return "".join(c for c in (s or "")
                   if c not in _DIACRITICS and c not in _SUBLETTERS)


def _normalize_alif(s: str) -> str:
    """ٱ (هَمزَة وَصل) → ا — كَي يَتَّفِق التَّحليل مَع المُعجم."""
    return (s or "").replace("ٱ", "ا")


# ─────────────────────────────────────────────────────────────────
# Suffix lexicon
# ─────────────────────────────────────────────────────────────────

_ATTACHED_SUFFIXES: list[str] = []
_SUFFIX_INFO: dict[str, dict] = {}


def _load_suffixes() -> None:
    if _ATTACHED_SUFFIXES:
        return
    if not _SUFFIXES_CSV.is_file():
        return
    seen = set()
    with _SUFFIXES_CSV.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            sfx = (row.get("suffix") or "").strip()
            if not sfx or sfx in seen:
                continue
            seen.add(sfx)
            _ATTACHED_SUFFIXES.append(sfx)
            _SUFFIX_INFO[sfx] = row
    _ATTACHED_SUFFIXES.sort(key=len, reverse=True)


# ─────────────────────────────────────────────────────────────────
# Verb-stem detector — مَع ٱ normalization
# ─────────────────────────────────────────────────────────────────

_IV_PREFIXES_DIAC = ("يَ", "يُ", "تَ", "تُ", "نَ", "نُ", "أَ", "أُ")


def _stem_looks_like_verb(stem: str) -> bool:
    """يَفحَص هَل الـstem فِعل (مَع/بِدون بادِئات).

    قَوي = نَعم:
      • IV prefix (يَ/تَ/نَ/أَ)
      • هَمزَة وَصل + سُكون عَلى ثاني حَرف (اكْتُبْ، استَفْعَل)
      • هَمزَة وَصل + شَدّة (اتَّقَى، اتَّخَذَ)
      • PV نَمَطيّ فَعَلَ (3 حُروف + فَتحَة)
      • شَدَّة في وَسَط الجِسم (عَلَّمَ، كَلَّمَ — form II)
      • بادِئة عَطف ف/و + جِسم فِعليّ (مَع ٱ أَو ا)

    مَنع قَطعيّ (لَيس فِعل):
      • يَنتَهي بِكَسرَة (ـِ) → جَرّ
    """
    if not stem:
        return False

    # NORMALIZE: ٱ → ا
    stem_n = _normalize_alif(stem)
    plain = _strip_diac(stem_n)
    if len(plain) < 3:
        return False

    # HARD-NO: نِهايَة كَسرَة → اسم مَجرور
    # استِثناء: IV verb يَفقِد ي/و قَبل ضَمير المَفعول (يَأْتِكُمْ ← يَأْتِي + كم)
    if stem_n.endswith("ِ"):
        if stem_n.startswith(_IV_PREFIXES_DIAC):
            # سُكون في الجِسم → فِعل مُضارِع نَاقِص
            if "ْ" in stem_n[:5]:
                return True
        return False

    # IV
    if stem_n.startswith(_IV_PREFIXES_DIAC) and len(plain) >= 3:
        return True

    # PV/CV with hamzat wasl
    if plain.startswith("ا") and len(plain) >= 3:
        # هَمزَة وَصل + سُكون
        if len(stem_n) >= 4 and "ْ" in stem_n[:4]:
            return True
        # form VIII (اتَّفَعَل) — مَع شَدّة
        if plain.startswith(("است", "انف", "افت", "ات", "اث", "اد", "از", "اص")):
            return True
        if "ّ" in stem_n[:5]:
            return True

    # Conj + verb body — ٱكتب، ٱتَّقى، يَكتب
    if plain.startswith(("ف", "و", "ك", "ل")) and len(plain) >= 4:
        # نَزِل بادِئة بِحَرَكَة (فَ، وَ، …) أَو حَرف واحِد
        if stem_n[:2] in ("فَ", "وَ", "كَ", "لَ", "لِ"):
            sub_stem = stem_n[2:]
        else:
            sub_stem = stem_n[1:]
        sub_plain = _strip_diac(sub_stem)
        if not sub_plain:
            return False
        # IV بَعد بادِئة
        if sub_stem.startswith(_IV_PREFIXES_DIAC):
            return True
        # هَمزَة وَصل + سُكون أَو شَدّة بَعد بادِئة
        if sub_plain.startswith("ا") and len(sub_plain) >= 3:
            if "ْ" in sub_stem[:4] or "ّ" in sub_stem[:5]:
                return True
        # لام الأَمر بَعد عَطف (وَلْيَ، فَلْيَ)
        if sub_stem.startswith(("لْ", "لِ")) and len(sub_stem) >= 4:
            if sub_stem[2:].startswith(_IV_PREFIXES_DIAC):
                return True

    # PV form II/III مَع شَدّة في الوَسَط — عَلَّمَ، كَلَّمَ
    # 3 حَرف + شَدّة + فَتحات
    if "ّ" in stem_n and len(plain) <= 4:
        # نَمَط فَعَّلَ
        if stem_n[1:2] == "َ":  # فَتحَة عَلى الأَوَّل
            return True

    # PV simple: 3 حَرف + 3 حَرَكات
    if len(plain) == 3 and plain[1] not in {"ا", "ى", "و", "ي"}:
        if (len(stem_n) >= 5 and stem_n[1] == "َ"
            and stem_n[3] in {"َ", "ُ", "ِ", "ْ"}):
            return True

    return False


# ─────────────────────────────────────────────────────────────────
# Main classifier
# ─────────────────────────────────────────────────────────────────

class AttachedPronounRole(Enum):
    NONE = "NONE"
    OBJECT_OF_VERB = "OBJECT_OF_VERB"
    POSSESSIVE_OF_NOUN = "POSSESSIVE_OF_NOUN"


@dataclass
class PronounClassification:
    role: AttachedPronounRole
    suffix: str = ""
    stem: str = ""
    reason: str = ""

    @property
    def is_possessive(self) -> bool:
        return self.role == AttachedPronounRole.POSSESSIVE_OF_NOUN

    @property
    def is_object(self) -> bool:
        return self.role == AttachedPronounRole.OBJECT_OF_VERB

    @property
    def has_pronoun(self) -> bool:
        return self.role != AttachedPronounRole.NONE


def classify_attached_pronoun(token: str) -> PronounClassification:
    """يُصَنِّف الضَّمير المُلصَق إلى object (مَفعول) أَو possessive (إِضافَة)."""
    _load_suffixes()

    if not token or not token.strip():
        return PronounClassification(role=AttachedPronounRole.NONE)

    plain = _strip_all(token)
    if len(plain) < 3:
        return PronounClassification(role=AttachedPronounRole.NONE)

    # ابحَث عَن أَطول suffix يُطابِق
    for sfx in _ATTACHED_SUFFIXES:
        plain_sfx = _strip_all(sfx)
        if not plain_sfx:
            continue
        if not plain.endswith(plain_sfx):
            continue
        stem_plain = plain[:-len(plain_sfx)]
        # MC FIX 2026-05-25: تَشديد — stem effective length ≥ 3
        # نَحسِب الشَّدّة كَحَرف إِضافيّ (رَبَّ = ر + ب + ب فِعليًّا)
        stem_full = _strip_token_suffix(token, plain_sfx)
        effective_len = len(stem_plain) + (1 if "ّ" in stem_full else 0)
        if effective_len < 3:
            continue

        stem_full = _strip_token_suffix(token, plain_sfx)

        # هَل الـstem فِعل؟
        if _stem_looks_like_verb(stem_full):
            return PronounClassification(
                role=AttachedPronounRole.OBJECT_OF_VERB,
                suffix=sfx,
                stem=stem_full,
                reason=f"verb stem ({stem_full}) + {sfx} → object pronoun",
            )

        # وإلّا → ضَمير مِلكيَّة (إِضافَة)
        return PronounClassification(
            role=AttachedPronounRole.POSSESSIVE_OF_NOUN,
            suffix=sfx,
            stem=stem_full,
            reason=f"nominal stem ({stem_full}) + {sfx} → possessive",
        )

    return PronounClassification(role=AttachedPronounRole.NONE)


def _strip_token_suffix(token: str, plain_sfx: str) -> str:
    """يَنزِع آخِر len(plain_sfx) حَرف stripped مِن الـtoken الكامِل."""
    if not plain_sfx:
        return token
    chars = list(token)
    to_remove = len(plain_sfx)
    while chars and to_remove > 0:
        c = chars[-1]
        if c in _DIACRITICS or c in _SUBLETTERS:
            chars.pop()
        else:
            chars.pop()
            to_remove -= 1
    return "".join(chars)


# ─────────────────────────────────────────────────────────────────
# Compatibility shim — يَسمَح بِاستِخدام نَفس الـAPI القَديم
# ─────────────────────────────────────────────────────────────────

@dataclass
class PossessiveCheckResult:
    """نَفس الـAPI القَديم في possessive_nominal_blocker لِلتَّوافُق."""
    blocked: bool
    reason: str = ""
    detected_suffix: str = ""
    nominal_stem: str = ""


def check_possessive_nominal_v2(token: str) -> PossessiveCheckResult:
    """API مُتَوافِق مَع possessive_nominal_blocker.check_possessive_nominal."""
    cls = classify_attached_pronoun(token)
    if cls.is_possessive:
        return PossessiveCheckResult(
            blocked=True,
            reason=cls.reason,
            detected_suffix=cls.suffix,
            nominal_stem=cls.stem,
        )
    return PossessiveCheckResult(blocked=False)


# ─────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cases = [
        # (token, expected_role)
        # OBJECT_OF_VERB
        ("فَٱكْتُبُوهُ",   AttachedPronounRole.OBJECT_OF_VERB),
        ("فَاكْتُبُوهُ",   AttachedPronounRole.OBJECT_OF_VERB),
        ("اكْتُبْهُ",      AttachedPronounRole.OBJECT_OF_VERB),
        ("عَلَّمَهُ",      AttachedPronounRole.OBJECT_OF_VERB),
        ("يَعْلَمُهُ",     AttachedPronounRole.OBJECT_OF_VERB),
        ("وَيُعَلِّمُكُمُ", AttachedPronounRole.OBJECT_OF_VERB),
        ("نَزَّلَهَا",     AttachedPronounRole.OBJECT_OF_VERB),
        ("كَتَبَهُ",       AttachedPronounRole.OBJECT_OF_VERB),
        # POSSESSIVE_OF_NOUN
        ("أَجَلِهِ",       AttachedPronounRole.POSSESSIVE_OF_NOUN),
        ("رَبِّهِ",        AttachedPronounRole.POSSESSIVE_OF_NOUN),
        ("كِتَابِهِ",      AttachedPronounRole.POSSESSIVE_OF_NOUN),
        ("عِلْمِهِ",       AttachedPronounRole.POSSESSIVE_OF_NOUN),
        ("بَيتُهَا",       AttachedPronounRole.POSSESSIVE_OF_NOUN),
        ("رَبُّنَا",       AttachedPronounRole.POSSESSIVE_OF_NOUN),
        # NONE
        ("كِتَابٌ",        AttachedPronounRole.NONE),
        ("كَتَبَ",         AttachedPronounRole.NONE),
        ("ٱللَّهَ",        AttachedPronounRole.NONE),
    ]
    print(f"{'token':<22} {'expected':<22} {'got':<22} reason")
    print("-" * 100)
    for tok, exp in cases:
        cls = classify_attached_pronoun(tok)
        mark = "✓" if cls.role == exp else "✗"
        print(f"{mark} {tok:<20} {exp.value:<22} {cls.role.value:<22} {cls.reason[:50]}")
