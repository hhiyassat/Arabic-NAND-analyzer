"""non_verb_override_gate.py — بَوَّابَة مَنع الفِعل الكاذِب.

تَنفيذ تَوصيَة المُستَخدِم 2026-05-25:

  "العَقد لا يَقول: هَل يُشبِه فِعلًا؟
   بَل يَقول: هَل يُشبِه فِعلًا، ولا تَنطَبِق عَلَيه أَيّ مانِعات
   اسميَّة/حَرفيَّة/مَبنيَّة/إِغلاق؟"

  VerbCertificate =
    VerbEvidence
    ∧ NoNominalBlocker
    ∧ NoParticleBlocker
    ∧ NoMabniBlocker
    ∧ NoClosedListOverride

هَذا الوَحدَة تَفحَص الـoverrides الـ4 وَتَردّ:

  OverrideResult(blocked: bool, reason: str, override_class: str)

تُستَدعى مِن داخِل VerbFormContract.evaluate_verb_form() قَبل
إِصدار Certificate.
"""

from __future__ import annotations

from dataclasses import dataclass

_DIACRITICS = set("ًٌٍَُِّْٰـ")
# Recitation/sub-letter marks: small alif, madd, etc.
_SUBLETTERS = set("ٰۭٓۚۖۗۘۙۛۜ۝۠ۥۦ")


def _strip_diac(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIACRITICS)


def _strip_all_marks(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIACRITICS and c not in _SUBLETTERS)


# ─────────────────────────────────────────────────────────────────
# Closed-list overrides — أَدوات مَعروفَة لا تَكون فِعلًا أَبَدًا
# ─────────────────────────────────────────────────────────────────

# قَوائم صَريحَة لِلكَلِمات التي تُشبِه فِعلًا شَكلًا وَلَيست فِعلًا.
# هَذه القائِمَة قَصيرَة لأَنّ closed_class الكامِل يُدار عَبر CSV
# (singular_terms, relative_pronouns, demonstratives, operators).
# هَذه هي الـtokens المُتَنازَع عَلَيها التي يَخطَئ فيها VerbFormContract.
# ─────────────────────────────────────────────────────────────────
# Proper noun + functional noun lexicons (CSV — لا inline)
# ─────────────────────────────────────────────────────────────────
import csv as _csv
from pathlib import Path as _Path

_PROPER_NOUNS_PLAIN_CACHE: set | None = None
_FUNCTIONAL_NOUNS_CACHE: set | None = None


