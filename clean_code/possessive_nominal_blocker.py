"""possessive_nominal_blocker.py — مَنع اسم+ضَمير مِن التَّصعيد إلى فِعل.

تَنفيذ تَوصيَة المُستَخدِم 2026-05-25:

  "Possessive/Genitive Nominal Blocker:
   إِذا كانَ الـtoken لَه stem اسميّ + ضَمير مُلصَق
   وَيَقَع بَعد HARF_JARR أَو في خانة إِضافَة،
   امنَع تَصعيده إلى FIIL."

أَمثِلَة المُستَخدِم:
  أَجَلِهِ، رَبِّهِ، عِلْمِهِ، كِتَابِهِ — كُلّها اسم مُضاف، لا فِعل.

الـcontract:
  1. تَفحَص هَل الـtoken يَنتَهي بِضَمير مُتَّصِل مَعروف
  2. تَنزِع الضَّمير، تَفحَص الـstem
  3. إِذا الـstem لا يُطابِق بُنية فِعل واضِحَة (لا IV prefix، لا PV CCC،
     لا CV hamzat wasl) → اسم. امنَع FIIL.

كُلّ ضَمائر المُلصَقات في data/contracts/lists/possessive_pronoun_suffixes.csv.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
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


# ─────────────────────────────────────────────────────────────────
# Lexicon — ضَمائر مُلصَقَة
# ─────────────────────────────────────────────────────────────────

_POSSESSIVE_SUFFIXES: list[str] = []
_POSSESSIVE_INFO: dict[str, dict] = {}


def _load_suffixes() -> None:
    if _POSSESSIVE_SUFFIXES:
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
            _POSSESSIVE_SUFFIXES.append(sfx)
            _POSSESSIVE_INFO[sfx] = row
    # تَرتيب الأَطول أَوَّلًا — كَي نُطابِق هُمَا قَبل هُ
    _POSSESSIVE_SUFFIXES.sort(key=len, reverse=True)


# ─────────────────────────────────────────────────────────────────
# Verb-stem detector — هَل هَذا الـstem فِعل؟
# ─────────────────────────────────────────────────────────────────

_IV_PREFIXES_DIAC = ("يَ", "يُ", "تَ", "تُ", "نَ", "نُ", "أَ", "أُ")


def _stem_looks_like_verb(stem: str) -> bool:
    """يَفحَص هَل stem يَحوي بُنية فِعل واضِحَة.

    قَوي = نَعم:
      • بَدَأ بِبادِئة مُضارِع (يَ/تَ/نَ/أَ مَع فَتحَة/ضَمَّة)
      • بَدَأ بِهَمزَة وَصل + سُكون (افْعَل، استَفْعَل)
      • نَمَط فَعَلَ بِكامِل التَّشكيل + فَتحَة عَلى الأَوَّل

    مَنع قَطعيّ (لَيس فِعل):
      • يَنتَهي بِكَسرَة بِدون ضَمير لاحِق (ـِ = حالَة جَرّ، لا فِعل)
      • يَنتَهي بِسُكون عَلى آخِر حَرف ثُمّ كَسرَة (اسم مَجرور: عِلْمِ)
    """
    if not stem:
        return False

    plain = _strip_diac(stem)
    if len(plain) < 3:
        return False

    # === HARD-NO: نِهايَة الـstem كَسرَة → جَرّ، لَيس فِعل ===
    # (الفِعل يَنتَهي بِفَتحَة/ضَمَّة/سُكون، لا بِكَسرَة بَسيطَة)
    if stem.endswith("ِ"):
        return False

    # IV
    if stem.startswith(_IV_PREFIXES_DIAC) and len(plain) >= 3:
        return True

    # CV / PV with hamzat wasl
    if plain.startswith("ا") and len(plain) >= 4:
        # هَمزَة وَصل + سُكون عَلى ثاني حَرف
        if len(stem) >= 4 and "ْ" in stem[:4]:
            return True
        # استَفْعَل، انفَعَل، افتَعَل، اتَّفَعَل
        if plain.startswith(("است", "انف", "افت", "ات")):
            return True
        # شَدّة بَعد هَمزَة وَصل (form VIII: اتَّقَى، اتَّخَذَ)
        if "ّ" in stem[:5]:
            return True

    # === Conj + verb body (فَاكْتُبُو، وَاتَّقُو) ===
    # نَزِل بادِئة العَطف وَ نُعيد الفَحص
    if plain.startswith(("ف", "و")) and len(plain) >= 4:
        sub_stem = stem[2:] if stem[:2] in ("فَ", "وَ") else stem[1:]
        sub_plain = _strip_diac(sub_stem)
        if sub_plain.startswith("ا") and len(sub_plain) >= 3:
            # هَمزَة وَصل بَعد عَطف
            if "ْ" in sub_stem[:4] or "ّ" in sub_stem[:5]:
                return True
        # IV بَعد عَطف
        if sub_stem.startswith(_IV_PREFIXES_DIAC):
            return True
        # ل + يَ (لام الأَمر + مُضارِع) بَعد عَطف
        if sub_stem.startswith(("لْ", "لِ")) and len(sub_stem) >= 4:
            if sub_stem[2:].startswith(_IV_PREFIXES_DIAC):
                return True

    # PV بَسيط: 3 حَرف + 3 حَرَكات
    # نَطلُب أَنّ الحَرف الثاني لَيس مُدّ (ا/ى/و/ي)
    # وَ أَنّ الحَرف الأَوَّل عَلَيه فَتحَة (PV نَمَطيّ فَعَلَ)
    if len(plain) == 3 and plain[1] not in {"ا", "ى", "و", "ي"}:
        # يَحتاج فَتحَة عَلى الأَوَّل (نَمَط فَعَل)
        # ـِ عَلى الأَوَّل = اسم مَكسور (عِلْم) لا فِعل
        if (len(stem) >= 5 and stem[1] == "َ"
            and stem[3] in {"َ", "ُ", "ِ", "ْ"}):
            return True

    return False


# ─────────────────────────────────────────────────────────────────
# Main blocker
# ─────────────────────────────────────────────────────────────────

@dataclass
class PossessiveCheckResult:
    blocked: bool
    reason: str = ""
    detected_suffix: str = ""
    nominal_stem: str = ""


def check_possessive_nominal(token: str) -> PossessiveCheckResult:
    """يَفحَص هَل الـtoken اسم + ضَمير مُلصَق.

    Returns:
      PossessiveCheckResult(blocked=True) إِذا الـstem اسميّ + ضَمير
      PossessiveCheckResult(blocked=False) إِذا غَير ذَلِك (فِعل + ضَمير
        مَفعول أَو لا ضَمير)
    """
    _load_suffixes()

    if not token or not token.strip():
        return PossessiveCheckResult(blocked=False)

    plain = _strip_all(token)
    if len(plain) < 3:
        return PossessiveCheckResult(blocked=False)

    # نُجَرِّب كُلّ ضَمير (الأَطول أَوَّلًا)
    for sfx in _POSSESSIVE_SUFFIXES:
        plain_sfx = _strip_all(sfx)
        if not plain_sfx:
            continue
        if not plain.endswith(plain_sfx):
            continue
        # احسِب طول الـ stem المُتَبَقّي
        stem_plain = plain[:-len(plain_sfx)]
        if len(stem_plain) < 2:
            continue  # stem قَصير جِدًّا

        # نَأخُذ الـstem مَع التَّشكيل — نَزِل عَلى الـtoken كامِلًا
        # نَفصِل: نَبحَث مَوقِع آخِر حَرف stripped في الـtoken
        # (تَقدير: نَستَعمِل _strip_all لِنُحَدِّد المَوقِع)
        # طَريقَة بَسيطَة: نَنزِع آخِر len(plain_sfx) حَرف stripped
        # مِن الـtoken الكامِل.
        stem_full = _strip_token_suffix(token, plain_sfx)

        # هَل الـstem فِعل واضِح؟
        if _stem_looks_like_verb(stem_full):
            # فِعل + ضَمير مَفعول → لا تَمنَع
            return PossessiveCheckResult(blocked=False)

        # stem لَيس فِعلًا → اسم + ضَمير مُضاف إِلَيه → امنَع
        return PossessiveCheckResult(
            blocked=True,
            reason=f"nominal stem + possessive suffix ({sfx}) → idafa, not verb",
            detected_suffix=sfx,
            nominal_stem=stem_full,
        )

    return PossessiveCheckResult(blocked=False)


def _strip_token_suffix(token: str, plain_sfx: str) -> str:
    """يَنزِع الـsuffix مِن نِهايَة الـtoken الكامِل (بِالتَّشكيل)."""
    if not plain_sfx:
        return token
    # نَزِل مِن النِّهايَة حَتَّى نَتَخَلَّص مِن نَفس عَدَد الحُروف
    result_chars = list(token)
    chars_to_remove = len(plain_sfx)
    i = len(result_chars) - 1
    while i >= 0 and chars_to_remove > 0:
        c = result_chars[i]
        if c in _DIACRITICS or c in _SUBLETTERS:
            del result_chars[i]
        else:
            del result_chars[i]
            chars_to_remove -= 1
        i = len(result_chars) - 1 if i > len(result_chars) - 1 else i - 1
    return "".join(result_chars)


# ─────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cases = [
        # (token, expected_blocked, note)
        ("أَجَلِهِ", True, "noun + هـ"),
        ("رَبِّهِ", True, "noun + هـ"),
        ("كِتَابِهِ", True, "noun + هـ"),
        ("عِلْمِهِ", True, "noun + هـ"),
        ("بَيتُهَا", True, "noun + ها"),
        ("رَبُّنَا", True, "noun + نا"),
        ("اسْمُكَ", True, "noun + كَ"),
        # Verb + object pronoun — should NOT block
        ("يَضْرِبُهُ", False, "verb + هـ (مفعول)"),
        ("كَتَبَهُ", False, "verb + هـ"),
        ("نَزَّلَهَا", False, "verb + ها"),
        ("اكْتُبْهُ", False, "imperative + هـ"),
        ("عَلَّمَنَا", False, "verb + نا"),
        # No suffix — should NOT block
        ("كِتَابٌ", False, "no suffix"),
        ("كَتَبَ", False, "verb no suffix"),
    ]
    print(f"{'token':<22} {'expected':<10} {'got':<10} {'reason'}")
    print("-" * 95)
    for tok, exp, note in cases:
        r = check_possessive_nominal(tok)
        mark = "✓" if r.blocked == exp else "✗"
        exp_str = "BLOCK" if exp else "PASS"
        got_str = "BLOCK" if r.blocked else "PASS"
        extra = f" — {r.reason}" if r.blocked else ""
        print(f"{mark} {tok:<20} {exp_str:<10} {got_str:<10} {note}{extra}")
