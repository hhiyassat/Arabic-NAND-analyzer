"""Layer 2 — Case + Mark classifier.

Given a sentence's tokens (already Layer-1 classified), assign each token:
  - case_id  (1=مرفوع, 2=منصوب, 3=مجرور, 4=مجزوم, 5=مبني)
  - mark_id  (1..14 from i3rab_marks.csv)

Rules (priority order — first match wins, each carries a source_of_claim):

  HARF / ISM_MABNI / JALALAH (kullha مَبْنِي):
    → case_id = 5 (مَبْنِي)
    → mark from final diacritic of the surface

  FIIL:
    ماضٍ (PV)        → مَبْنِي على الفتح / الضم / السكون (per surface ending)
    أمر (CV)         → مَبْنِي على السكون / حذف النون / حذف حرف العلة
    مضارع (IV):
      - default                → مَرْفُوع، علامة الضمة
      - if preceded by HARF_NASB (أن، لن، كي، ...) → مَنْصُوب، علامة الفتحة
      - if preceded by HARF_JAZM (لم، لا الناهية، إن الشرطية) → مَجْزُوم، علامة السكون / حذف النون

  ISM_MUARAB / JAMID / AALAM:
    - after HARF_JARR → مَجْرُور، علامة الكسرة (default) / الياء (جمع مذكر سالم / مثنى)
    - after إنّ/أنّ/كأنّ/لكنّ/لعلّ/ليت → مَنْصُوب
    - after كان/أصبح/صار وأخواتها (when detected) → اسم مرفوع
    - default: case derived from final diacritic:
        ُ → مَرْفُوع (ضمة)
        ٌ → مَرْفُوع (ضمة + تنوين)
        َ → مَنْصُوب (فتحة)
        ً → مَنْصُوب (فتحة + تنوين)
        ِ → مَجْرُور (كسرة)
        ٍ → مَجْرُور (كسرة + تنوين)
        ون → مَرْفُوع علامته الواو (جمع مذكر سالم)
        ين → مَنْصُوب/مَجْرُور علامته الياء
        ان → مَرْفُوع علامته الألف (مثنى)
        ات → جمع مؤنث سالم — مَرْفُوع ضمة / مَنْصُوب كسرة
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CLEAN_CODE = _HERE.parent
sys.path.insert(0, str(_CLEAN_CODE))

from wazn_data import DIACRITICS  # type: ignore

_DIAC = set(DIACRITICS)


def _strip_diac(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIAC)


def _last_significant_diac(token: str) -> str:
    """Return the LAST diacritic in the token (the one carrying the case
    marker if it's a declinable noun/verb). Skips trailing letters that
    don't carry a vowel."""
    # Walk from end: skip silent letters (ـ), find first diacritic.
    for c in reversed(token):
        if c in _DIAC:
            return c
        # Stop at non-diacritic, non-letter (no further useful info)
        # Actually we should NOT stop on letters — case marker is on the
        # last letter's vowel. So scan backwards finding the last vowel.
    return ""


def _last_vowel_before_index(token: str, idx: int) -> str:
    """Find the last vowel diacritic before position idx."""
    for i in range(idx - 1, -1, -1):
        if token[i] in _DIAC:
            return token[i]
    return ""


def _detect_case_from_ending(token: str) -> tuple[int, int, str, str]:
    """Return (case_id, mark_id, reason, tanwin) from the surface ending.

    ``tanwin`` is one of "ضم"/"فتح"/"كسر"/"" depending on the final
    diacritic. Empty if no tanwin.

    Handles the common patterns:
      - Trailing ون / ين / ان / ات (with diacritics)
      - Trailing tanwin (ٌ/ٍ/ً)
      - Trailing case vowel (ُ/ِ/َ)
    """
    plain = _strip_diac(token)
    last_vowel = _last_significant_diac(token)

    # Plural / dual endings — صيغ موحَّدة بالعربيّة
    if plain.endswith("ون") and len(plain) >= 3:
        return 1, 3, "الواو — جمع مذكّر سالم مرفوع", ""
    if plain.endswith("ين") and len(plain) >= 3:
        return 3, 7, "الياء — جمع مذكّر سالم أو مثنّى (نصب/جر)", ""
    if plain.endswith("ان") and len(plain) >= 3:
        return 1, 2, "الألف — مثنّى مرفوع", ""
    if plain.endswith("ات") and len(plain) >= 3:
        if last_vowel == "ُ":
            return 1, 1, "الضمّة — جمع مؤنّث سالم مرفوع", ""
        if last_vowel == "ٌ":
            return 1, 1, "تنوين الضمّ — جمع مؤنّث سالم مرفوع", "ضم"
        if last_vowel == "ٍ" or last_vowel == "ِ":
            why = "تنوين الكسر" if last_vowel == "ٍ" else "الكسرة"
            return 3, 6, f"{why} — جمع مؤنّث سالم مجرور", \
                   ("كسر" if last_vowel == "ٍ" else "")
        if last_vowel == "ً" or last_vowel == "َ":
            why = "تنوين الفتح" if last_vowel == "ً" else "الفتحة"
            return 2, 10, f"{why} — جمع مؤنّث سالم منصوب (الكسرة نائبة)", \
                   ("فتح" if last_vowel == "ً" else "")

    # تنوين الحركات — نصّ موحَّد «X المنوّنة» مع تَسجيل التنوين كحقل مستقلّ
    if last_vowel == "ٌ":
        return 1, 1, "تنوين الضمّ → مرفوع", "ضم"
    if last_vowel == "ً":
        return 2, 4, "تنوين الفتح → منصوب", "فتح"
    if last_vowel == "ٍ":
        return 3, 6, "تنوين الكسر → مجرور", "كسر"

    # حركات مفردة (بدون تنوين)
    if last_vowel == "ُ":
        return 1, 1, "الضمّة → مرفوع", ""
    if last_vowel == "َ":
        return 2, 4, "الفتحة → منصوب", ""
    if last_vowel == "ِ":
        return 3, 6, "الكسرة → مجرور", ""
    if last_vowel == "ْ":
        return 4, 8, "السكون → مجزوم/مبني", ""

    return 0, 0, "لا علامة إعرابيّة في النهاية", ""


def _mabni_mark_from_ending(token: str) -> tuple[int, str]:
    """For مَبْنِي words: mark says 'مبني على ...' which doesn't fit the
    14 marks table cleanly. We map to the closest case-aware mark when
    possible. Returns (mark_id_or_0, mark_text)."""
    last = _last_significant_diac(token)
    if last == "َ":
        return 0, "مَبْنِي عَلَى الْفَتْحِ"
    if last == "ُ":
        return 0, "مَبْنِي عَلَى الضَّمِّ"
    if last == "ِ":
        return 0, "مَبْنِي عَلَى الْكَسْرِ"
    if last == "ْ":
        return 0, "مَبْنِي عَلَى السُّكُونِ"
    if last == "ّ":
        return 0, "مَبْنِي عَلَى الْفَتْحِ (مشدد)"
    return 0, "مَبْنِي"


# Particles whose ROLE affects the FOLLOWING token's case
# (very small starter set — extend via i3rab_operators.csv later)
_HARF_JARR_KIND = "HARF_JARR"          # → ism majroor
_HARF_NASB_KIND = "HARF_NASB"          # → fi'l mudari mansoob
_HARF_JAZM_KIND = "HARF_JAZM"          # → fi'l mudari majzoom


class CaseMarkClassifier:
    """Assign case + mark per token with proof-theoretic metadata.

    Per 14_Minimal_Complete_Theory.md, each decision carries kind/contract.
    Kind assignment policy:
      Certificate — لـ HARF/ISM_MABNI/PV (المبني حُكْم لازم)؛
                    + اسم سُبِق بـ HARF_JARR قَطْعِيّ (السياق محسوم).
      Hypothesis  — استدلال بالحركة الأخيرة (قد يُغيِّر السياقُ الحكمَ).
      Zero        — لا حركة في النهاية ولا سياق يحسم.
    """

    def __init__(self) -> None:
        pass

    def _set(self, t, *, case_id, mark_id, source, kind, contract,
             blockers=None, alternatives=None, tanwin=""):
        """Assign all case/mark + proof + tanwin fields in one call."""
        t.case_id = case_id
        t.mark_id = mark_id
        t.case_source = source
        t.case_kind = kind
        t.case_contract = contract
        t.tanwin = tanwin
        if blockers:
            t.case_blockers = list(blockers)
        if alternatives:
            t.case_alternatives = list(alternatives)

    def classify_sentence(self, sent) -> None:
        tokens = sent.tokens
        for i, t in enumerate(tokens):
            prev = tokens[i - 1] if i > 0 else None

            # === HARF / ISM_MABNI → مَبْنِي (Certificate) ===
            if t.word_class in {"HARF", "ISM_MABNI"}:
                _, txt = _mabni_mark_from_ending(t.token)
                self._set(
                    t,
                    case_id=5, mark_id=None,
                    source=f"layer1:{t.word_class}_is_mabni",
                    kind="Certificate",
                    contract=f"mabni_by_class:{t.word_class}",
                )
                t.notes.append(txt)
                continue

            # === JALALAH → معرب، حالة من الحركة (Hypothesis) ===
            if t.word_class == "JALALAH":
                case_id, mark_id, why, tanwin = _detect_case_from_ending(t.token)
                if case_id:
                    self._set(
                        t,
                        case_id=case_id, mark_id=mark_id,
                        source=why,
                        kind="Hypothesis",
                        contract="case_by_final_diacritic",
                        tanwin=tanwin,
                    )
                else:
                    self._set(
                        t,
                        case_id=None, mark_id=None,
                        source="jalalah_no_ending_marker",
                        kind="Zero",
                        contract="case_by_final_diacritic",
                        blockers=["no_final_vowel_on_token"],
                    )
                continue

            # === FIIL ===
            if t.word_class == "FIIL":
                if t.verb_aspect == "PV":
                    last = _last_significant_diac(t.token)
                    if last == "َ":
                        src = "PV:mabni_ala_fath"
                    elif last == "ُ":
                        src = "PV:mabni_ala_damm (مع واو الجماعة)"
                    elif last == "ْ":
                        src = "PV:mabni_ala_sukoon (مع ضمير رفع)"
                    else:
                        src = "PV:mabni"
                    self._set(
                        t, case_id=5, mark_id=None, source=src,
                        kind="Certificate",
                        contract="PV_is_mabni",
                    )
                    continue

                if t.verb_aspect == "CV":
                    self._set(
                        t, case_id=5, mark_id=None, source="CV:mabni",
                        kind="Certificate",
                        contract="CV_is_mabni",
                    )
                    continue

                # IV (مضارع) — السياق يحدّد
                prev_kind = prev.closed_class_kind if prev else ""
                if prev_kind == _HARF_NASB_KIND:
                    self._set(
                        t,
                        case_id=2, mark_id=4,
                        source=f"IV+prev_HARF_NASB({prev.token if prev else ''})",
                        kind="Certificate",
                        contract=f"IV_after_HARF_NASB:{prev.token if prev else ''}",
                    )
                elif prev_kind == _HARF_JAZM_KIND:
                    self._set(
                        t,
                        case_id=4, mark_id=8,
                        source=f"IV+prev_HARF_JAZM({prev.token if prev else ''})",
                        kind="Certificate",
                        contract=f"IV_after_HARF_JAZM:{prev.token if prev else ''}",
                    )
                else:
                    # IV الافتراضي مرفوع — Hypothesis لأنّ السياق الأبعد
                    # قد يغيّر الحكم (إن لم نُغطِّ كل أدوات النصب/الجزم)
                    plain = _strip_diac(t.token)
                    if plain.endswith("ون") or plain.endswith("ان"):
                        mid = 13
                        src = "IV:default_marfu (أفعال خمسة — ثبوت النون)"
                    else:
                        mid = 1
                        src = "IV:default_marfu (ضمة)"
                    self._set(
                        t, case_id=1, mark_id=mid, source=src,
                        kind="Hypothesis",
                        contract="IV_default_marfu",
                        blockers=["may_be_governed_by_unseen_particle"],
                        alternatives=[
                            {"case_id": 2, "reason": "if_preceded_by_unseen_HARF_NASB"},
                            {"case_id": 4, "reason": "if_preceded_by_unseen_HARF_JAZM"},
                        ],
                    )
                continue

            # === ISM_MUARAB / JAMID / AALAM → معرب ===
            if t.word_class in {"ISM_MUARAB", "JAMID", "AALAM"}:
                # سُبق بحرف جر → مجرور (Certificate — السياق قاطع)
                if prev and prev.closed_class_kind == _HARF_JARR_KIND:
                    plain = _strip_diac(t.token)
                    last = _last_significant_diac(t.token)
                    # تَحقّق من تنوين الكسر على آخر الكلمة
                    tanwin = "كسر" if last == "ٍ" else ""
                    if plain.endswith("ين") or plain.endswith("ون"):
                        mid = 7  # الياء
                    elif plain.endswith("ات"):
                        mid = 6  # الكسرة
                    else:
                        mid = 6
                    self._set(
                        t, case_id=3, mark_id=mid,
                        source=f"ism+prev_HARF_JARR({prev.token})",
                        kind="Certificate",
                        contract=f"ism_after_HARF_JARR:{prev.token}",
                        tanwin=tanwin,
                    )
                    continue
                # غير ذلك: نستدلّ من الحركة (Hypothesis)
                case_id, mark_id, why, tanwin = _detect_case_from_ending(t.token)
                if case_id:
                    self._set(
                        t,
                        case_id=case_id, mark_id=mark_id,
                        source=why,
                        kind="Hypothesis",
                        contract="case_by_final_diacritic",
                        tanwin=tanwin,
                        alternatives=[
                            {"case_id": 2, "reason": "may_be_mafool_bih_overriding_ending"},
                            {"case_id": 1, "reason": "may_be_faail_overriding_ending"},
                        ] if case_id == 3 else [],
                    )
                else:
                    self._set(
                        t,
                        case_id=None, mark_id=None,
                        source="unknown_ending",
                        kind="Zero",
                        contract="case_by_final_diacritic",
                        blockers=["no_final_vowel_no_context_signal"],
                    )
                continue

            # === UNKNOWN — best-effort then Zero ===
            case_id, mark_id, why, tanwin = _detect_case_from_ending(t.token)
            if case_id:
                self._set(
                    t, case_id=case_id, mark_id=mark_id,
                    source=f"فئة مجهولة: {why}",
                    kind="Hypothesis",
                    contract="case_by_final_diacritic_unknown_class",
                    tanwin=tanwin,
                    blockers=["word_class_unknown"],
                )
            else:
                self._set(
                    t, case_id=None, mark_id=None,
                    source="unknown_class+no_ending",
                    kind="Zero",
                    contract="no_case_signal",
                    blockers=["word_class_unknown", "no_ending"],
                )


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    from .layer1 import WordClassClassifier
    from .types import SentenceI3rab, TokenI3rab, CASE_IDS, MARK_IDS

    clf1 = WordClassClassifier()
    clf2 = CaseMarkClassifier()

    # Fatiha-style mini-sentences
    sentences = [
        "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ",
        "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
        "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ",
        "اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ",
        "ذَلِكَ الْكِتَابُ لَا رَيْبَ فِيهِ",
        "إِنَّ اللَّهَ غَفُورٌ رَحِيمٌ",
        "لَنْ يَكْتُبَ الْمُسْلِمُونَ",
        "لَمْ يَكْتُبْ أَحَدٌ",
    ]
    for text in sentences:
        print(f"\n=== {text} ===")
        sent = SentenceI3rab(text=text)
        for i, tok in enumerate(text.split()):
            ti = TokenI3rab(token=tok, position=i)
            r1 = clf1.classify(tok)
            ti.word_class = r1["word_class"]
            ti.word_class_source = r1["source"]
            ti.closed_class_kind = r1["closed_class_kind"]
            ti.verb_aspect = r1["verb_aspect"]
            ti.root = r1["root"]
            ti.wazn = r1["wazn"]
            sent.tokens.append(ti)
        clf2.classify_sentence(sent)
        for t in sent.tokens:
            case_name = CASE_IDS.get(t.case_id, "—") if t.case_id else "—"
            mark_name = MARK_IDS[t.mark_id][0] if t.mark_id else "—"
            print(
                f"  {t.token:<20} class={t.word_class:<11} "
                f"case={case_name:<8} mark={mark_name:<12} "
                f"src={t.case_source}"
            )