def _load_proper_nouns() -> set:
    global _PROPER_NOUNS_PLAIN_CACHE
    if _PROPER_NOUNS_PLAIN_CACHE is not None:
        return _PROPER_NOUNS_PLAIN_CACHE
    here = _Path(__file__).resolve().parent
    path = here / "data" / "contracts" / "lists" / "proper_nouns_lexicon.csv"
    s = set()
    if path.is_file():
        with path.open(encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                p = (row.get("plain") or row.get("surface") or "").strip()
                if p:
                    # نَستَخدِم _strong_normalize أَوَّلًا (ٰ→ا) ثُمَّ نَزع التَّشكيل
                    s.add(_strip_all_marks(_strong_normalize(p)))
    _PROPER_NOUNS_PLAIN_CACHE = s
    return s


def _load_functional_nouns() -> set:
    global _FUNCTIONAL_NOUNS_CACHE
    if _FUNCTIONAL_NOUNS_CACHE is not None:
        return _FUNCTIONAL_NOUNS_CACHE
    here = _Path(__file__).resolve().parent
    path = here / "data" / "contracts" / "lists" / "functional_nouns_lexicon.csv"
    s = set()
    if path.is_file():
        with path.open(encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                surf = (row.get("surface") or "").strip()
                if surf:
                    s.add(surf)
                    s.add(_strip_all_marks(_normalize_alif(surf)))
                    s.add(_strip_all_marks(_strong_normalize(surf)))
    _FUNCTIONAL_NOUNS_CACHE = s
    return s


_KNOWN_NON_VERBS = {
    # ظُروف وَشَرط
    "إِذَا", "إذا", "إِذْ", "إذ",
    "إِذًا", "إذا",
    # تَركيب كاف + ما
    "كَمَا", "كما", "كَأَنَّمَا",
    # شَرطيَّات
    "إِنَّمَا", "إنما",
    # أَدوات استِفهام/شَرط مَبنيَّة
    "مَتَى", "متى", "أَيْنَ", "أين",
    "كَيْفَ", "كيف", "هَلْ", "هل",
    # أَدوات نَفي/استِثناء
    "إِلَّا", "إلا",
}


# ─────────────────────────────────────────────────────────────────
# Nominal surface blockers
# ─────────────────────────────────────────────────────────────────

def _starts_with_definite_article(token: str) -> bool:
    """ال أَو الْ أَو ٱل في البِدايَة → اسم قَطعًا."""
    # نَتجاوَز ٱ → ا
    t = token.replace("ٱ", "ا")
    if t.startswith(("ال", "الْ", "الَ", "الُ", "الِ")):
        # تَأَكَّد أَنّ هَذه فِعلًا "ال" التَّعريف وَلَيس بِدايَة كَلِمَة طَويلَة
        # تَبدَأ بِـ ا ثُمّ ل (مَثَلًا «اللَّيْل» تَبدَأ بِـ ا+ل+ل+ي…)
        # ال التَّعريف يَتبَعُها حَرف ساكِن أَو مَشدود غالِبًا
        plain = _strip_diac(t)
        if len(plain) >= 3 and plain[0] == "ا" and plain[1] == "ل":
            return True
    return False


def _starts_with_definite_article_after_prefix(token: str, conj: str) -> bool:
    """فَ/وَ + ال → اسم (مَع conjunction)."""
    if not conj:
        return False
    rest = token[len(conj):]
    return _starts_with_definite_article(rest)


def _ends_with_taa_marbuta(token: str) -> bool:
    """ـة → مُؤَنَّث، اسم."""
    plain = _strip_diac(token)
    return plain.endswith("ة")


def _ends_with_dual_marker(token: str) -> bool:
    """ـان/ـانِ/ـيْنِ/ـَيْنِ → مُثَنَّى، اسم.

    نَستَثني:
      • المُضارِع المُثَنَّى (يَكْتُبَانِ، تَكُونَا) — يَبدَأ بِبادِئة فِعليَّة
      • كان/ليس + lemma مَعروف (3 حُروف فَقَط، لَيس مُثَنَّى)
    """
    plain = _strip_diac(token)
    if not (plain.endswith("ان") or plain.endswith("ين")):
        return False
    # استِثناء: المُثَنَّى يَحتاج جِسم ≥4 حُروف
    # (كان = 3 حُروف، لَيس مُثَنَّى)
    if len(plain) < 4:
        return False
    # استِثناء: لَو بَدَأ بِبادِئة مُضارِع (يَ/تَ/نَ) فَهَذا فِعل مُثَنَّى
    if plain and plain[0] in {"ي", "ت", "ن"}:
        return False
    # استِثناء: لَو بَدَأ بِ ك/ف/و + يَ/تَ/نَ → فِعل بَعد عَطف
    if len(plain) >= 2 and plain[0] in {"ك", "ف", "و"} and plain[1] in {"ي", "ت", "ن"}:
        return False
    return True


def _ends_with_alif_maqsura(token: str) -> bool:
    """ـى مَع تَشكيل اسميّ → اسم تَفضيل/مَقصور."""
    plain = _strip_all_marks(token)
    # ـى أَو ـا مَع طول إِجماليّ كاف
    if plain.endswith("ى") and len(plain) >= 3:
        # استِثناء: الفِعل المُعتَلّ الناقِص (رَمَى، يَنهَى)
        # لَو بَدَأ بِبادِئة فِعليَّة قَويَّة (يَ/تَ/نَ/أَ مَع فَتحَة أَو ضَمَّة)
        if (plain[0] in {"ي", "ت", "ن", "أ"}
            and token.startswith(("يَ", "يُ", "تَ", "تُ", "نَ", "نُ", "أَ", "أُ"))):
            return False
        return True
    return False


def _is_tafdeel_pattern(token: str, body: str) -> bool:
    """أَفْعَلُ بَدون شَدّة بَعد بادِئة عَطف → اسم تَفضيل لا فِعل.

    أَقْسَطُ، أَقْوَمُ، أَدْنَى، أَكْبَرُ، أَفْضَلُ

    تَمييز: tafdeel يَنتَهي بِـ ـُ (مَرفوع) أَو ـِ (مَجرور).
    الفِعل أَفْعَلَ يَنتَهي بِـ ـَ (فَتحَة عَلى اللام = ماضٍ).

    إِضافَة 2026-05-25 (الجَلسَة 5):
    تَفضيل أَفعَل يَطلُب فَتحَة عَلى عَين الكَلِمَة (الحَرف الثالث):
        أَكْبَرُ = أ + َ + ك + ْ + ب + َ + ر + ُ
                            ↑ سُكون          ↑ فَتحَة (شَرط)
    الفِعل أَخْلُقُ:
        أ + َ + خ + ْ + ل + ُ + ق + ُ
                          ↑ ضَمَّة (لَيس فَتحَة → فِعل لا تَفضيل)
    """
    plain = _strip_diac(body)
    if not (plain.startswith("أ") and len(plain) == 4):
        return False
    # نَمَط أَفْعَلُ: أَ + ف + ْ + ع + َ + ل + ُ
    if "ّ" in body[:7]:  # شَدّة → فِعل (أَفَّر) لَيس تَفضيل
        return False
    # سُكون عَلى الفاء — شَرط ضَروريّ
    if not (body.startswith("أَ") and "ْ" in body[:5]):
        return False
    # نِهايَة بِـ ـَ (فَتحَة) → فِعل ماضٍ أَفْعَلَ (أَسْلَمَ، أَكْرَمَ، أَظْلَمَ)
    if body.endswith("َ"):
        return False  # لا تَمنَع — فِعل ماضٍ
    # === شَرط جَديد: فَتحَة عَلى العَين (المَوقِع 5) ===
    # tafdeel = أَ ف ْ ع َ ل ُ → token[5] يَجِب أَن يَكون "َ" (فَتحَة)
    # فِعل مُضارِع 1st sg = أَ ف ْ ع ُ ل ُ → token[5] = "ُ" (ضَمَّة) → فِعل
    if len(body) >= 6 and body[5] not in ("َ",):
        return False  # لَيس فَتحَة عَلى عَين → فِعل مُضارِع لا تَفضيل
    # نِهايَة بِـ ـُ (مَرفوع) أَو ـِ (مَجرور) → تَفضيل
    if body.endswith(("ُ", "ِ")):
        return True
    # أَفْعَى/أَفْعَل بِأَلِف مَقصورَة (أَدنى، أَعلى)
    if plain.endswith(("ى", "ا")) and len(plain) == 4:
        return True
    return False


def _normalize_alif(s: str) -> str:
    """تَطبيع خَفيف — يَحفَظ أ/إ كَ هَمزَة (لا يَدمِجها بِـ ا).

    يُستَخدَم في الـgates القَديمَة الَّتي تَفحَص أ-بادِئة (Form IV).
    """
    return (s or "").replace("ٱ", "ا").replace("آ", "ا")


def _strong_normalize(s: str) -> str:
    """تَطبيع شامِل — لِمُطابَقَة الـlexicons (أَعلام، ظُروف).

    ٱ/آ/إ/أ → ا، ٰ → ا، ئ → ي
    """
    return ((s or "")
            .replace("ٱ", "ا")
            .replace("آ", "ا")
            .replace("إ", "ا")
            .replace("أ", "ا")
            .replace("ؤ", "ا")
            .replace("ٰ", "ا"))


def _is_broken_plural_pattern(token: str) -> bool:
    """جُموع تَكسير عَلى وَزن أَفْعَال / أَفْعُل / أَفْعِلَة.

    تَوصيَة المُستَخدِم 2026-05-25:
      أَوْلِيَآءَ، أَنفُسُهُمْ، أَعْقَابِنَا، أَصْحَاب، أَنبِيَاء
    هَذه أَسماء جَمع تَكسير — لا أَفعال.
    قَرينَة: تَبدَأ بِـ أَ + سُكون عَلى ثاني حَرف + يَحوي ا/ى في الوَسَط/الآخِر
    أَو يَنتَهي بِـ ضَمير مُلصَق (ـهُمْ، ـنا، ـكُمْ، ـه).
    """
    plain = _strip_all_marks(_normalize_alif(token))
    if not plain.startswith("أ"):
        return False
    if len(plain) < 5:
        return False

    # GATE -1: واو الجَماعَة في الفِعل الماضي → فِعل، لا اسم
    # أَكَلُوا، أَخْرَجُوا، أُحْصِرُوا، شَرِبُوا، قَتَلُوا
    # نَمَط: …و+ا (نِهايَة) أَو …و+كُمْ/هُمْ (مَع لاحِقَة مَفعول)
    if plain.endswith("وا"):
        return False  # ـوا = ماضٍ جَماعَة، لا اسم
    # واو قَبل كُمْ/هُمْ/هَا = ماضٍ جَماعَة + ضَمير مَفعول
    for sfx in ("هُمْ","هُم","كُمْ","كُم","هَا","نَا"):
        if token.endswith(sfx) or token.endswith(_strip_diac(sfx)):
            sfx_start = token.rfind(sfx[0])
            if sfx_start > 2:
                pre = token[max(0,sfx_start-2):sfx_start]
                if "و" in pre:  # واو الجَماعَة قَبل اللاحِقَة → فِعل
                    return False

    # GATE 0: فَحص ما-قَبل-اللاحِقَة. لَو سُكون/فَتحَة قَبل نَا/هُمْ/كُمْ/كَ/هُۥ
    # → فِعل ماضٍ، لا اسم. هَذا الفَحص الأَوَّل (قَبل أَيّ نَمَط جَمع)
    # لأَنّ كَلِمات مِثل أَخَذْنَا، أَرْسَلْنَا تَحوي ا في وَسَط plain
    # لَكِنّها جُزء مِن لاحِقَة نَا، لا مِن جَمع أَفْعَال.
    for plain_sfx, full_sfx in [("نا","نَا"),("كم","كُمْ"),("هم","هُمْ"),
                                ("ها","هَا"),("ك","كَ"),("ه","هُ")]:
        if plain.endswith(plain_sfx) and len(plain) - len(plain_sfx) >= 3:
            # نَبحَث عَن آخِر ظُهور لِأَوَّل حَرف مِن اللاحِقَة في الـsurface
            sfx_idx = token.rfind(full_sfx[0])
            if sfx_idx > 2:
                pre = token[max(0, sfx_idx-3):sfx_idx]
                # سُكون قَبل نَا/كُمْ → فِعل ماضٍ مُتَكَلِّم/مُخاطَب
                if pre.endswith("ْ") and plain_sfx in ("نا","كم"):
                    return False
                # فَتحَة قَبل أَيّ ضَمير → فِعل ماضٍ ثُلاثيّ سالِم
                if pre.endswith("َ"):
                    return False

    # نَمَط أَفْعَال (أَوْلَاد، أَصْحَاب، أَنبَاء، أَوْلِيَاء)
    # يَحوي ا في المَوقِع 4 أَو 5
    if "ا" in plain[3:6]:
        # تَأَكَّد أَنّ بِنيَة الـtoken لَيست فِعل أَمر (اف...)
        if not (token.startswith("أَ") and "ْ" in token[:5]):
            return True
        # حَتَّى لَو كانَ أَفعَل، لَو يَنتَهي بِـ ضَمير → اسم
        for sfx in ("هُمْ", "هُم", "هَا", "نَا", "كُمْ", "هُۥ", "ه"):
            if plain.endswith(_strip_all_marks(sfx)):
                return True
        # ا في الوَسَط → جَمع
        if "ا" in plain[2:5]:
            return True
    # نَمَط أَفعُل/أَفعِل + ضَمير (أَنفُسهم، أَهلهم، أَجرهم، أَيدِيهم)
    # في الـHafs Uthmani قَد لا يَكون السُّكون مَكتوبًا (أَنفُسُهُمْ)
    # مَنع: لَو الـbody قَبل الضَّمير يَنتَهي بِفَتحَة عَلى آخِر حَرف
    # → فِعل ماضٍ (أَخَذَ-هم، أَرسَلَ-هم) لا اسم
    for sfx_pair in [("هم","هُمْ"),("ها","هَا"),("نا","نَا"),("كم","كُمْ"),("هن","هُنَّ")]:
        plain_sfx, full_sfx = sfx_pair
        if plain.endswith(plain_sfx) and len(plain) >= 5:
            if token.startswith("أَ"):
                stem_plain_len = len(plain) - len(plain_sfx)
                if stem_plain_len >= 3:
                    # نَفحَص النَّمَط في الـsurface بَين أَ وَالضَّمير.
                    # نَستَخدِم rfind لأَنّ بَعض الكَلِمات تَحوي نَفس الحَرف
                    # قَبل الضَّمير (مَثَلًا أَنفُسِنَا فيها ن في الجِذع).
                    # عَلامَتا فِعل قَبل الضَّمير:
                    #   • فَتحَة (ـَ) قَبل ضَمير → ماضٍ ثُلاثيّ سالِم
                    #     (مَثَل: أَخَذَهُمْ)
                    #   • سُكون (ـْ) قَبل نَا/كُمْ → ماضٍ مُتَكَلِّم/مُخاطَب
                    #     (مَثَل: أَخَذْنَا، أَرْسَلْنَا، بَعَثْكُمْ)
                    body_pre_sfx_idx = token.rfind(full_sfx[0])
                    if body_pre_sfx_idx > 2:
                        # نَأخُذ الـ3 chars قَبل الضَّمير
                        pre = token[max(0, body_pre_sfx_idx-3):body_pre_sfx_idx]
                        if pre.endswith("َ"):
                            return False  # فَتحَة → ماضٍ
                        if pre.endswith("ْ") and plain_sfx in ("نا","كم"):
                            return False  # سُكون قَبل نَا/كُمْ → ماضٍ
                        # أَلِف مَقصورَة سُفليَّة (ٰ) أَو ى/ا قَبل الضَّمير:
                        # نَمَط ماضٍ مُعتَلّ ناقِص (أَحْيَٰهُمْ، هَدَىٰهُمْ، أَتَىٰكُمْ)
                        if pre.endswith(("ٰ","ى","ا")):
                            return False  # ماضٍ مُعتَلّ ناقِص + ضَمير
                    return True
    return False


def _is_definite_article_word(token: str, conj: str) -> bool:
    """يَتأَكَّد أَنّ الكَلِمَة تَبدَأ بِـ ال التَّعريف (مَع/بِدون عَطف).

    مَهَمّ: في «ٱلْحَقُّ»: ٱ+ل+ْ+ح+َ+ق+ُ+ّ → هَذه «ال» تَعريف، لَيست
    هَمزَة وَصل لِأَمر. الفَرق: ال التَّعريف لا تَتبَعها فِعل، بَل اسم.
    """
    if _starts_with_definite_article(token):
        return True
    if conj and _starts_with_definite_article_after_prefix(token, conj):
        return True
    return False


# ─────────────────────────────────────────────────────────────────
# Main gate
# ─────────────────────────────────────────────────────────────────

@dataclass
class OverrideResult:
    blocked: bool
    reason: str = ""
    override_class: str = ""  # ISM_MUARAB / HARF / ISM_MABNI / TAFDIL


def check_non_verb_override(token: str, *, body: str = "",
                            conj: str = "") -> OverrideResult:
    """يَفحَص هَل الـtoken مَحجوب مِن إِصدار Certificate كَفِعل.

    Args:
      token: الـsurface كامِل (مَع التَّشكيل)
      body:  الجِسم بَعد نَزع البادِئات (مِن prefix_stack)
      conj:  بادِئة العَطف (ف/و)

    إِذا لَم تُحَدَّد body/conj، نَستَنتِجهما تِلقائيًّا مِن بادِئة الـtoken
    (و، ف، ل) كَي يَعمَل tafdeel-check حَتَّى عَلى المُدخَلات الكامِلَة.

    Returns: OverrideResult(blocked, reason, override_class)
    """
    plain = _strip_diac(token)

    # auto-detect conj from token whenever conj wasn't supplied,
    # so callers passing body=token (full surface) still get tafdeel-check
    if not conj and token:
        if token.startswith(("وَ", "فَ")):
            conj = token[:2]
            if not body or body == token:
                body = token[2:]
        elif token.startswith(("و", "ف")) and len(token) >= 2:
            conj = token[:1]
            if not body or body == token:
                body = token[1:]
    if not body:
        body = token

    # 1. Closed-list override — أَدوات مَعروفَة
    if token in _KNOWN_NON_VERBS or plain in _KNOWN_NON_VERBS:
        return OverrideResult(
            blocked=True,
            reason=f"in known non-verbs list: {token}",
            override_class="HARF",
        )

    # 1.5 NominalSurfaceBlocker v3 (T) — تَنوين عَلى الـtoken = اسم قَطعًا
    # تَوصيَة المُستَخدِم 2026-05-25 (الجَلسَة 6):
    #   كِتَٰبٌ، مَّرْقُومٌ، رَسُولٌ، جَنَّاتٌ — التَّنوين دَليل اسم لا فِعل.
    if any(c in token for c in ("ٌ", "ٍ", "ً")):
        return OverrideResult(
            blocked=True,
            reason="tanwin (ـٌ/ـٍ/ـً) → indefinite noun, never verb",
            override_class="ISM_MUARAB",
        )

    # 1.55 RelativePronounClosedList v2 (W) — قَبل ال-check
    # تَوصيَة المُستَخدِم 2026-05-25 (الجَلسَة 6):
    #   ٱلَّذِينَ، ٱلَّذِى، ٱلَّتِى يَجِب أَن تَكون ISM_MAWSOOL قَبل
    #   أَيّ فَحص ال-التَّعريف العامّ.
    plain_rel = _strip_all_marks(_strong_normalize(token)).replace("ى","ي")
    _RELATIVE_PRONOUNS_PLAIN = {
        "الذي","التي","الذين","اللذان","اللذين","اللتان","اللتين",
        "اللاتي","اللائي","اللواتي","من","ما",
    }
    if plain_rel in _RELATIVE_PRONOUNS_PLAIN:
        return OverrideResult(
            blocked=True,
            reason=f"relative pronoun (closed list): {plain_rel}",
            override_class="ISM_MAWSOOL",
        )

    # 1.6 NominalSurfaceBlocker v3 (T-b) — جَمع تَكسير + ضَمير مَنصوب
    # أَمْوَٰلَكُمُ، أَموَالَهُم: نَمَط فَعَال + اللاحِقَة كَ المَفعول كَسرَة عَلى ل
    # ثُمَّ ضَمير مَفعول.
    # القَرينَة: ا في الوَسَط + ـكُمْ/ـكُم/ـهُمْ/ـهُم/ـهَا فَور.
    plain_check = _strip_all_marks(_strong_normalize(token))
    for sfx in ("كم","هم","ها","كن","هن","ك","ه"):
        if plain_check.endswith(sfx) and len(plain_check) >= 6:
            stem = plain_check[:-len(sfx)]
            # نَمَط فَعال/فُعال/أَفعال — اسم مَع ا في المَوقِع 2 أَو 3
            # تَطبيع شامِل يَضَع ا في مَكان أ/ٰ، فَالنَّمَط واضِح
            if "ا" in stem[1:5] and len(stem) >= 4:
                # تَمييز: لَو الـtoken في explicit_verbs_lexicon → فِعل
                try:
                    from explicit_verbs_contract import is_explicit_verb
                    if is_explicit_verb(token):
                        continue  # في lexicon الأَفعال → اسمَح
                except Exception:
                    pass
                # تَمييز إِضافيّ: لَو لاحِقَة ـكَ أَو ـه (مُفرَد قَصير) قَد تَكون
                # عَلى فِعل ماضٍ (أَصلَحَه). نَفحَص نَمَط ـَ قَبل اللاحِقَة:
                # فِعل ماضٍ: …َ-ـَ-سُفِكس (فَتحَتان مُتتاليَتان عَلى آخِر حَرفَين)
                # اسم: …+ا+حَرف ساكِن أَو حَرَكَة قَصيرَة + سُفِكس
                if sfx in ("ك","ه") and len(plain_check) < 6:
                    continue  # قَصير جِدًّا — مُحتَمَل فِعل
                return OverrideResult(
                    blocked=True,
                    reason=f"broken plural-like stem (mid-alif) + suffix {sfx} → noun",
                    override_class="JAMID",
                )

    # 1.7 ProperNounOverrideContract (U) — أَعلام
    # تَوصيَة المُستَخدِم 2026-05-25 (الجَلسَة 6):
    #   يَعْقُوبَ، إِسْمَٰعِيلَ، إِسْحَٰقَ، إِبْرَٰهِيمَ، مُوسَىٰ، عِيسَىٰ، يُوسُفَ
    #   مَعجَم صَريح، rule-based.
    _PROPER_NOUNS_PLAIN = _load_proper_nouns()
    # تَطبيع شامِل لِلـtoken لِلمُطابَقَة (إ/أ/ٰ/آ → ا)
    # تَطبيع أَوَّلًا (لِيُحَوَّل ٰ → ا) ثُمَّ نَزع التَّشكيل
    plain_pn_strong = _strip_all_marks(_strong_normalize(token))
    # نَزع و/ف/ل/ب/ك بادِئة
    if plain_pn_strong.startswith(("و", "ف", "ل", "ب", "ك")) and len(plain_pn_strong) > 4:
        stripped = plain_pn_strong[1:]
        if stripped in _PROPER_NOUNS_PLAIN:
            return OverrideResult(
                blocked=True,
                reason=f"proper noun with prefix: {stripped}",
                override_class="JAMID",
            )
    if plain_pn_strong in _PROPER_NOUNS_PLAIN:
        return OverrideResult(
            blocked=True,
            reason=f"proper noun (lexicon): {plain_pn_strong}",
            override_class="JAMID",
        )

    # 1.8 FunctionalNounBlocker (X) — غَيْرَ، قَبْلَ، بَعْدَ، بَيْنَ، عِندَ
    _FUNCTIONAL_NOUNS = _load_functional_nouns()
    plain_pn = _strip_all_marks(_normalize_alif(token))
    if (plain_pn in _FUNCTIONAL_NOUNS or token in _FUNCTIONAL_NOUNS
        or plain_pn_strong in _FUNCTIONAL_NOUNS):
        return OverrideResult(
            blocked=True,
            reason=f"functional noun (ظَرف/إِضافَة): {token}",
            override_class="ISM_MUARAB",
        )

    # 2. ال التَّعريف — اسم قَطعًا
    if _is_definite_article_word(token, conj):
        return OverrideResult(
            blocked=True,
            reason="definite article (ال) → nominal, never verb",
            override_class="ISM_MUARAB",
        )

    # 3. ـة (تاء مَربوطَة) — اسم مُؤَنَّث
    if _ends_with_taa_marbuta(token):
        return OverrideResult(
            blocked=True,
            reason="ends with ـة → feminine noun, never verb",
            override_class="ISM_MUARAB",
        )

    # 4. ـان/ـين بَعد جِسم اسميّ — مُثَنَّى
    if _ends_with_dual_marker(token):
        return OverrideResult(
            blocked=True,
            reason="ends with dual marker (ـان/ـين) → dual noun, never verb",
            override_class="ISM_MUARAB",
        )

    # 5. ـى أَلِف مَقصورَة بَدون بادِئة فِعليَّة قَويَّة → اسم
    if _ends_with_alif_maqsura(token):
        return OverrideResult(
            blocked=True,
            reason="ends with ـى → maqsura noun (likely tafdeel/maqsur)",
            override_class="ISM_MUARAB",
        )

    # 6. أَفْعَلُ بَعد عَطف → تَفضيل
    if body and _is_tafdeel_pattern(token, body):
        return OverrideResult(
            blocked=True,
            reason="أَفْعَلُ pattern (with/without conj) → tafdeel, never verb",
            override_class="ISM_MUARAB",
        )

    # 7. جُموع تَكسير أَفْعَال/أَفْعُل + ضَمير → اسم لا فِعل
    if _is_broken_plural_pattern(token):
        return OverrideResult(
            blocked=True,
            reason="أَفْعَال/أَفْعُل + suffix → broken plural noun, never verb",
            override_class="JAMID",
        )

    return OverrideResult(blocked=False)


# ─────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cases = [
        # (token, conj, body, expected_blocked)
        ("إِذَا", "", "إِذَا", True),
        ("كَمَا", "", "كَمَا", True),
        ("ٱلْحَقُّ", "", "ٱلْحَقُّ", True),
        ("وَٱمْرَأَتَانِ", "وَ", "ٱمْرَأَتَانِ", True),
        ("ٱلْأُخْرَىٰ", "", "ٱلْأُخْرَىٰ", True),
        ("أَجَلِهِ", "", "أَجَلِهِ", False),  # might still be blocked by other paths
        ("أَقْسَطُ", "", "أَقْسَطُ", True),
        ("وَأَقْوَمُ", "وَ", "أَقْوَمُ", True),
        ("وَأَدْنَىٰٓ", "وَ", "أَدْنَىٰٓ", True),
        ("لِلشَّهَٰدَةِ", "لِ", "الشَّهَٰدَةِ", True),  # ال after لِ
        # Verbs — should NOT be blocked
        ("كَتَبَ", "", "كَتَبَ", False),
        ("يَكْتُبُ", "", "يَكْتُبُ", False),
        ("فَلْيَكْتُبْ", "فَ", "يَكْتُبْ", False),
        ("وَٱتَّقُوا", "وَ", "ٱتَّقُوا", False),
        ("فَلَيْسَ", "فَ", "لَيْسَ", False),
        ("كَانَ", "", "كَانَ", False),
        ("يَكْتُبَانِ", "", "يَكْتُبَانِ", False),  # IV dual — should NOT block
    ]
    print(f"{'token':<22} {'expected':<10} {'got':<10} {'reason'}")
    print("-" * 90)
    for tok, conj, body, exp in cases:
        r = check_non_verb_override(tok, body=body, conj=conj)
        mark = "✓" if r.blocked == exp else "✗"
        exp_str = "BLOCK" if exp else "PASS"
        got_str = "BLOCK" if r.blocked else "PASS"
        print(f"{mark} {tok:<20} {exp_str:<10} {got_str:<10} {r.reason}")
