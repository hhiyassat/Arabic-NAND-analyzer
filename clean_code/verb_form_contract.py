"""verb_form_contract.py — عَقد إِصدار «هَذا فِعل».

السُّؤال الذي يَجيب عَنه:
  «هَل لَدَيَّ بُرهان كاف عَلى أَنّ هَذا الـtoken فِعل،
   بِغَضّ النَّظَر عَمّا تَقوله القَوائم المُغلَقَة؟»

ثَلاث طَبَقات داخِليَّة:

  1. PrefixStackParser    — يَنزِع ف+لـ+يَ المُتَكَدِّسَة (فَلْيَكْتُبْ)
  2. MoodDetector         — يَكشِف الجَزم/الأَمر/المُضارِع مِن البُنية
  3. MorphFeatures        — يُعَيِّن aspect/person/number/gender/mood

النَّتيجَة: VerbVerdict(kind ∈ {Certificate, Hypothesis, Zero}, …).

سِياسات صارِمَة:
  • الفَتوى الإيجابيَّة (Certificate) تَستَلزِم:
      – بُنية واضِحَة (بادِئة فِعل + جِسم فِعل + لاحِقَة مُتَّسِقَة)
      – أَو وُجود في kana_family.csv
  • Hypothesis: قَرائن غامِضَة
  • Zero: لا قَرائن

كُلّ القَواعد في data/contracts/lists/kana_family.csv —
لا inline rules.

تَوصيَة المُستَخدِم: «يُعطي أَكبَر تَحسين في كامِل سِلسِلَة البُرهان».
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

VerdictKind = Literal["Certificate", "Hypothesis", "Zero"]
Aspect = Literal["PV", "IV", "CV", ""]
Mood = Literal["INDIC", "JUSS", "SUBJ", "IMPER", ""]

_HERE = Path(__file__).resolve().parent
_KANA_CSV = _HERE / "data" / "contracts" / "lists" / "kana_family.csv"

_DIACRITICS = set("ًٌٍَُِّْٰـ")


def _strip_diac(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIACRITICS)


def _normalize_alif(s: str) -> str:
    """ٱ (همزة وصل) → ا — كَي يَتَّفِق التَّحليل مَع المُعجم."""
    return (s or "").replace("ٱ", "ا")


# ─────────────────────────────────────────────────────────────────
# Lexicon loader (kana family)
# ─────────────────────────────────────────────────────────────────

_KANA_LEX: dict[str, dict] = {}  # surface (with diac) → row
_KANA_LEX_PLAIN: dict[str, dict] = {}  # surface stripped → row


def _load_kana_lex() -> None:
    if _KANA_LEX:
        return
    if not _KANA_CSV.is_file():
        return
    with _KANA_CSV.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            surf = (row.get("surface") or "").strip()
            if not surf:
                continue
            _KANA_LEX[surf] = row
            _KANA_LEX_PLAIN[_strip_diac(surf)] = row


# ─────────────────────────────────────────────────────────────────
# Audit
# ─────────────────────────────────────────────────────────────────

_AUDIT = {
    "candidates_seen": 0,
    "certificate": 0,
    "hypothesis": 0,
    "zero": 0,
    "by_path": {},
    "blockers_count": 0,
}


def reset_audit() -> None:
    _AUDIT["candidates_seen"] = 0
    _AUDIT["certificate"] = 0
    _AUDIT["hypothesis"] = 0
    _AUDIT["zero"] = 0
    _AUDIT["by_path"] = {}
    _AUDIT["blockers_count"] = 0


def get_audit() -> dict:
    return dict(_AUDIT)


# ─────────────────────────────────────────────────────────────────
# Sub-contract 1 — PrefixStackParser
# ─────────────────────────────────────────────────────────────────

@dataclass
class PrefixStack:
    """يَنزِع البادِئات المُتَكَدِّسَة قَبل جِسم الفِعل.

    البادِئات المَدعومَة (بِالتَّرتيب):
      • ف / فَ      — حَرف عَطف/استئناف
      • و / وَ      — حَرف عَطف
      • ل / لِ      — لام الأَمر (تَجزِم المُضارِع)
      • س / سَ      — السِّين (تَنفيس)
      • أ / أَ      — هَمزَة الِاستِفهام (لَيست بادِئة فِعليَّة)
    """
    raw: str
    conj: str = ""       # ف / و
    lam_amr: str = ""    # ل (لام الأَمر)
    saa: str = ""        # س
    body: str = ""       # ما تَبَقَّى

    @property
    def has_lam_amr(self) -> bool:
        return bool(self.lam_amr)

    @property
    def has_conj(self) -> bool:
        return bool(self.conj)


def parse_prefix_stack(token: str) -> PrefixStack:
    """يَنزِع ف/و + لِ + س مِن بِدايَة الـtoken."""
    s = _normalize_alif(token)
    stack = PrefixStack(raw=token)

    # 1. ف/و (حَرف عَطف/استئناف)
    if s.startswith(("فَ", "وَ")):
        stack.conj = s[:2]
        s = s[2:]
    elif s.startswith(("ف", "و")) and len(s) >= 2 and s[1] not in _DIACRITICS:
        stack.conj = s[:1]
        s = s[1:]

    # 2. لِ / لْ (لام الأَمر — تَكون بِسُكون أَو كَسرَة)
    if s.startswith(("لْ", "لِ")):
        stack.lam_amr = s[:2]
        s = s[2:]
    elif s.startswith("ل") and len(s) >= 2 and s[1] in {"ْ", "ِ"}:
        stack.lam_amr = s[:2]
        s = s[2:]

    # 3. سَ / س (تَنفيس — لِلمُضارِع فَقَط)
    if s.startswith(("سَ",)):
        stack.saa = s[:2]
        s = s[2:]

    stack.body = s
    return stack


# ─────────────────────────────────────────────────────────────────
# Sub-contract 2 — MoodDetector
# ─────────────────────────────────────────────────────────────────

@dataclass
class MoodResult:
    aspect: Aspect = ""
    mood: Mood = ""
    evidence: list[str] = field(default_factory=list)


_IV_PREFIXES_DIAC = ("يَ", "يُ", "تَ", "تُ", "نَ", "نُ", "أَ", "أُ")
_IV_PREFIXES_PLAIN = ("ي", "ت", "ن", "أ")


def detect_mood(body: str, *, has_lam_amr: bool) -> MoodResult:
    """يَكشِف الجَهَة (aspect) + المَود (mood) مِن جِسم الفِعل بَعد البادِئات.

    اعتِمادًا عَلى:
      • بادِئة مُضارِع (يَ/تَ/نَ/أَ) → IV
      • همزَة وَصل + سُكون → PV (افْعَل/استَفْعَل) أَو CV (اكْتُبْ)
      • سُكون نِهائيّ + lam_amr → JUSS (مَجزوم أَمر)
      • سُكون نِهائيّ بِدون lam_amr → JUSS (مَجزوم بِلَم/لَن…)
      • فَتحَة نِهائيَّة عَلى ع → PV غالِبًا
    """
    res = MoodResult()
    if not body:
        return res

    plain = _strip_diac(body)
    if len(plain) < 2:
        return res

    # PATCH 2D (2026-05-26) — Form V/VI past pre-check.
    # تَفَعَّلَ (V) and تَفَاعَلَ (VI) past forms start with تَ — which the
    # IV-prefix check below would otherwise classify as imperfect. When the
    # verb ENDS in an unambiguous past-2nd-person subject suffix (تُمْ /
    # تُمَا / تُنَّ), the verb is unambiguously past, not imperfect.
    # Targets from Quran 2:282: تَدَايَنْتُمْ, تَبَايَعْتُمْ.
    # Coordinated with segmenter.py PATCH 2C which blocks IMPERF_PREF in
    # the same situation; this gate ensures the L3 aspect verdict matches.
    if (body.startswith(_IV_PREFIXES_DIAC)
            and body[:1] == "ت"  # only تَ-initial (Form V/VI signature)
            and any(plain.endswith(suf) for suf in ("تم", "تما", "تن"))
            and len(plain) >= 4):  # at least تَ + 2 consonants + past suffix
        res.aspect = "PV"
        res.evidence.append(
            "PATCH 2D Form V/VI past (تَ-initial + past-2p suffix تم/تما/تن)"
        )
        return res

    # IV (مُضارِع)
    if body.startswith(_IV_PREFIXES_DIAC) and len(plain) >= 3:
        res.aspect = "IV"
        res.evidence.append(f"IV prefix: {body[:2]}")
        # mood
        if has_lam_amr:
            res.mood = "JUSS"
            res.evidence.append("with lam_amr → jussive")
            return res
        # لاحِقَة ـونَ / ـينَ / ـانِ → الأَفعال الخَمسَة مَرفوعَة (INDIC)
        if (body.endswith("ونَ") or body.endswith("ينَ")
            or body.endswith("انِ")):
            res.mood = "INDIC"
            res.evidence.append("five-verbs indicative ending")
            return res
        # لاحِقَة ـوا / ـي / ـا (مَجزوم أَو مَنصوب — حَذف النّون)
        if (body.endswith("وا") or body.endswith("ي")
            or (body.endswith("ا") and not body.endswith("نَا"))):
            res.mood = "JUSS"  # غالِبًا مَجزوم/مَنصوب
            res.evidence.append("five-verbs noon-deleted")
            return res
        # نِهايَة سُكون عَلى آخِر حَرف → JUSS
        if body.endswith("ْ"):
            res.mood = "JUSS"
            res.evidence.append("body ends with sukun → jussive")
        elif body.endswith("َ"):
            # فَتحَة عَلى آخِر حَرف فَقَط (لَيس ـونَ) → SUBJ
            res.mood = "SUBJ"
            res.evidence.append("body ends with fatha → subjunctive")
        elif body.endswith("ُ"):
            res.mood = "INDIC"
            res.evidence.append("body ends with damma → indicative")
        else:
            res.mood = "INDIC"
            res.evidence.append("default indicative")
        return res

    # CV (أَمر) — يَبدَأ بِـ هَمزَة وَصل + سُكون أَو شَدّة
    # مَثَل: اكْتُبْ، اقْرَأْ، استَخْرِجْ، اتَّقُوا
    if plain.startswith("ا") and len(plain) >= 3:
        # هَمزَة وَصل + سُكون (الأَمر العادي)
        if len(body) >= 4 and "ْ" in body[:4]:
            res.aspect = "CV"
            res.mood = "IMPER"
            res.evidence.append("hamzat wasl + sukun → imperative")
            return res
        # هَمزَة وَصل + ت + شَدّة → form VIII (افتَعَل / اتَّفَعَل) — قَد يَكون أَمر أَو ماضٍ
        if (len(body) >= 4 and "ّ" in body[:5]
            and plain[:2] in ("ات", "اث", "اد", "اذ", "از", "اس")):
            # اتَّقُوا → أَمر بِلاحِقَة وا
            if body.endswith("وا"):
                res.aspect = "CV"
                res.mood = "IMPER"
                res.evidence.append("form VIII imperative with shadda + وا")
            else:
                res.aspect = "PV"
                res.evidence.append("form VIII perfect with shadda")
            return res
        # هَمزَة وَصل لِلماضي: استَفْعَل، انفَعَل، افتَعَل
        if plain.startswith(("است", "انف", "افت")) and len(plain) >= 5:
            res.aspect = "PV"
            res.mood = ""
            res.evidence.append(f"hamzat wasl perfect: {plain[:3]}")
            return res

    # PV passive plural — فُعُوا/فُعِلُوا (دُعُوا، قُتِلُوا، أُخْرِجُوا، نُودُوا)
    # نَمَط: C + ضَمَّة + (C? + ضَمَّة/كَسرَة) + و + ا
    if (len(body) >= 5 and body[0] not in _DIACRITICS
        and body[1] == "ُ"  # ضَمَّة عَلى الأَوَّل (passive marker)
        and body.endswith("وا")):
        # body has at least 3 letters and ends in وا
        body_plain_chk = _strip_diac(body)
        if len(body_plain_chk) >= 3 and body_plain_chk[1] not in {"ت","ن"}:
            # ليس فِعل ماضٍ مَع لاحِقَة تُمْ/نا
            res.aspect = "PV"
            res.evidence.append(f"passive PV plural (فُعُوا pattern): {body}")
            return res

    # PV — يَبدَأ بِفَتحَة + حَرف ثاني بِفَتحَة (كَتَبَ، فَعَلَ)
    # نَطلُب 3 حُروف صَحيحَة + ≥3 حَرَكات. ما يَحوي ا/ى/ي/و كَحَرف ثاني/ثالِث
    # غالِبًا اسم (إِذَا، كَمَا)، لا فِعل.
    plain_body = _strip_diac(body)
    if len(plain_body) >= 3:
        # نَستَثني الحالات التي تَحوي مُدودًا (madd letters) في الجِسم
        if len(plain_body) == 3 and plain_body[2] in {"ا", "ى", "و", "ي"}:
            return res
        # form II PV (فَعَّلَ): C+vowel+C+shadda+vowel+C+vowel
        # عَلَّمَ، كَلَّمَ، نَزَّلَ — مَع/بِدون لاحِقَة ضَمير
        if (len(body) >= 6 and body[0] not in _DIACRITICS
            and body[1] in {"َ", "ُ", "ِ"}
            and "ّ" in body[3:5]
            and plain_body[1] not in {"ا", "ى"}
        ):
            res.aspect = "PV"
            res.evidence.append("form II PV with shadda")
            return res
        # كَتَبَ: ك+َ+ت+َ+ب+َ = 6 chars، نَطلُب حَرَكات عَلى مَواقِع
        # الحُروف الـ3 الأَولى
        if len(body) >= 6 and body[0] not in _DIACRITICS:
            if (body[1] in {"َ", "ُ", "ِ"}
                and body[3] in {"َ", "ُ", "ِ", "ْ"}
                and len(body) >= 5 and body[5] in {"َ", "ُ", "ِ"}
                and plain_body[1] not in {"ا", "ى"}
            ):
                res.aspect = "PV"
                res.evidence.append("CCC vowel pattern → past")
                return res

    return res


# ─────────────────────────────────────────────────────────────────
# Sub-contract 3 — MorphFeatures
# ─────────────────────────────────────────────────────────────────

@dataclass
class MorphFeatures:
    aspect: Aspect = ""
    mood: Mood = ""
    person: str = ""     # 1st / 2nd / 3rd
    number: str = ""     # SG / DU / PL
    gender: str = ""     # M / F
    evidence: list[str] = field(default_factory=list)


_PV_SUFFIX_FEATURES = {
    "تُ":      ("1", "SG", ""),    # كَتَبْتُ
    "نَا":     ("1", "PL", ""),    # كَتَبْنَا
    "تَ":      ("2", "SG", "M"),   # كَتَبْتَ
    "تِ":      ("2", "SG", "F"),   # كَتَبْتِ
    "تُمَا":   ("2", "DU", ""),   # كَتَبْتُمَا
    "تُمْ":    ("2", "PL", "M"),   # كَتَبْتُمْ
    "تُنَّ":   ("2", "PL", "F"),   # كَتَبْتُنَّ
    "ا":       ("3", "DU", "M"),   # كَتَبَا
    "تَا":     ("3", "DU", "F"),   # كَتَبَتَا
    "وا":      ("3", "PL", "M"),   # كَتَبُوا
    "نَ":      ("3", "PL", "F"),   # كَتَبْنَ
    "تْ":      ("3", "SG", "F"),   # كَتَبَتْ
}


def extract_features(token: str, *, prefix: PrefixStack,
                     mood_res: MoodResult) -> MorphFeatures:
    """يَستَخرِج الـperson/number/gender مِن اللَّاحِقَة."""
    feat = MorphFeatures(aspect=mood_res.aspect, mood=mood_res.mood)
    body = prefix.body
    if not body:
        return feat

    # PV suffixes — تَرتيب الأَطول أَوَّلًا
    if feat.aspect == "PV":
        for sfx in sorted(_PV_SUFFIX_FEATURES.keys(), key=len, reverse=True):
            if body.endswith(sfx):
                p, n, g = _PV_SUFFIX_FEATURES[sfx]
                feat.person, feat.number, feat.gender = p, n, g
                feat.evidence.append(f"PV suffix: {sfx} → {p}/{n}/{g}")
                break
        else:
            feat.person, feat.number, feat.gender = "3", "SG", "M"
            feat.evidence.append("default PV: 3/SG/M")

    # IV — نَستَدِلّ مِن البادِئة
    elif feat.aspect == "IV":
        plain = _strip_diac(body)
        if plain.startswith("ي"):
            feat.person = "3"
            feat.gender = "M"
        elif plain.startswith("ت"):
            feat.person = "2"  # أَو 3 مُؤَنَّث
        elif plain.startswith("ن"):
            feat.person = "1"
            feat.number = "PL"
        elif plain.startswith("أ"):
            feat.person = "1"
            feat.number = "SG"
        # number from suffix
        if body.endswith("ون") or body.endswith("ونَ"):
            feat.number = "PL"
            feat.gender = "M"
        elif body.endswith("وا"):
            feat.number = "PL"
            feat.gender = "M"
        elif body.endswith("نَ"):
            feat.number = "PL"
            feat.gender = "F"
        elif body.endswith("ان") or body.endswith("انِ"):
            feat.number = "DU"
        if not feat.number:
            feat.number = "SG"
        feat.evidence.append(f"IV: {feat.person}/{feat.number}/{feat.gender}")

    # CV (أَمر)
    elif feat.aspect == "CV":
        feat.person = "2"
        if body.endswith("وا"):
            feat.number = "PL"
            feat.gender = "M"
        elif body.endswith("نَ"):
            feat.number = "PL"
            feat.gender = "F"
        elif body.endswith("ا"):
            feat.number = "DU"
        elif body.endswith("ي"):
            feat.number = "SG"
            feat.gender = "F"
        else:
            feat.number = "SG"
            feat.gender = "M"
        feat.evidence.append(f"CV: 2/{feat.number}/{feat.gender}")

    return feat


# ─────────────────────────────────────────────────────────────────
# Main contract
# ─────────────────────────────────────────────────────────────────

@dataclass
class VerbVerdict:
    kind: VerdictKind
    contract: str = "VerbFormContract:v1"
    aspect: Aspect = ""
    mood: Mood = ""
    person: str = ""
    number: str = ""
    gender: str = ""
    lemma: str = ""
    evidence: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    prefix_stack: Optional[PrefixStack] = None


def _record(verdict: VerbVerdict, path: str) -> None:
    _AUDIT["candidates_seen"] += 1
    if verdict.kind == "Certificate":
        _AUDIT["certificate"] += 1
    elif verdict.kind == "Hypothesis":
        _AUDIT["hypothesis"] += 1
    else:
        _AUDIT["zero"] += 1
    _AUDIT["by_path"][path] = _AUDIT["by_path"].get(path, 0) + 1
    _AUDIT["blockers_count"] += len(verdict.blockers)


def evaluate_verb_form(token: str) -> VerbVerdict:
    """العَقد الرَّئيس: هَل هَذا فِعل؟"""
    _load_kana_lex()

    if not token or not token.strip():
        v = VerbVerdict(kind="Zero", blockers=["empty_token"])
        _record(v, "empty")
        return v

    # === [HIGHEST] ClosedFunctionWordGate — تَوصيَة المُستَخدِم 2026-05-25 ===
    # "ClosedFunctionWordContract يَجِب أَن يَسبِق VerbFormContract."
    # الأَدوات المُغلَقَة (مِمَّن، إِلَّآ، فَإِنَّهُۥ، أَلَّا، …) لا تَدخُل
    # مَسار الفِعل أَبَدًا.
    try:
        from closed_function_word_gate import check_closed_function_word
        _fn = check_closed_function_word(token)
        if _fn.is_function:
            v = VerbVerdict(
                kind="Zero",
                blockers=[f"ClosedFunctionWordGate: {_fn.category} — {_fn.note}"],
            )
            _record(v, "closed_function_word")
            return v
    except ImportError:
        pass

    # === HARD GATE: تَنوين عَلى الـsurface → اسم قَطعًا ===
    if any(c in token for c in ("ٌ", "ٍ", "ً")):
        v = VerbVerdict(kind="Zero", blockers=["tanwin → nominal, never verb"])
        _record(v, "hard_gate_tanwin")
        return v

    # === ObjectPronounVsPossessivePronounGate — تَوصيَة المُستَخدِم 2026-05-25 ===
    # يَفصِل بَين ضَمير المَفعول (اكتبوه — مَرَّ) وَ ضَمير المِلكيَّة (أَجَلِهِ — مَنع).
    # يَستَوعِب ٱ (هَمزَة وَصل) بَعد إِصلاح الـnormalization.
    try:
        from object_pronoun_vs_possessive_gate import classify_attached_pronoun
        _cls = classify_attached_pronoun(token)
        if _cls.is_possessive:
            v = VerbVerdict(
                kind="Zero",
                blockers=[f"PossessivePronoun (not verb): {_cls.reason}"],
            )
            _record(v, "possessive_pronoun_blocked")
            return v
        # OBJECT_OF_VERB or NONE → اسمَح بِالاستِمرار
    except ImportError:
        pass

    # === EARLY kana check — قَبل override gates لِيَنجُو وَكَانَ مِن مَنع المُثَنَّى ===
    # نَفحَص الـstripped مَع/بِدون بادِئة عَطف.
    _plain_early = _strip_diac(token)
    _kana_pre_check_hit = (token in _KANA_LEX or _plain_early in _KANA_LEX_PLAIN)
    if not _kana_pre_check_hit:
        # جَرِّب نَزع و/ف ثُمّ ابحَث
        if _plain_early[:1] in {"و", "ف"} and _plain_early[1:] in _KANA_LEX_PLAIN:
            _kana_pre_check_hit = True

    # === NonVerbOverrideGate — تَوصيَة المُستَخدِم 2026-05-25 ===
    # نَفحَص الـoverrides قَبل أَيّ مَنطِق فِعل: ال التَّعريف، ـة، ـان مُثَنَّى،
    # ـى مَقصورَة، أَفْعَلُ تَفضيل، وَ القائِمَة الصَّريحَة (إِذَا، كَمَا…).
    # نَستَثني المُطابِق لِـ kana_family — لأَنّ كَان ـ ان قَد يُشبِه مُثَنَّى.
    if not _kana_pre_check_hit:
        try:
            from non_verb_override_gate import check_non_verb_override
            _override_pre = check_non_verb_override(token, body=token, conj="")
            if _override_pre.blocked:
                v = VerbVerdict(
                    kind="Zero",
                    blockers=[f"NonVerbOverrideGate: {_override_pre.reason}"],
                )
                _record(v, "non_verb_override_pre")
                return v
        except ImportError:
            pass

    # === HARD GATE: أَفْعَلُ تَفضيل بَدون بادِئة فِعليَّة ===
    # نَمَط: أَ + ف + ْ + ع + َ + ل + ُ (4 حُروف، 7 chars بِالحَرَكات)
    # هَذا اسم تَفضيل (أَكْبَرُ، أَفْضَلُ)، لَيس فِعل 1sg.
    # نَستَثني: لَو سَبَقَتها بادِئة فِعليَّة (سَ/فَ + verb context) — نَتركها
    plain_norm = _strip_diac(_normalize_alif(token))
    if (
        len(plain_norm) == 4
        and plain_norm.startswith("أ")
        and token.startswith("أَ")
        and "ْ" in token[:5]  # سُكون عَلى الفاء
        and token.endswith(("ُ", "َ", "ِ"))
        and "ّ" not in token  # لا شَدّة
    ):
        v = VerbVerdict(
            kind="Zero",
            blockers=["أَفْعَلُ pattern bare → tafdeel (nominal), not 1sg verb"],
        )
        _record(v, "hard_gate_tafdeel")
        return v

    # === Path 1: kana-family lexicon (مَع/بِدون بادِئات) ===
    plain = _strip_diac(token)
    # مُحاوَلَة مُباشَرَة
    if token in _KANA_LEX:
        row = _KANA_LEX[token]
        v = VerbVerdict(
            kind="Certificate",
            aspect=row.get("aspect", ""),
            lemma=row.get("lemma", ""),
            evidence=[f"kana_family_lexicon: {token}"],
        )
        _record(v, "kana_exact")
        return v
    if plain in _KANA_LEX_PLAIN:
        row = _KANA_LEX_PLAIN[plain]
        v = VerbVerdict(
            kind="Certificate",
            aspect=row.get("aspect", ""),
            lemma=row.get("lemma", ""),
            evidence=[f"kana_family_lexicon (stripped): {plain}"],
        )
        _record(v, "kana_stripped")
        return v

    # === Path 2: parse prefix stack + check body in kana ===
    stack = parse_prefix_stack(token)
    body_plain = _strip_diac(stack.body)

    # === NonVerbOverrideGate POST-PREFIX: نُعيد الفَحص بِمَعرِفَة الـbody ===
    # كَي يَلتَقِط وَأَقْوَمُ (تَفضيل بَعد عَطف).
    # نَستَثني: لَو الـbody في kana → لا تَمنَع
    if (stack.body not in _KANA_LEX
        and _strip_diac(stack.body) not in _KANA_LEX_PLAIN):
        try:
            from non_verb_override_gate import check_non_verb_override
            _override_post = check_non_verb_override(
                token, body=stack.body, conj=stack.conj
            )
            if _override_post.blocked:
                v = VerbVerdict(
                    kind="Zero",
                    blockers=[f"NonVerbOverrideGate(post-stack): {_override_post.reason}"],
                    prefix_stack=stack,
                )
                _record(v, "non_verb_override_post")
                return v
        except ImportError:
            pass
    if stack.body in _KANA_LEX or body_plain in _KANA_LEX_PLAIN:
        row = _KANA_LEX.get(stack.body) or _KANA_LEX_PLAIN.get(body_plain, {})
        v = VerbVerdict(
            kind="Certificate",
            aspect=row.get("aspect", ""),
            lemma=row.get("lemma", ""),
            evidence=[
                f"prefix_stack: conj={stack.conj!r} lam={stack.lam_amr!r}",
                f"body in kana_lexicon: {stack.body}",
            ],
            prefix_stack=stack,
        )
        _record(v, "kana_with_prefix")
        return v

    # === Path 3: MoodDetector على الـbody ===
    mood_res = detect_mood(stack.body, has_lam_amr=stack.has_lam_amr)
    if not mood_res.aspect:
        # لا نَستَطيع التَّعَرُّف
        v = VerbVerdict(
            kind="Zero",
            evidence=[f"prefix_stack body={stack.body!r}"],
            blockers=["mood_detector: no aspect signal"],
            prefix_stack=stack,
        )
        _record(v, "no_mood")
        return v

    # === Path 4: MorphFeatures ===
    feat = extract_features(token, prefix=stack, mood_res=mood_res)

    # Certificate إِن كانَت الـbody تُطابِق بُنية فِعل واضِحَة:
    #   • IV: prefix يَ/تَ/نَ/أَ + body length >= 3
    #   • CV: همزَة وَصل + سُكون
    #   • PV: نَمَط CCC + فَتحَة
    #
    # نَطلُب أَيضًا أَن يَكون هُناك بادِئة أَمر/عَطف (دَليل قَوي)
    # أَو لاحِقَة فِعل واضِحَة (وا/تُم/تُما…)

    is_strong = False
    strong_reasons = []

    # بادِئة لام الأَمر مَع IV → قَطعيّ
    if stack.has_lam_amr and mood_res.aspect == "IV":
        is_strong = True
        strong_reasons.append("lam_amr + IV → command verb")

    # بادِئة ف/و + body فِعل واضِحَة
    if stack.has_conj and mood_res.aspect in ("IV", "PV", "CV"):
        # تَأَكَّد أَنّ الـbody كافِية الطُّول
        if len(body_plain) >= 4:
            is_strong = True
            strong_reasons.append(f"conj + {mood_res.aspect} body")

    # لاحِقَة فِعل واضِحَة (وا، تُم، تُما، تَا، نَ)
    verb_suffixes_clear = ("وا", "تُمْ", "تُمَا", "تُنَّ", "نَا", "تَا")
    if any(stack.body.endswith(sfx) for sfx in verb_suffixes_clear):
        is_strong = True
        strong_reasons.append(f"clear verb suffix")
    # PATCH 2D-fixup (2026-05-26): the diacritized list above misses
    # surface forms like تَدَايَنتُم whose final م carries no sukun in
    # the Quran rasm. Compare against diacritic-stripped tail so the
    # past-2p subject markers تم / تما / تن are caught regardless of
    # sukun/shadda presence on the final letter.
    body_plain = _strip_diac(stack.body)
    if (mood_res.aspect == "PV"
            and any(body_plain.endswith(s) for s in ("تم", "تما", "تن"))):
        is_strong = True
        strong_reasons.append("past-2p subject suffix (plain-strip match)")

    # هَمزَة وَصل + سُكون → CV قَطعيّ
    if mood_res.aspect == "CV":
        is_strong = True
        strong_reasons.append("CV with hamzat wasl + sukun")

    # PV simple (CCC pattern مَع 3 حَرَكات)
    if (
        mood_res.aspect == "PV" and not stack.has_conj
        and len(body_plain) == 3
    ):
        # كَتَبَ يَكون 3 حَرف + 3 فَتحات — قَطعيّ
        if all(c in stack.body for c in ("َ",)):
            is_strong = True
            strong_reasons.append("bare PV CCC pattern")

    # IV مَع تَشكيل كامِل عَلى الـbody ⇒ قَطعيّ
    # يَكْتُبُ، تَكْتُبُ، نَكْتُبُ، أَكْتُبُ
    # نَشتَرِط: بادِئة + سُكون داخِليّ + ضَمَّة/فَتحَة/كَسرَة نِهائيَّة + ≥3 letters
    if (
        mood_res.aspect == "IV" and not is_strong
        and len(body_plain) >= 3
        and "ْ" in stack.body  # سُكون داخِليّ (دَليل بُنية مُضارِع كامِلَة)
        and stack.body.endswith(("ُ", "َ", "ِ", "ُّ", "َّ"))
    ):
        is_strong = True
        strong_reasons.append("bare IV fully diacritized")

    # form II PV — شَدّة عَلى ثاني حَرف (عَلَّمَ، كَلَّمَ، نَزَّلَ)
    # نَمَط فَعَّلَ — قَطعيّ
    if (
        mood_res.aspect == "PV" and not is_strong
        and "ّ" in stack.body[:5]  # شَدّة بَعد الحَرف الأَوَّل
        and stack.body[:1] not in {"ٱ", "ا"}  # لَيس form VIII
    ):
        is_strong = True
        strong_reasons.append("form II PV with shadda")

    # PV passive plural — دُعُوا، قُتِلُوا (فُعُوا)
    # body[1] = ُ (passive marker) + ends in وا
    if (
        mood_res.aspect == "PV" and not is_strong
        and len(stack.body) >= 5
        and stack.body[1:2] == "ُ"
        and stack.body.endswith("وا")
    ):
        is_strong = True
        strong_reasons.append("passive PV plural فُعُوا")

    kind: VerdictKind = "Certificate" if is_strong else "Hypothesis"
    blockers = [] if is_strong else [
        "weak verb signal — body shape ambiguous"
    ]

    v = VerbVerdict(
        kind=kind,
        aspect=feat.aspect,
        mood=feat.mood,
        person=feat.person,
        number=feat.number,
        gender=feat.gender,
        evidence=mood_res.evidence + feat.evidence + strong_reasons,
        blockers=blockers,
        prefix_stack=stack,
    )
    _record(v, f"morph_{kind.lower()}")
    return v


# ─────────────────────────────────────────────────────────────────
# Helper for upstream: «هَل هَذا فِعل بِيَقين؟»
# ─────────────────────────────────────────────────────────────────

def is_verb_certified(token: str) -> bool:
    """Quick yes/no — يُسبق `closed_class_detector` في Layer 1."""
    return evaluate_verb_form(token).kind == "Certificate"


# ─────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cases = [
        "كَانَ", "لَيْسَ", "فَلَيْسَ", "وَكَانَ",
        "فَٱكْتُبُوهُ", "فَاكْتُبُوهُ", "اكْتُبْ",
        "وَلْيَكْتُبْ", "فَلْيَكْتُبْ", "وَلْيُمْلِلْ", "فَلْيُمْلِلْ",
        "وَٱتَّقُوا", "وَأَشْهِدُوا",
        "كَتَبَ", "يَكْتُبُ", "تَكْتُبُونَ",
        # nominal — should be Zero
        "كِتَابٌ", "تِجَارَةً", "ٱلَّذِينَ", "أَفْضَلُ",
        # short ambiguous
        "بِ", "فِي", "إِنَّ",
    ]
    print(f"{'token':<22} {'kind':<14} {'aspect':<5} {'mood':<6} {'lemma':<10} {'evidence'}")
    print("-" * 100)
    for tok in cases:
        v = evaluate_verb_form(tok)
        sym = {"Certificate": "✓", "Hypothesis": "?", "Zero": "✗"}[v.kind]
        ev = " | ".join(v.evidence[:2])
        print(f"{sym} {tok:<20} {v.kind:<12} {v.aspect:<5} {v.mood:<6} {v.lemma:<10} {ev}")
    print()
    print(f"audit: {get_audit()}")
