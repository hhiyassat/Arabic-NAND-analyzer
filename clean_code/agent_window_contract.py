"""agent_window_contract.py — عَقد نافِذَة الفاعل.

تَوصيَة المُستَخدِم 2026-05-25:

  "agent_of لا يَعتَمِد عَلى role=فاعل مرفوع وَحده.
   بَل يَحتاج:
     1. الفِعل certified FIIL.
     2. الاسم داخِل نافِذَة نَحويَّة صالِحَة.
     3. لا يوجَد فاصِل جار/مَفعول/تابع يَمنَع العَلاقَة.
     4. لا يوجَد فاعِل مُستَتِر أَقوى لِلفِعل.
     5. الاسم لَيس خَبَر/صِفَة/تَفضيل/تابِع/مُضاف إِلَيه."

البَوّابَة:
  evaluate_agent_window(verb_token, noun_token, *,
                         all_tokens, verb_idx, noun_idx,
                         has_implicit_agent: bool=False)
    → AgentWindowVerdict(kind ∈ {Certificate, Hypothesis, Zero}, blockers)

الفِكرَة الأَساسيَّة: agent_of يَتَطَلَّب نَوافِذ مَكانيَّة دَقيقَة،
لَيس مُجَرَّد قُرب أَو role سَطحيّ.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

VerdictKind = Literal["Certificate", "Hypothesis", "Zero"]

_DIACRITICS = set("ًٌٍَُِّْٰـ")


def _strip_diac(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIACRITICS)


# ─────────────────────────────────────────────────────────────────
# Audit
# ─────────────────────────────────────────────────────────────────

_AUDIT = {
    "candidates_seen": 0,
    "certificate": 0,
    "hypothesis": 0,
    "zero": 0,
    "zero_reasons": {},
}


def reset_audit() -> None:
    _AUDIT["candidates_seen"] = 0
    _AUDIT["certificate"] = 0
    _AUDIT["hypothesis"] = 0
    _AUDIT["zero"] = 0
    _AUDIT["zero_reasons"] = {}


def get_audit() -> dict:
    return dict(_AUDIT)


# ─────────────────────────────────────────────────────────────────
# Sub-checks (gates)
# ─────────────────────────────────────────────────────────────────

def _verb_is_certified(v_tok) -> bool:
    """الفِعل مُصَنَّف Certificate (مِن VerbFormContract أَو الـloaders)."""
    if not v_tok:
        return False
    if getattr(v_tok, "word_class", "") != "FIIL":
        return False
    kind = getattr(v_tok, "wordclass_kind", "") or ""
    return kind == "Certificate"


def _verb_has_command_or_jussive_form(v_tok) -> bool:
    """فِعل أَمر أَو مَجزوم يَفضِّل فاعِلًا مُستَتِرًا.

    قَرائن (أَيّ واحِدَة كافِيَة):
      • role يَحوي «أمر» أَو «مَجزوم»
      • aspect = CV
      • mood = JUSS / IMPER
      • surface يَبدَأ بِـ وَلْ/فَلْ/لْ (لام الأَمر بَعد عَطف)
      • surface يَبدَأ بِـ ا + سُكون + جِسم فِعل أَمر
    """
    if not v_tok:
        return False
    role = (getattr(v_tok, "role_phrase", "") or "")
    if "أمر" in role or "مَجزوم" in role or "مجزوم" in role:
        return True
    aspect = getattr(v_tok, "verb_aspect", "") or ""
    if aspect == "CV":
        return True
    mood = getattr(v_tok, "verb_mood", "") or ""
    if mood in ("JUSS", "IMPER"):
        return True
    # SURFACE detection: لام الأَمر (وَلْيَ/فَلْيَ/لْيَ)
    surface = getattr(v_tok, "token", "") or ""
    if surface.startswith(("وَلْ", "فَلْ", "لْ")):
        return True
    # Imperative pattern: ا+سُكون (اكْتُبْ، اقْرَأْ)
    plain = _strip_diac(surface).replace("ٱ", "ا")
    if plain.startswith("ا") and len(surface) >= 4 and "ْ" in surface[:4]:
        # exclude form X/VII/VIII past (استَ، انفَ، افتَ)
        if not plain.startswith(("است", "انف", "افت")):
            return True
    # Imperative ending وا — اكتبوا، اتقوا (CV plural)
    if (plain.endswith("وا") and plain.startswith(("ا", "و", "ف"))
        and len(plain) >= 5):
        return True
    return False


def _intervening_blocker(all_tokens: list, verb_idx: int, noun_idx: int) -> str:
    """يَبحَث عَن HARF_JARR/مَفعول/تابِع/مَنصوب بَين الفِعل وَالاسم.

    Returns: empty string لو لا فاصِل، وَإلّا سَبَب الحَجب.
    """
    lo = min(verb_idx, noun_idx)
    hi = max(verb_idx, noun_idx)
    if hi - lo <= 1:
        return ""  # لا فَجوَة
    for j in range(lo + 1, hi):
        t = all_tokens[j]
        wc = getattr(t, "word_class", "")
        closed = getattr(t, "closed_class_kind", "") or ""
        role = (getattr(t, "role_phrase", "") or "")
        surface = getattr(t, "token", "") or ""
        # HARF_JARR بَين الفِعل وَالاسم → الاسم مَجرور لا فاعِل
        if wc == "HARF" and closed == "HARF_JARR":
            return f"HARF_JARR ({t.token}) intervenes between verb[{verb_idx}] and noun[{noun_idx}]"
        # مَفعول صَريح بَين الفِعل وَالاسم
        if "مفعول" in role:
            return f"explicit مَفعول ({t.token}) intervenes — noun is بَدَل/تابع"
        # اسم مَنصوب صَريح بَين (تَنوين فَتح أَو رولّ مَنصوب)
        if (wc in ("ISM_MUARAB", "JAMID", "SINGULAR_TERM", "AALAM")
            and ("منصوب" in role or "ً" in surface)):
            return f"explicit مَنصوب ({t.token}) intervenes — candidate noun is بَدَل/تَوكيد"
        # خَبَر كان/إنّ بَين
        if "خبر" in role and "كان" in role:
            return f"khabar of kana intervenes"
    return ""


def _intervening_verb(all_tokens: list, verb_idx: int, noun_idx: int) -> str:
    """فِعل آخَر بَين الفِعل وَالاسم → الاسم لِلفِعل الأَقرَب، لا لِهَذا.

    تَوصيَة المُستَخدِم 2026-05-25:
      «إذا تَجاوَزَت النّافِذَة فِعلًا تالِيًا → الاسم لِلفِعل التالي.»
    """
    lo = min(verb_idx, noun_idx)
    hi = max(verb_idx, noun_idx)
    if hi - lo <= 1:
        return ""
    for j in range(lo + 1, hi):
        if j == verb_idx or j == noun_idx:
            continue
        t = all_tokens[j]
        if getattr(t, "word_class", "") == "FIIL":
            return f"intervening FIIL ({t.token}) at [{j}] — noun belongs to closer verb"
    return ""


def _detached_pronoun_after_verb(all_tokens: list, verb_idx: int, noun_idx: int) -> str:
    """ضَمير مُنفَصِل (هُوَ/هي/هم...) مُباشَرَة بَعد الفِعل = فاعل صَريح.

    تَوصيَة المُستَخدِم: «إِذا ظَهَر ضَمير صَريح بَعد الفِعل، الاسم
    اللاحِق لا يَتَّصِل بِالفِعل عَبر حُدود الفِعل التالي.»

    أَمثِلَة: يُمِلَّ هُوَ → هُوَ هُو الفاعل، وَلِيُّهُ لَيس فاعِلًا لِيُمِلَّ.
    """
    if noun_idx <= verb_idx:
        return ""
    DETACHED_PRONOUNS = {
        "هُوَ", "هِيَ", "هُمَا", "هُمْ", "هُنَّ",
        "أَنَا", "نَحْنُ", "أَنْتَ", "أَنْتِ", "أَنْتُمَا",
        "أَنْتُمْ", "أَنْتُنَّ",
    }
    # نَفحَص الـtokens مُباشَرَة بَعد الفِعل (1-2 خانات)
    for j in range(verb_idx + 1, min(verb_idx + 3, noun_idx)):
        t = all_tokens[j]
        surface = (getattr(t, "token", "") or "").strip()
        if surface in DETACHED_PRONOUNS:
            return (
                f"detached pronoun ({surface}) at [{j}] right after verb "
                f"— it is the explicit subject; noun at [{noun_idx}] is for next verb"
            )
    return ""


def _is_passive_voice(v_tok) -> str:
    """يَفحَص هَل الفِعل مَبني لِلمَجهول.

    قَرائن:
      • يُ + فِعل أَجوَف (يُقالُ، يُضارَّ، يُؤكَل)
      • يُ + شَدّة في الجِسم (يُضَارَّ، يُمَلَّى) + فَتحَة عَلى الأَوَّل
      • فُعِل (PV passive): ضَمَّة + كَسرَة + فَتحَة
    """
    if not v_tok:
        return ""
    surface = getattr(v_tok, "token", "") or ""
    if len(surface) < 3:
        return ""
    # نُطَبِّع آ/ٱ → ا لِلفَحص
    surface_n = surface.replace("ٱ", "ا").replace("آ", "ا")
    plain = "".join(c for c in surface_n if c not in _DIACRITICS)
    if len(plain) < 3:
        return ""
    # يُ + body with shadda/alif (form II/III/IV passive)
    if surface.startswith("يُ"):
        # يُضَآرَّ / يُضَارَّ — form III passive
        if "ا" in plain[:4] and "ّ" in surface:
            return f"passive voice (يُ + alif + shadda): {surface}"
        # يُفَعَّل (form II passive)
        if "ّ" in surface and "َ" in surface[:5]:
            return f"passive voice (يُ + shadda + fatha): {surface}"
        # يُفْعَل (form I passive) — يُ + C + ْ + C + َ + C
        if len(surface) >= 6 and surface[3:4] == "ْ" and surface[5:6] == "َ":
            # يَ doesn't match this pattern at index [3]ْ
            return f"passive voice (يُفْعَل pattern): {surface}"
    # تُ + same patterns
    if surface.startswith("تُ") and len(surface) >= 5:
        if ("ا" in plain[:4] and "ّ" in surface) or (
            "ّ" in surface and "َ" in surface[:5]):
            return f"passive voice (تُ + shadda/alif + fatha): {surface}"
    return ""


def _noun_in_inna_scope(all_tokens: list, verb_idx: int, noun_idx: int) -> str:
    """يَفحَص: هَل الاسم خَبَر إِنَّ/أَنَّ (لا فاعِل لِفِعل لاحِق)؟

    قَرينَة: بَعد إِنَّ + ضَمير → خَبَر، لَيس فاعِل لِفِعل قَبله.
    مَثَل: «فَإِنَّهُ فُسُوقٌ» — فُسُوقٌ خَبَر إِنَّ، لا فاعِل لِـ تَفْعَلُوا.
    """
    if noun_idx <= 0:
        return ""
    # نَبحَث في الـ3 tokens السابِقَة لِلاسم عَن إِنَّ-مَركَّب
    for k in range(max(0, noun_idx - 3), noun_idx):
        t = all_tokens[k]
        surface = getattr(t, "token", "") or ""
        plain = "".join(c for c in surface if c not in _DIACRITICS)
        plain = plain.replace("ٱ", "ا")
        # إنَّ/أَنَّ/فَإِنَّ/وَإِنَّ + هـ/ه/ها/هم
        if plain.startswith(("إن", "أن", "فإن", "وإن", "كأن", "لكن", "ليت", "لعل")):
            # يَجِب أَن يَحوي شَدّة (دَليل إِنَّ، لا أَن المَصدَريَّة)
            if "ّ" in surface and ("ه" in plain[-3:] or "ها" in plain
                                   or "هم" in plain or "كم" in plain):
                return f"noun follows {surface} (inna+pronoun) → خَبَر إِنَّ, not agent"
    return ""


def _noun_role_blocks_agent(noun_tok) -> str:
    """يَفحَص دَور الاسم — إِن كانَ خَبَر/صِفَة/تَفضيل/تابِع/مُضاف إِلَيه."""
    role = (getattr(noun_tok, "role_phrase", "") or "")
    blocking_roles = [
        ("خبر", "noun has role=خبر (predicate, not agent)"),
        ("صفة", "noun has role=صفة"),
        ("نعت", "noun has role=نعت (attribute)"),
        ("بدل", "noun has role=بدل"),
        ("توكيد", "noun has role=توكيد"),
        ("مضاف", "noun has role=مضاف إليه (genitive)"),
        ("معطوف", "noun has role=معطوف"),
        ("تمييز", "noun has role=تمييز"),
        ("حال", "noun has role=حال"),
    ]
    for marker, reason in blocking_roles:
        if marker in role:
            # استِثناء: «مُضاف» وَحدها قَد تَكون «اسم مُضاف» لا «مُضاف إليه»
            if marker == "مضاف" and "إليه" not in role:
                continue
            return reason
    return ""


def _noun_is_tafdeel(noun_tok) -> str:
    """اسم تَفضيل (أَفْعَلُ) — لا يَكون فاعِلًا عادَةً."""
    surface = getattr(noun_tok, "token", "") or ""
    plain = _strip_diac(surface).replace("ٱ", "ا")
    # أَفْعَلُ + لا تَنوين + ضَمَّة نِهائيَّة
    if (len(plain) == 4 and plain.startswith("أ")
        and not any(c in surface for c in ("ٌ", "ٍ", "ً"))
        and surface.endswith("ُ")
        and "ْ" in surface[:5]
        and "ّ" not in surface):
        return "noun is أَفْعَلُ pattern (tafdeel) — not an agent"
    return ""


def _noun_is_predicate_with_tanwin_before_conj_verb(
    noun_tok, all_tokens: list, verb_idx: int, noun_idx: int
) -> str:
    """v3 — تَوصيَة المُستَخدِم 2026-05-25 (الجَلسَة 5):

      "غَفُورٌ لا يَكون agent_of وَيَغْفِرْ.
       Predicate/attribute nouns cannot become verbal agents."

    القَرينَة: اسم مُنَوَّن (تَنوين ضَمّ = خَبَر) قَبل و/ف + فِعل
      → خَبَر جُملَة اسميَّة سابِقَة، لَيس فاعِل الفِعل التالي.

    أَمثِلَة:
      ٱللَّهُ غَفُورٌ وَيَغْفِرْ → غَفُورٌ خَبَر ٱللَّهُ، لا فاعِل يَغْفِر
      عَلِيمٌ حَكِيمٌ وَيَفعَلُ → كِلاهُما خَبَر، لا فاعِلان
    """
    if noun_idx >= len(all_tokens) - 1:
        return ""
    if verb_idx <= noun_idx:
        return ""  # هَذه القاعِدَة لِلِاسم قَبل الفِعل (noun_idx < verb_idx)
    surface = getattr(noun_tok, "token", "") or ""
    # تَنوين الضَّمّ (ـٌ) عَلى الاسم → نَكِرَة مَرفوعَة (خَبَر مُحتَمَل)
    if "ٌ" not in surface:
        return ""
    # افحَص ما بَين الاسم وَالفِعل: لَو يَحوي و/ف + الفِعل مُباشَرَة
    # → خَبَر سابِق + جُملَة جَديدَة بِالعَطف
    for k in range(noun_idx + 1, min(verb_idx + 1, len(all_tokens))):
        tk = all_tokens[k]
        tk_surf = getattr(tk, "token", "") or ""
        if k == verb_idx:
            # وَصَلنا لِلفِعل — افحَص هَل بَدَأ بِـ و/ف
            if tk_surf.startswith(("وَ", "فَ", "و", "ف")):
                return "noun is predicate (tanwin ـٌ) before conj+verb — خَبَر جُملَة اسميَّة، لا فاعِل"
    return ""


def _stronger_implicit_subject(v_tok, has_implicit_agent: bool = False) -> str:
    """فِعل أَمر/مَجزوم له فاعِل مُستَتِر أَقوى.

    تَوصيَة المُستَخدِم: «أفعال الأَمر أَو لام الأَمر، الفاعل المُستَتِر
    غالِبًا أَقوى مِن اسم بَعيد أَو تابِع لاحِق.»

    نَفحَص الفِعل نَفسه بِدلًا مِن الِاعتِماد فَقَط عَلى has_implicit_agent flag.
    """
    if _verb_has_command_or_jussive_form(v_tok):
        return "command/jussive verb has stronger implicit subject (⊕أَنْتَ/⊕أَنْتُمْ)"
    return ""


def _distance_too_far(verb_idx: int, noun_idx: int, max_window: int = 4) -> str:
    """لَو المَسافَة بَين الفِعل وَالاسم > max_window، رَفض."""
    d = abs(noun_idx - verb_idx)
    if d > max_window:
        return f"distance verb→noun = {d} tokens > window ({max_window})"
    return ""


# ─────────────────────────────────────────────────────────────────
# Main evaluator
# ─────────────────────────────────────────────────────────────────

@dataclass
class AgentWindowVerdict:
    kind: VerdictKind
    contract: str = "AgentWindowContract:v1"
    evidence: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


def _record(verdict: AgentWindowVerdict) -> None:
    _AUDIT["candidates_seen"] += 1
    if verdict.kind == "Certificate":
        _AUDIT["certificate"] += 1
    elif verdict.kind == "Hypothesis":
        _AUDIT["hypothesis"] += 1
    else:
        _AUDIT["zero"] += 1
        for b in verdict.blockers:
            key = b.split(" — ")[0][:60]
            _AUDIT["zero_reasons"][key] = _AUDIT["zero_reasons"].get(key, 0) + 1


def evaluate_agent_window(*, v_token, x_token,
                          all_tokens: list,
                          verb_idx: int, noun_idx: int,
                          has_implicit_agent: bool = False,
                          max_window: int = 4) -> AgentWindowVerdict:
    """العَقد الرَّئيس: هَل الاسم فاعِل صالِح لِلفِعل؟

    تَوصيَة المُستَخدِم 2026-05-25 (تَشديد): فِعل الأَمر/المَجزوم يَرفُض
    أَيّ فاعِل صَريح — الفاعِل المُستَتِر هُوَ الأَقوى دائِمًا.
    """
    evidence = []
    blockers = []

    # === Gate 1: STRONG REJECT — command/jussive verb has implicit subject ===
    # هَذا أَقوى Reject. لا Hypothesis، Zero.
    stronger = _stronger_implicit_subject(v_token)
    if stronger:
        v = AgentWindowVerdict(kind="Zero", blockers=[stronger])
        _record(v); return v

    # === Gate 2: distance window ===
    far = _distance_too_far(verb_idx, noun_idx, max_window=max_window)
    if far:
        v = AgentWindowVerdict(kind="Zero", blockers=[far])
        _record(v); return v

    # === Gate 3: intervening blocker (HARF_JARR/مَفعول/مَنصوب/خَبَر كان) ===
    interv = _intervening_blocker(all_tokens, verb_idx, noun_idx)
    if interv:
        v = AgentWindowVerdict(kind="Zero", blockers=[interv])
        _record(v); return v

    # === Gate 3.5: intervening FIIL → الاسم لِلفِعل التالي (v2) ===
    interv_v = _intervening_verb(all_tokens, verb_idx, noun_idx)
    if interv_v:
        v = AgentWindowVerdict(kind="Zero", blockers=[interv_v])
        _record(v); return v

    # === Gate 3.6: detached pronoun after verb (v2) ===
    # هُوَ/هي/أَنْتَ مُباشَرَة بَعد الفِعل = فاعل صَريح؛ الاسم اللاحِق لِفِعل آخَر
    det_pron = _detached_pronoun_after_verb(all_tokens, verb_idx, noun_idx)
    if det_pron:
        v = AgentWindowVerdict(kind="Zero", blockers=[det_pron])
        _record(v); return v

    # === Gate 3.7: passive voice → نائِب فاعِل لا agent_of عاديّ (v2) ===
    passive = _is_passive_voice(v_token)
    if passive:
        v = AgentWindowVerdict(
            kind="Zero",
            blockers=[f"{passive} — use naib_faail not agent_of"],
        )
        _record(v); return v

    # === Gate 4: noun in إِنَّ scope → خَبَر إنّ، لا فاعِل ===
    inna = _noun_in_inna_scope(all_tokens, verb_idx, noun_idx)
    if inna:
        v = AgentWindowVerdict(kind="Zero", blockers=[inna])
        _record(v); return v

    # === Gate 5: noun role blocks ===
    role_block = _noun_role_blocks_agent(x_token)
    if role_block:
        v = AgentWindowVerdict(kind="Zero", blockers=[role_block])
        _record(v); return v

    # === Gate 6: noun is tafdeel ===
    tafdeel = _noun_is_tafdeel(x_token)
    if tafdeel:
        v = AgentWindowVerdict(kind="Zero", blockers=[tafdeel])
        _record(v); return v

    # === Gate 6.5 (v3): predicate noun (tanwin) before conj+verb ===
    # غَفُورٌ وَيَغْفِرْ — خَبَر سابِق، لا فاعِل لِلفِعل التالي
    pred_block = _noun_is_predicate_with_tanwin_before_conj_verb(
        x_token, all_tokens, verb_idx, noun_idx
    )
    if pred_block:
        v = AgentWindowVerdict(kind="Zero", blockers=[pred_block])
        _record(v); return v

    # === Gate 7: verb certified ===
    if not _verb_is_certified(v_token):
        blockers.append("verb is FIIL but not Certificate")

    # === Gate 8: position-based ===
    if noun_idx > verb_idx and noun_idx - verb_idx <= 2:
        evidence.append(f"noun adjacent post-verb (distance={noun_idx-verb_idx})")
    elif noun_idx < verb_idx and verb_idx - noun_idx <= 2:
        evidence.append(f"noun pre-verb (distance={verb_idx-noun_idx})")
    else:
        blockers.append(f"distance={abs(verb_idx-noun_idx)} — outside ideal window")

    # Verdict
    if not blockers:
        v = AgentWindowVerdict(kind="Certificate", evidence=evidence)
    else:
        v = AgentWindowVerdict(
            kind="Hypothesis",
            evidence=evidence,
            blockers=blockers,
        )
    _record(v); return v


# ─────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("AgentWindowContract:v1")
    print()
    # Simple smoke test with fake tokens
    class FakeToken:
        def __init__(self, token, word_class="ISM_MUARAB",
                     role_phrase="", wordclass_kind="",
                     closed_class_kind="", verb_aspect="",
                     verb_mood=""):
            self.token = token
            self.word_class = word_class
            self.role_phrase = role_phrase
            self.wordclass_kind = wordclass_kind
            self.closed_class_kind = closed_class_kind
            self.verb_aspect = verb_aspect
            self.verb_mood = verb_mood

    cases = [
        # (label, verb, noun, all_tokens, vi, ni, has_implicit)
        ("kataba alwaladu (Cert)",
         FakeToken("كَتَبَ", "FIIL", wordclass_kind="Certificate"),
         FakeToken("الْوَلَدُ", role_phrase="فاعل مرفوع"),
         None, 0, 1, False),
        ("walyumlili al-haqq (jussive + implicit)",
         FakeToken("وَلْيُمْلِلِ", "FIIL", wordclass_kind="Certificate", verb_mood="JUSS"),
         FakeToken("ٱلْحَقُّ", role_phrase="فاعل مرفوع"),
         None, 0, 3, True),  # 3 tokens away
        ("rabbahu after verb",
         FakeToken("وَلْيَتَّقِ", "FIIL", wordclass_kind="Certificate", verb_mood="JUSS"),
         FakeToken("رَبَّهُ", role_phrase="فاعل مرفوع"),
         None, 0, 2, True),
        ("aqsatu tafdeel",
         FakeToken("تَكْتُبُوهَا", "FIIL", wordclass_kind="Hypothesis"),
         FakeToken("أَقْسَطُ", role_phrase="فاعل مرفوع"),
         None, 0, 5, False),
    ]
    for label, v, x, all_t, vi, ni, has_imp in cases:
        if all_t is None:
            all_t = [v] + ([None] * (max(vi, ni))) + [x]
            # fill with empty fake tokens
            all_t = [FakeToken(f"t{i}") for i in range(max(vi, ni) + 1)]
            all_t[vi] = v
            all_t[ni] = x
        r = evaluate_agent_window(
            v_token=v, x_token=x,
            all_tokens=all_t,
            verb_idx=vi, noun_idx=ni,
            has_implicit_agent=has_imp,
        )
        sym = {"Certificate": "✓", "Hypothesis": "?", "Zero": "✗"}[r.kind]
        print(f"  {sym} {label:40s} → {r.kind}")
        for b in r.blockers[:2]:
            print(f"      blocker: {b}")
    print()
    print(f"audit: {get_audit()}")
