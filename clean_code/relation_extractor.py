"""relation_extractor.py — جَلسة 15: استخراج العَلاقات مِن i3rab.

يَأخُذ `SentenceI3rab` (مِن `i3rab_engine.engine`) ويُنتِج `RelationGraph`.

كُلّ علاقَة:
  • Token مَع role_phrase = «فاعل» ← agent_of(token, nearest_verb)
  • Token مَع role_phrase = «مفعول به» ← patient_of(token, nearest_verb)
  • Token مَع role_phrase = «مضاف إليه» ← possessor_of(token, prev_noun)
  • Token مَع role_phrase = «نعت» ← attribute_of(token, prev_noun)
  • Token مَع role_phrase = «مبتدأ» + خبر لاحِق ← topic_of/comment_of
  • Token مَع role_phrase = «خبر» ← comment_of(token, prev_mubtada)
  • Token مَع role_phrase = «اسم إنّ» / «خبر إنّ» ← inna_topic_of / inna_comment_of
  • Token مَع role_phrase = «اسم مجرور» ← harf_jarr_of(token, prev_harf_jarr)
    (التَّوسعة في جَلسة 16 — operator مِن `harf_jarr_relations.csv`)
  • Token مَع role_phrase = «معطوف» ← coordinate_of
  • Token مَع word_class = «FIIL» ← verb_in_clause(verb, —)

كُلّ علاقَة تَحمِل ProofObject-like metadata.

Constitutional commitments:
  1. Source-of-Claim — كُلّ علاقَة تَحمِل اسم role + اسم target + اسم rule
  2. Confidence — kind مَوروث مِن role_kind في i3rab (Certificate أَو Hypothesis)
  3. Alternatives — لَو فِعلان مُمكِنان كَ target، يُحفَظ الـ alternative
  4. Reversible — مُؤَجَّل
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows
from relation_schema import EntityNode, Relation, RelationGraph


CONTRACT_NAME = "RelationExtractor:v1"


# ============================================================================
# PATCH 7 (2026-05-28) — L4 Relation Safety Gates
# ============================================================================
#
# Block obviously invalid relations before they pollute the MeaningGraph
# (which L8 reads). Each gate is a small predicate; emission sites in
# the main extractor consult them with an early `continue`. No relation
# is invented here — only filtered.

_DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _p7_strip(s: str) -> str:
    s = "".join(c for c in (s or "") if c not in _DIACRITICS)
    return s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")


# Temporal / conditional particles that L3 sometimes mis-labels as
# مفعول به. They are ظَرف / أَداة شَرط, never a true verb patient.
_P7_TEMPORAL_OR_CONDITIONAL_PARTICLES = {
    "اذا", "اذ", "لما", "متى", "حين", "حينما", "ايان", "كلما",
    "حيث", "حيثما",
}


def _p7_is_temporal_or_conditional_particle(t) -> bool:
    """True if token is إِذَا / إِذ / لَمَّا / مَتى / حيث / كُلَّما / ... or
    if its wazn field literally contains 'ظرف' or 'شرط'."""
    surf = _p7_strip(getattr(t, "token", "") or getattr(t, "surface", ""))
    if surf in _P7_TEMPORAL_OR_CONDITIONAL_PARTICLES:
        return True
    wazn = getattr(t, "wazn", "") or ""
    if "ظرف" in wazn or "شرط" in wazn:
        return True
    return False


def _p7_token_has_prep_prefix(t) -> bool:
    """True if the segmenter peeled بِ/لِ/كِ as a PREP prefix on this token.
    Used to block possessor_of emission on prepositional-phrase nouns
    (بِكُلِّ is جار+مجرور, not a مضاف-إليه candidate for the next noun)."""
    prefix_tags = getattr(t, "prefix_tags", None) or []
    if "PREP" in prefix_tags:
        return True
    # Fallback for tokens that don't carry prefix_tags: re-segment.
    surface = getattr(t, "token", "") or getattr(t, "surface", "")
    if not surface:
        return False
    try:
        from segmenter import segment as _segment  # type: ignore
        seg = _segment(surface, normalize_input=True)
        return "PREP" in (seg.prefix_tags or [])
    except Exception:
        return False


def _p7_is_jalalah(t) -> bool:
    """True if the token is لَفظ الجَلالَة (ٱللَّه / اللَّه, in any case).
    The i3rab engine sometimes classifies it as JALALAH and sometimes
    as JAMID with wazn='لفظ الجلالة' (depending on position/MASAQ feed),
    so we check word_class, wazn, AND a stem/surface fallback."""
    if getattr(t, "word_class", "") == "JALALAH":
        return True
    wazn = getattr(t, "wazn", "") or ""
    if "جلال" in wazn:
        return True
    stem = getattr(t, "stem", "") or getattr(t, "token", "") or getattr(t, "surface", "") or ""
    stem_plain = _p7_strip(stem)
    return stem_plain in ("الله", "اللاه", "اله") or stem_plain.endswith("الله")


def _p7_token_starts_with_conjunction(t) -> bool:
    """True if the token starts with وَ / فَ (CONJ-peeled prefix)."""
    prefix_tags = getattr(t, "prefix_tags", None) or []
    if "CONJ" in prefix_tags:
        return True
    surface = getattr(t, "token", "") or ""
    return surface.startswith(("وَ", "فَ", "و", "ف"))


def _p7_has_iv_prefix_surface(surface_plain: str) -> bool:
    """True if a normalized verb surface starts with a مضارع prefix
    (يَ/تَ/نَ/أَ collapsed to ي/ت/ن/أ). Used by the implicit-agent gate
    to reject PAST-suffix rules on IV-prefixed verbs (e.g., يَكُونَا
    must not match the past-tense `نا` rule, which would inject
    ⊕نَحْنُ)."""
    if not surface_plain:
        return False
    return surface_plain[:1] in ("ي", "ت", "ن", "ا") or surface_plain[:1] == "أ"


# ============================================================================
# PATCH 12 (2026-05-28) — L4 Remaining Relation Cleanup
# ============================================================================
#
# Four narrow safety filters on top of PATCH 7:
#   • Block possessor_of when the target is a locative ظَرف noun
#     (ٱللَّهِ → عِندَ should not be possessor_of; ٱللَّهِ is the
#     complement of the locative, not the مالك of عِندَ).
#   • Block attribute_of when the TARGET has a PREP prefix
#     (شَىْءٍ → بِكُلِّ should not be attribute_of; شَىْءٍ is مضاف
#     إِليه inside the PP, not a نعت of the PP head).
#   • Block ism_of_kana when the source token starts with فَ
#     (فَرَجُلٌ is the apodosis جواب الشرط after «إن لم يكونا...»,
#     not the اسم of يَكُونَا).
#   • Block patient2_of when (a) the verb's root is NOT in the
#     ditransitive-verbs set, OR (b) a coordinator (أَوْ/و) sits
#     between the first patient and the candidate (الكَلِمَتان حال
#     مَعطوفَتان لا مَفعولان مُختَلِفان).


def _p12_target_is_locative_zarf(target_token) -> bool:
    """True if the target of a possessor_of relation is a locative
    ظَرف noun (e.g., عِندَ). Reads role_phrase set by L3."""
    if target_token is None:
        return False
    role = getattr(target_token, "role_phrase", "") or ""
    if "ظرف مكان" in role or "ظرف زمان" in role:
        return True
    # Surface fallback for tokens whose role wasn't filled yet
    surf = _p7_strip(getattr(target_token, "token", "") or "")
    if surf in {"عند", "بين", "تحت", "فوق", "قبل", "بعد",
                "امام", "خلف", "وراء", "مع"}:
        return True
    return False


def _p12_target_has_prep_prefix(target_token) -> bool:
    """True iff the TARGET token carries a PREP-peeled prefix
    (بِ / لِ / كِ). Used to block attribute_of from a نعت candidate
    to a PP-headed noun."""
    if target_token is None:
        return False
    return _p7_token_has_prep_prefix(target_token)


def _p12_source_is_apodosis_fa(source_token) -> bool:
    """True if the source surface starts with فَ — apodosis marker
    of a conditional (جواب الشرط). Used to block ism_of_kana from
    apodosis-headed nouns like فَرَجُلٌ → يَكُونَا."""
    surf = getattr(source_token, "token", "") or ""
    # Diacritic-sensitive: فَـ (fatha) is the apodosis/conjunction
    # marker; do NOT match فُـ (which is part of native words like
    # فُسُوقٌ; that case is the segmenter's false CONJ peel, but the
    # apodosis fa is always فَـ).
    return surf.startswith(("فَ",))


# Ditransitive-verb roots — verbs that genuinely take two objects.
_P12_DITRANS_ROOTS = {
    "عطي", "كسو", "لبس", "علم", "ظنن", "حسب",
    "خيل", "زعم", "وجد", "جعل", "اتخذ", "ري",
}

# Coordinators that separate parallel حال/صفة, NOT distinct patients.
_P12_COORD_SURFACES_PLAIN = {"او", "و", "ام", "بل", "ثم", "ف"}


def _p12_should_skip_patient2(verb_root: str, tokens, first_patient_pos: int,
                                candidate_pos: int) -> bool:
    """True if patient2_of(candidate → verb) should be blocked because:
       (a) verb root is NOT in the ditransitive-verbs set, OR
       (b) a coordinator (أَوْ / و / أم / ...) sits between the first
           patient position and the candidate position (the two nouns
           are coordinated حال/صفة, not two distinct patients).
    """
    if (verb_root or "").strip() not in _P12_DITRANS_ROOTS:
        return True
    for j in range(first_patient_pos + 1, candidate_pos):
        if 0 <= j < len(tokens):
            tw = getattr(tokens[j], "token", "") or ""
            plain = _p7_strip(tw).strip()
            if plain in _P12_COORD_SURFACES_PLAIN:
                return True
    return False


# ============================================================================
# تَطبيع role_phrase — يَدعَم تَنَوُّعات «مفعول به» / «مفعولٌ به» / «مفعول_به»
# ============================================================================

def _normalize_role(phrase: str) -> str:
    """يَستَخرِج جَوهَر role_phrase بِغَضّ النَّظَر عَن لاحِقات الحالَة.

    Examples:
      "فاعل مرفوع"             → "فاعل"
      "مفعول به منصوب"          → "مفعول_به"
      "مضاف إليه مجرور"         → "مضاف_إليه"
      "خبر إنّ مرفوع"           → "خبر_إنّ"
      "اسم مجرور"               → "اسم_مجرور"
      "مبتدأ مرفوع"             → "مبتدأ"
      "نعت مرفوع"               → "نعت"
      "اسم إنّ منصوب"           → "اسم_إنّ"
    """
    if not phrase:
        return ""
    out = phrase.strip()
    # حَذف تَشكيل
    for d in "ًٌٍَُِّْـ":
        out = out.replace(d, "")
    # حالات خاصَّة: «اسم مجرور» = الرَّول كامِلًا (مَفعول حَرف الجَرّ)
    # نَحفَظه قَبل تَجريد أَيّ لاحِقَة
    if out.startswith("اسم مجرور"):
        return "اسم_مجرور"
    # «اسم (إِنَّ) منصوب» وَ نَظائِرها — الـ engine يَستَخدِم هذه الصيغَة الجَديدَة
    if "اسم (إن" in out or out.startswith("اسم إن") or out.startswith("اسم إنّ"):
        return "اسم_إنّ"
    if "اسم (كان" in out or out.startswith("اسم كان"):
        return "اسم_كان"
    if "خبر (إن" in out or out.startswith("خبر إن") or out.startswith("خبر إنّ"):
        return "خبر_إنّ"
    if "خبر (كان" in out or out.startswith("خبر كان"):
        return "خبر_كان"
    if out.startswith("مفعول به"):
        return "مفعول_به"
    if out.startswith("مفعول لأجله") or out.startswith("مفعول لاجله"):
        return "مفعول_لأجله"
    if out.startswith("مفعول مطلق"):
        return "مفعول_مطلق"
    if out.startswith("مفعول فيه"):
        return "مفعول_فيه"
    if out.startswith("مضاف إليه"):
        return "مضاف_إليه"
    # تَطبيع لاحِقات الحالَة الشَّائِعة (لِـ «فاعل مرفوع»، «مبتدأ مرفوع»، إلخ)
    suffixes_to_strip = (
        " مرفوع", " منصوب", " مجرور", " مجزوم",
        " مبني",
    )
    changed = True
    while changed:
        changed = False
        for suf in suffixes_to_strip:
            if out.endswith(suf):
                out = out[: -len(suf)].strip()
                changed = True
    out = out.strip().replace(" ", "_")
    return out


# ============================================================================
# Extractor
# ============================================================================

class RelationExtractor:

    def __init__(self) -> None:
        self._relation_types = _load_rows("relation_types.csv")
        self._relation_types.sort(key=lambda r: int(r.get("priority", "99")))
        # جَلسة 16: حُروف الجَرّ كَ relation operators
        try:
            self._harf_jarr_relations = _load_rows("harf_jarr_relations.csv")
        except Exception:
            self._harf_jarr_relations = []
        # بِناء فِهرس سَريع: surface_plain → relation_row
        self._harf_jarr_index: dict[str, dict] = {}
        for row in self._harf_jarr_relations:
            harf_plain = row.get("harf_plain", "").strip()
            if harf_plain:
                self._harf_jarr_index[harf_plain] = row
            surfaces = row.get("harf_surfaces", "")
            for surf in [s.strip() for s in surfaces.split("،") if s.strip()]:
                surf_plain = self._strip_diac(surf)
                self._harf_jarr_index.setdefault(surf_plain, row)

    @staticmethod
    def _strip_diac(s: str) -> str:
        # Include extended diacritics: ٰ (dagger alif), ٱ (alef wasla)
        for d in "ًٌٍَُِّْـٰٓ":
            s = s.replace(d, "")
        # Normalize alef wasla to alef so عَلَىٰ → على
        s = s.replace("ٱ", "ا").replace("ى", "ى")
        return s

    def _lookup_harf_jarr(self, harf_surface: str) -> Optional[dict]:
        """يَبحَث عَن قاعِدَة harf_jarr مُطابِقَة للسَّطح. يُجَرِّب بِلا
        تَشكيل أَوّلًا، ثُمَّ بِلا «ال»، ثُمَّ بِلا lam/baa lead."""
        plain = self._strip_diac(harf_surface)
        if plain in self._harf_jarr_index:
            return self._harf_jarr_index[plain]
        # تَجريب أَوَّل حَرف (لِـ بِ، لِـ لِ، كَـ كَ)
        if len(plain) >= 1 and plain[0] in self._harf_jarr_index:
            return self._harf_jarr_index[plain[0]]
        return None

    def extract(self, sent) -> RelationGraph:
        """yields RelationGraph from SentenceI3rab."""
        # Reset contract audit counters at the start of each sentence
        try:
            from agent_agreement_contract import reset_audit as _reset_audit
            _reset_audit()
        except ImportError:
            pass
        try:
            from patient_agreement_contract import reset_audit as _reset_audit_p
            _reset_audit_p()
        except ImportError:
            pass
        g = RelationGraph(source_text=getattr(sent, "text", ""), contract=CONTRACT_NAME)
        tokens = sent.tokens

        # ── Phase 1: build EntityNode for every token ──
        for i, t in enumerate(tokens):
            entity = self._build_entity(t, i)
            g.add_node(entity)

        # ── Phase 2: walk tokens, emit relations ──
        # Context bookkeeping:
        last_verb_idx: Optional[int] = None
        verb_subject_set: dict[int, bool] = {}    # verb_idx → got fa3il?
        last_mubtada_idx: Optional[int] = None
        last_inna_subj_idx: Optional[int] = None
        last_kana_subj_idx: Optional[int] = None
        last_harf_jarr_idx: Optional[int] = None
        consumed_jarrs: set = set()  # MC FIX 2026-05-25: HarfJarr consume tracker
        last_noun_idx: Optional[int] = None       # for مضاف إليه / نعت

        for i, t in enumerate(tokens):
            role_n = _normalize_role(t.role_phrase)
            tid = f"t{i}"

            # ── FIIL: verb anchor + may have prior context (for مجزوم/منصوب) ──
            if t.word_class == "FIIL":
                # verb_in_clause anchor (target = — since no other node)
                g.add_relation(self._build_relation(
                    name="verb_in_clause",
                    kind_type="clause_anchor",
                    source_id=tid,
                    target_id="—",
                    role_kind=t.role_kind or "Hypothesis",
                    source_of_claim=f"word_class:FIIL + verb_in_clause(no_target)",
                ))
                last_verb_idx = i
                verb_subject_set[i] = False
                continue

            # ── HARF: track حرف الجَرّ + إِنَّ + كانَ + النِّداء ──
            if t.word_class == "HARF":
                if t.closed_class_kind == "HARF_JARR":
                    last_harf_jarr_idx = i
                # حِفظ إِنَّ-marker لِاستِخدامه كَ target لِـ inna_topic_of
                surface_plain = getattr(t, "token_plain", "") or _normalize_role(getattr(t, "token", ""))
                # تَطبيع surface_plain لِفَحص إِنَّ
                from relation_extractor import _normalize_role as _nr
                tk_plain = "".join(c for c in (getattr(t, "token", "") or "") if c not in "ًٌٍَُِّْـ")
                if tk_plain in {"إن", "أن", "كأن", "ليت", "لعل", "لكن"}:
                    last_inna_subj_idx = i
                continue

            # ── role-based dispatch ──

            # فاعل → agent_of(token, last_verb) — عَبر AgentAgreementContract
            # MC FIX 2026-05-25: DefectiveVerbContract — لَو الفِعل ناقِص
            # (كان/ليس/صار...) فالعَلاقَة ism_of_kana لا agent_of.
            if role_n == "فاعل":
                if last_verb_idx is not None:
                    v_tok = tokens[last_verb_idx]
                    _is_defective = False
                    try:
                        from defective_verb_contract import check_defective_verb
                        _dv = check_defective_verb(
                            getattr(v_tok, "token", "") or "",
                            lemma_hint=getattr(v_tok, "lemma", "") or "",
                        )
                        _is_defective = _dv.is_defective
                    except ImportError:
                        _dv = None
                    # PATCH 12 — block ism_of_kana when the source is an
                    # apodosis-headed noun (فَرَجُلٌ in «إن لم يكونا
                    # رجلين فرجل ...»). The فَ is the جواب-of-conditional
                    # marker; the noun starts a new sentence and is NOT
                    # the اسم of the prior كان-class verb.
                    if (_is_defective and _dv is not None
                            and _p12_source_is_apodosis_fa(t)):
                        _is_defective = False
                    if _is_defective and _dv is not None:
                        # كان وَأَخواتُها — هَذا اسم كان لا فاعل
                        g.add_relation(self._build_relation(
                            name=_dv.topic_relation or "ism_of_kana",
                            kind_type="kana_topic",
                            source_id=tid,
                            target_id=f"t{last_verb_idx}",
                            role_kind=t.role_kind or "Hypothesis",
                            source_of_claim=(
                                f"role:فاعل + DefectiveVerbContract:{_dv.lemma}"
                                f" → {_dv.topic_relation}"
                            ),
                        ))
                        verb_subject_set[last_verb_idx] = True
                    else:
                        # MC FIX 2026-05-25: AgentWindowContract — قَبل إِصدار
                        # agent_of، نَتَأَكَّد أَنّ الاسم في نافِذَة صالِحَة
                        # (لا حَرف جَرّ، لا مَفعول صَريح، لا تَفضيل، لا خَبَر،
                        # وَلَيس لِلفِعل فاعِل مُستَتِر أَقوى).
                        _window_block = False
                        try:
                            from agent_window_contract import evaluate_agent_window
                            # نُحاوِل اكتِشاف has_implicit_agent مِن aspect
                            _v_aspect = getattr(v_tok, "verb_aspect", "") or ""
                            _v_mood = getattr(v_tok, "verb_mood", "") or ""
                            _has_implicit = (_v_aspect == "CV" or _v_mood in ("JUSS", "IMPER"))
                            _aw = evaluate_agent_window(
                                v_token=v_tok, x_token=t,
                                all_tokens=tokens,
                                verb_idx=last_verb_idx, noun_idx=i,
                                has_implicit_agent=_has_implicit,
                            )
                            if _aw.kind == "Zero":
                                # نَرفُض إِصدار agent_of
                                _window_block = True
                                # تَسجيل الـsuppression
                                try:
                                    from agent_agreement_contract import mark_suppressed
                                    mark_suppressed()
                                except ImportError:
                                    pass
                        except ImportError:
                            pass
                        if not _window_block:
                            rel = self._build_agent_via_contract(
                                x_token=t,
                                v_token=v_tok,
                                source_id=tid,
                                target_id=f"t{last_verb_idx}",
                                position_evidence=f"role:فاعل + last_verb_idx:{last_verb_idx}",
                            )
                            if rel is not None:
                                g.add_relation(rel)
                                verb_subject_set[last_verb_idx] = True
                last_noun_idx = i

            # مفعول به → patient_of(token, last_verb) — عَبر PatientAgreementContract
            # MC FIX 2026-05-25: DefectiveVerbContract — لَو الفِعل ناقِص،
            # المَنصوب هُو خَبَر كان لا مَفعول.
            elif role_n in ("مفعول_به", "مفعولٌ_به", "مفعول"):
                # PATCH 7 — L4 Relation Safety Gate.
                # (a) Temporal/conditional particles (إِذَا, إِذ, لَمَّا, ...)
                #     are mis-labelled "مفعول به" by L3 sometimes. They are
                #     ظَرف / أَداة شَرط, never a true verb patient.
                # (b) HARF / particle tokens are never patients.
                if _p7_is_temporal_or_conditional_particle(t):
                    last_noun_idx = i
                    continue
                if t.word_class == "HARF":
                    last_noun_idx = i
                    continue
                # PatientWindowContract (R): تَقديم المَفعول.
                # لَو الـtoken الحاليّ مَنصوب وَ مَسبوق بِفاء/واو
                # وَ يَلِيه فِعل مُباشَرَة → الفِعل التالي هُوَ الناصِب،
                # لَيس last_verb_idx (الَّذي قَد يَكون في جُملَة سابِقَة).
                # مَثَل 5:70: «فَرِيقًا كَذَّبُوا» — فَرِيقًا مَفعول كَذَّبُوا
                # لَيس مَفعول تَهْوَىٰ في الجُملَة السابِقَة.
                _forward_verb_idx = None
                _surf = getattr(t, "token", "") or ""
                if _surf.startswith(("فَ","وَ","ف","و")):
                    # ابحَث عَن أَوَّل فِعل بَعد الـtoken (حَتَّى 4 tokens)
                    for j in range(i+1, min(i+5, len(tokens))):
                        if getattr(tokens[j], "word_class", "") == "FIIL":
                            _forward_verb_idx = j
                            break
                        # لَو وُجِد اسم آخَر، نَتَوَقَّف (لا نَعبُر الـnoun phrases)
                        if getattr(tokens[j], "word_class", "") in (
                            "ISM_MUARAB","ISM_MABNI","JAMID"):
                            break
                # نَستَخدِم متَغَيِّر مَحَلّيّ لِئَلّا نُلَوِّث last_verb_idx
                # لِلتَّكرارات اللاحِقَة
                _attach_to_idx = _forward_verb_idx if _forward_verb_idx is not None else last_verb_idx
                if _attach_to_idx is not None:
                    v_tok = tokens[_attach_to_idx]
                    _is_defective = False
                    try:
                        from defective_verb_contract import check_defective_verb
                        _dv2 = check_defective_verb(
                            getattr(v_tok, "token", "") or "",
                            lemma_hint=getattr(v_tok, "lemma", "") or "",
                        )
                        _is_defective = _dv2.is_defective
                    except ImportError:
                        _dv2 = None
                    if _is_defective and _dv2 is not None:
                        # كان وَأَخواتُها — المَنصوب خَبَر كان لا مَفعول
                        g.add_relation(self._build_relation(
                            name=_dv2.comment_relation or "khabar_of_kana",
                            kind_type="kana_comment",
                            source_id=tid,
                            target_id=f"t{_attach_to_idx}",
                            role_kind=t.role_kind or "Hypothesis",
                            source_of_claim=(
                                f"role:مفعول_به + DefectiveVerbContract:{_dv2.lemma}"
                                f" → {_dv2.comment_relation}"
                            ),
                        ))
                    else:
                        prev_tok = tokens[i - 1] if i > 0 else None
                        _ev = ("role:مفعول_به + forward_verb_idx:" + str(_forward_verb_idx)
                               if _forward_verb_idx is not None
                               else f"role:مفعول_به + last_verb_idx:{_attach_to_idx}")
                        rel = self._build_patient_via_contract(
                            x_token=t, v_token=v_tok,
                            source_id=tid, target_id=f"t{_attach_to_idx}",
                            prev_token=prev_tok,
                            position_evidence=_ev,
                        )
                        if rel is not None:
                            g.add_relation(rel)
                last_noun_idx = i

            # مضاف إليه → possessor_of(token, prev_noun)
            elif role_n in ("مضاف_إليه", "مضافٌ_إليه"):
                # PATCH 7 — L4 Relation Safety Gate (PP-not-إضافة).
                # If the token carries a PREP-peeled prefix (بِ / لِ / كِ),
                # it is the noun of a جار+مجرور phrase, NOT a مضاف-إليه
                # to whatever last_noun_idx happens to be. Example from
                # 2:282: بِكُلِّ شَىْءٍ — بِكُلِّ should NOT become
                # possessor_of وَٱللَّهُ; it's an adverbial PP.
                if _p7_token_has_prep_prefix(t):
                    last_noun_idx = i
                    continue
                # PATCH 12 — block possessor_of when the TARGET is a
                # locative ظَرف noun (عِندَ / بَيْنَ / تَحْتَ / فَوْقَ).
                # «عِندَ ٱللَّهِ» — ٱللَّهِ is the مَعمول of the locative,
                # NOT a possessor of عِندَ. Emitting possessor_of here
                # would mislead L5/L6/L8 ("does Allah possess عِندَ?").
                if last_noun_idx is not None and last_noun_idx != i:
                    if _p12_target_is_locative_zarf(tokens[last_noun_idx]):
                        last_noun_idx = i
                        continue
                if last_noun_idx is not None and last_noun_idx != i:
                    g.add_relation(self._build_relation(
                        name="possessor_of",
                        kind_type="possession",
                        source_id=tid,
                        target_id=f"t{last_noun_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:مضاف_إليه + last_noun_idx:{last_noun_idx} + relation_types:possessor_of",
                    ))
                last_noun_idx = i

            # نعت → attribute_of(token, prev_noun)
            # MC FIX 2026-05-25: AttributeAgreementContract — يَفحَص المُطابَقَة
            elif role_n == "نعت":
                if last_noun_idx is not None and last_noun_idx != i:
                    _emit_attr = True
                    # PATCH 7 — L4 Relation Safety Gate (jalalah-attribute loop).
                    # وَٱللَّهُ following ٱللَّهُ across a clause is a coordinated
                    # subject of a new clause, not a نعت of the prior لَفظ
                    # الجَلالَة. Block when BOTH source and target are JALALAH
                    # AND source carries a CONJ prefix (وَ / فَ).
                    if (
                        _p7_is_jalalah(t)
                        and _p7_is_jalalah(tokens[last_noun_idx])
                        and _p7_token_starts_with_conjunction(t)
                    ):
                        _emit_attr = False
                    # PATCH 12 — block attribute_of when the TARGET is
                    # a PP-headed noun (بِكُلِّ). شَىْءٍ → بِكُلِّ is
                    # mis-emitted because شَىْءٍ has role=نعت (case
                    # agreement with بِكُلِّ); but inside «بِكُلِّ
                    # شَىْءٍ» the شَىْءٍ is مُضاف-إِليه to كُلِّ, not a
                    # نعت of the whole PP head.
                    if _emit_attr and _p12_target_has_prep_prefix(tokens[last_noun_idx]):
                        _emit_attr = False
                    if _emit_attr:
                        try:
                            from attribute_agreement_contract import evaluate_attribute
                            _av = evaluate_attribute(
                                x_token=t, y_token=tokens[last_noun_idx],
                                x_idx=i, y_idx=last_noun_idx,
                                all_tokens=tokens,
                            )
                            if _av.kind == "Zero":
                                _emit_attr = False
                        except ImportError:
                            pass
                    if _emit_attr:
                        g.add_relation(self._build_relation(
                            name="attribute_of",
                            kind_type="attribute",
                            source_id=tid,
                            target_id=f"t{last_noun_idx}",
                            role_kind=t.role_kind or "Hypothesis",
                            source_of_claim=f"role:نعت + last_noun_idx:{last_noun_idx} + relation_types:attribute_of",
                        ))
                last_noun_idx = i

            # مبتدأ → topic_anchor + remember for خبر
            elif role_n == "مبتدأ":
                g.add_relation(self._build_relation(
                    name="topic_anchor",
                    kind_type="clause_anchor",
                    source_id=tid,
                    target_id="—",
                    role_kind=t.role_kind or "Hypothesis",
                    source_of_claim=f"role:مبتدأ + relation_types:topic_anchor",
                ))
                last_mubtada_idx = i
                last_noun_idx = i

            # خبر → comment_of(token, last_mubtada)
            elif role_n == "خبر":
                if last_mubtada_idx is not None:
                    g.add_relation(self._build_relation(
                        name="comment_of",
                        kind_type="topic_comment",
                        source_id=tid,
                        target_id=f"t{last_mubtada_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:خبر + last_mubtada_idx:{last_mubtada_idx} + relation_types:comment_of",
                    ))
                last_noun_idx = i

            # اسم إنّ → inna_topic_of
            elif role_n in ("اسم_إنّ", "اسم_إن"):
                # target = the إِنّ harf itself; we use last_inna_subj_idx as a placeholder
                if last_inna_subj_idx is not None and last_inna_subj_idx != i:
                    g.add_relation(self._build_relation(
                        name="inna_topic_of",
                        kind_type="topic_comment",
                        source_id=tid,
                        target_id=f"t{last_inna_subj_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:اسم_إنّ + harf_inna_idx:{last_inna_subj_idx} + relation_types:inna_topic_of",
                    ))
                last_inna_subj_idx = i  # now THIS is the subject
                last_noun_idx = i

            # خبر إنّ → inna_comment_of
            elif role_n in ("خبر_إنّ", "خبر_إن"):
                if last_inna_subj_idx is not None and last_inna_subj_idx != i:
                    g.add_relation(self._build_relation(
                        name="inna_comment_of",
                        kind_type="topic_comment",
                        source_id=tid,
                        target_id=f"t{last_inna_subj_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:خبر_إنّ + inna_subj:{last_inna_subj_idx} + relation_types:inna_comment_of",
                    ))
                last_noun_idx = i

            # اسم مجرور → harf_jarr_of + relation مُتَخَصِّصَة (in_location/...) مِن harf_jarr_relations.csv
            # MC FIX 2026-05-25: HarfJarrAgreementContract — يَفحَص الـwindow
            # وَ يَستَهلِك الـharf بَعد أَوَّل مُتَعَلِّق صالِح.
            elif role_n in ("اسم_مجرور", "مجرور"):
                if last_harf_jarr_idx is not None and last_harf_jarr_idx != i:
                    harf_surface = tokens[last_harf_jarr_idx].token
                    _emit_jarr = True
                    try:
                        from harf_jarr_agreement_contract import evaluate_harf_jarr
                        _hjv = evaluate_harf_jarr(
                            h_token=tokens[last_harf_jarr_idx],
                            x_token=t,
                            all_tokens=tokens,
                            h_idx=last_harf_jarr_idx,
                            x_idx=i,
                            consumed_jarrs=consumed_jarrs,
                        )
                        if _hjv.kind == "Zero":
                            _emit_jarr = False
                    except ImportError:
                        pass
                    if _emit_jarr:
                        # العَلاقَة الأَساسيَّة العامَّة
                        g.add_relation(self._build_relation(
                            name="harf_jarr_of",
                            kind_type="prep_phrase",
                            source_id=tid,
                            target_id=f"t{last_harf_jarr_idx}",
                            operator=harf_surface,
                            role_kind=t.role_kind or "Hypothesis",
                            source_of_claim=f"role:اسم_مجرور + harf_jarr_idx:{last_harf_jarr_idx} + operator:{harf_surface}",
                        ))
                        # العَلاقَة المُتَخَصِّصَة (locative/goal/source/...) إِن وُجِدَت
                        rule = self._lookup_harf_jarr(harf_surface)
                        if rule:
                            g.add_relation(self._build_relation(
                                name=rule.get("creates_relation", "harf_jarr_specialized"),
                                kind_type=rule.get("relation_kind", "prep_phrase"),
                                source_id=tid,
                                target_id=f"t{last_harf_jarr_idx}",
                                operator=harf_surface,
                                role_kind=t.role_kind or "Hypothesis",
                                source_of_claim=(
                                    f"role:اسم_مجرور + harf_jarr:{harf_surface} + "
                                    f"harf_jarr_relations:{rule.get('name','?')}"
                                ),
                            ))
                        # CONSUME: حَرف الجَرّ يُستَهلَك
                        consumed_jarrs.add(last_harf_jarr_idx)
                        last_harf_jarr_idx = None
                last_noun_idx = i

            # معطوف → coordinate_of(token, prev_noun)
            elif role_n == "معطوف":
                if last_noun_idx is not None and last_noun_idx != i:
                    g.add_relation(self._build_relation(
                        name="coordinate_of",
                        kind_type="coordination",
                        source_id=tid,
                        target_id=f"t{last_noun_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:معطوف + last_noun_idx:{last_noun_idx} + relation_types:coordinate_of",
                    ))
                last_noun_idx = i

            # ── Phase C COMPLETION: 5 relations جَديدَة ────────────────────

            # مَفعول ثانٍ → patient2_of (لِأَفعال: أَعطى، كَسا، أَلبَسَ، ظَنَّ، حَسِبَ...)
            elif role_n in ("مفعول_به_ثان", "مفعول_ثان", "مفعول_ثاني"):
                if last_verb_idx is not None:
                    g.add_relation(self._build_relation(
                        name="patient2_of",
                        kind_type="subj_pred",
                        source_id=tid,
                        target_id=f"t{last_verb_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:مفعول_به_ثان + last_verb_idx:{last_verb_idx} + relation_types:patient2_of",
                    ))
                last_noun_idx = i

            # اسم كانَ → kana_topic_of
            elif role_n in ("اسم_كان", "اسم_كانَ"):
                # نَستَخدِم last_kana_subj_idx — يَلتَقِط كانَ كَـ HARF أَو FIIL سابِق
                # placeholder: لَو لَم نُلتَقِط كانَ، نَستَخدِم last_verb_idx
                target_idx = last_kana_subj_idx if last_kana_subj_idx is not None else last_verb_idx
                if target_idx is not None and target_idx != i:
                    g.add_relation(self._build_relation(
                        name="kana_topic_of",
                        kind_type="topic_comment",
                        source_id=tid,
                        target_id=f"t{target_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:اسم_كان + kana_idx:{target_idx} + relation_types:kana_topic_of",
                    ))
                last_kana_subj_idx = i
                last_noun_idx = i

            # خَبَر كانَ → kana_comment_of
            elif role_n in ("خبر_كان", "خبر_كانَ"):
                if last_kana_subj_idx is not None and last_kana_subj_idx != i:
                    g.add_relation(self._build_relation(
                        name="kana_comment_of",
                        kind_type="topic_comment",
                        source_id=tid,
                        target_id=f"t{last_kana_subj_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:خبر_كان + kana_subj:{last_kana_subj_idx} + relation_types:kana_comment_of",
                    ))
                last_noun_idx = i

            # بَدَل → substitute_of(token, prev_noun)
            elif role_n in ("بدل", "بَدَل"):
                if last_noun_idx is not None and last_noun_idx != i:
                    g.add_relation(self._build_relation(
                        name="substitute_of",
                        kind_type="apposition",
                        source_id=tid,
                        target_id=f"t{last_noun_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:بدل + last_noun_idx:{last_noun_idx} + relation_types:substitute_of",
                    ))
                last_noun_idx = i

            # مُنادى → vocative_of (target = حَرف نِداء سابِق، أَو "—")
            elif role_n in ("منادى", "مُنادى"):
                # ابحَث عَن حَرف نِداء سابِق (يا، أَيا، هَيا)
                vocative_marker_idx = None
                for j in range(i - 1, max(-1, i - 3), -1):
                    prev_tok = tokens[j]
                    prev_text = getattr(prev_tok, "token", "") or ""
                    if prev_text in ("يا", "يَا", "أَيا", "أَيَا", "هَيا", "هَيَا", "أَ"):
                        vocative_marker_idx = j
                        break
                target = f"t{vocative_marker_idx}" if vocative_marker_idx is not None else "—"
                g.add_relation(self._build_relation(
                    name="vocative_of",
                    kind_type="vocative",
                    source_id=tid,
                    target_id=target,
                    role_kind=t.role_kind or "Hypothesis",
                    source_of_claim=f"role:منادى + nida_marker_idx:{vocative_marker_idx}",
                ))
                last_noun_idx = i

            # any other ISM → just remember as last_noun
            else:
                # MC: SINGULAR_TERM (لَفظ الجَلالَة) يَكون كَ noun لِأَغراض العَلاقات
                if t.word_class in ("ISM_MUARAB", "JAMID", "AALAM", "JALALAH", "SINGULAR_TERM"):
                    last_noun_idx = i

        # ── Phase C 100%: post-detection لِسَدّ ما يَفوت i3rab ──
        self._post_detect_missed_relations(g, tokens)

        return g

    # ──────────────────────────────────────────────────────────
    # POST-DETECTION (Phase C 100% — heuristic rules)
    # ──────────────────────────────────────────────────────────

    # كانَ وَ أَخَواتها — مَخزون في CSV لاحِقًا، حاليًّا inline لِلسُّرعَة
    _KANA_FAMILY_SURFACES = {
        "كانَ", "كان", "كانَت", "كانت", "كانوا", "كنتم", "كنتُ",
        "صارَ", "صار", "أَصبَحَ", "اصبح", "أَمسَى", "امسى",
        "أَضحَى", "اضحى", "باتَ", "بات", "ظَلَّ", "ظل",
        "ليسَ", "ليس", "ما زالَ", "ما زال",
    }
    _VOCATIVE_MARKERS = {"يا", "يَا", "أَيا", "أَيَا", "هَيا", "هَيَا"}

    # ── Detached pronouns cache (loaded from CSV — MC compliant) ──
    _DETACHED_PRONOUNS_CACHE: dict | None = None
    # ── Implicit-agent rules cache (IV prefix → pronoun) ──
    _IMPLICIT_AGENTS_CACHE: list | None = None

    @classmethod
    def _load_implicit_agents(cls) -> list:
        """يُحَمِّل implicit_agents.csv — قَواعِد البادِئَة → ضَمير مُستَتِر."""
        if cls._IMPLICIT_AGENTS_CACHE is not None:
            return cls._IMPLICIT_AGENTS_CACHE
        import csv as _csv
        from pathlib import Path
        path = Path(__file__).resolve().parent / "data" / "contracts" / "lists" / "implicit_agents.csv"
        rows: list = []
        if path.exists():
            with open(path, encoding="utf-8") as f:
                for row in _csv.DictReader(f):
                    rows.append(row)
        # رَتِّب: قَواعِد بِـ verb_suffix_pattern قَبل العامَّة (longer first)
        rows.sort(key=lambda r: (-len(r.get("verb_suffix_pattern", "") or ""),
                                  r.get("iv_prefix_plain", "")))
        cls._IMPLICIT_AGENTS_CACHE = rows
        return rows

    @classmethod
    def _load_detached_pronouns(cls) -> dict:
        """يُحَمِّل detached_pronouns.csv — يُعيد dict مُفَهرَس بِالسَّطح وَ المُجَرَّد."""
        if cls._DETACHED_PRONOUNS_CACHE is not None:
            return cls._DETACHED_PRONOUNS_CACHE
        import csv as _csv
        import unicodedata
        from pathlib import Path
        path = Path(__file__).resolve().parent / "data" / "contracts" / "lists" / "detached_pronouns.csv"
        idx: dict = {}
        if path.exists():
            with open(path, encoding="utf-8") as f:
                for row in _csv.DictReader(f):
                    surface = unicodedata.normalize("NFC", row.get("surface", "").strip())
                    plain = row.get("plain", "").strip()
                    if surface:
                        idx[surface] = row
                    if plain:
                        idx.setdefault(plain, row)
        cls._DETACHED_PRONOUNS_CACHE = idx
        return idx

    @staticmethod
    def _strip_diac_static(s: str) -> str:
        for d in "ًٌٍَُِّْـ":
            s = s.replace(d, "")
        return s

    def _post_detect_missed_relations(self, g, tokens):
        """يَكشِف 5 أَنواع relations لا يُغَطّيها i3rab صَريحًا.

        Phase C completion — heuristic rule-based.
        """
        # ── 1. اسم كان + خَبَر كان ──
        for i, t in enumerate(tokens):
            tk = getattr(t, "token", "") or ""
            if tk in self._KANA_FAMILY_SURFACES:
                # المَرفوع التَّالي = اسم كان، المَنصوب بَعده = خَبَر كان
                kana_idx = i
                kana_subj_idx = None
                kana_pred_idx = None
                for j in range(i + 1, min(i + 6, len(tokens))):
                    tj = tokens[j]
                    if tj.word_class not in ("ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM"):
                        continue
                    role_p = (getattr(tj, "role_phrase", "") or "")
                    # heuristic: أَوَّل اسم = اسم كان، الَّذي يَليه = خَبَرها
                    if kana_subj_idx is None:
                        kana_subj_idx = j
                    elif kana_pred_idx is None:
                        kana_pred_idx = j
                        break

                if kana_subj_idx is not None:
                    g.add_relation(self._build_relation(
                        name="kana_topic_of",
                        kind_type="topic_comment",
                        source_id=f"t{kana_subj_idx}",
                        target_id=f"t{kana_idx}",
                        role_kind="Hypothesis",
                        source_of_claim=f"post_detect: kana_surface:{tk} + next_ism:{kana_subj_idx}",
                    ))
                if kana_pred_idx is not None:
                    g.add_relation(self._build_relation(
                        name="kana_comment_of",
                        kind_type="topic_comment",
                        source_id=f"t{kana_pred_idx}",
                        target_id=f"t{kana_subj_idx}",
                        role_kind="Hypothesis",
                        source_of_claim=f"post_detect: kana_pred:{kana_pred_idx} → kana_subj:{kana_subj_idx}",
                    ))

        # ── 2. مَفعول ثانٍ — يَأتي بَعد مَفعول أَوَّل لِأَفعال مُتَعَدِّيَة لِاثنَين ──
        # نَكشِف: لَو نَفس الفِعل لَه patient_of (1) وَ بَعده اسم مَنصوب آخَر
        # حَتَّى لَو الـ engine صَنَّفه نعت — نَتَجاوَز ذلِك (override)
        patients_by_verb = {}
        for r in g.relations:
            if r.name == "patient_of":
                patients_by_verb.setdefault(r.target_id, []).append(r.source_id)
        # ditrans_verbs heuristic: أَفعال يُعطي ونَحوها
        DITRANS_ROOTS = {"عطي", "كسو", "لبس", "علم", "ظنن", "حسب",
                         "خيل", "زعم", "وجد", "جعل", "اتخذ", "ري"}
        for verb_id, patients in patients_by_verb.items():
            verb_idx = int(verb_id[1:])
            if verb_idx >= len(tokens):
                continue
            verb_root = (tokens[verb_idx].root or "").strip()
            # نَفعَل فَقَط لَو الفِعل مَن DITRANS، أَو لَو يَوجَد اسم مَنصوب آخَر
            first_patient_pos = int(patients[0][1:])
            for j in range(first_patient_pos + 1, min(first_patient_pos + 4, len(tokens))):
                tj = tokens[j]
                if tj.word_class not in ("ISM_MUARAB", "JAMID", "AALAM"):
                    continue
                surface = getattr(tj, "token", "") or ""
                is_nasb = surface.endswith(("ًا", "اً", "ةً", "َ"))
                if not is_nasb:
                    continue
                if f"t{j}" in patients:
                    continue
                # PATCH 12 — patient2_of safety gate.
                # The original heuristic over-fires: it labels ANY
                # second منصوب-tanwin noun after a verb as patient2_of,
                # even when (a) the verb is NOT ditransitive, and
                # (b) the two nouns are coordinated حال/صفة separated
                # by أَوْ / و (صَغِيرًا أَوْ كَبِيرًا → both are size
                # حال, not two distinct patients).
                if _p12_should_skip_patient2(verb_root, tokens,
                                              first_patient_pos, j):
                    continue
                # override: نَحذِف أَيّ attribute_of لِهذا الـ token (لأنّه مَفعول ثانٍ)
                g.relations = [r for r in g.relations
                                if not (r.name == "attribute_of" and r.source_id == f"t{j}")]
                g.add_relation(self._build_relation(
                    name="patient2_of",
                    kind_type="subj_pred",
                    source_id=f"t{j}",
                    target_id=verb_id,
                    role_kind="Hypothesis",
                    source_of_claim=f"post_detect: ditrans verb (root:{verb_root}) → patient2:{j}",
                ))
                break  # فَقَط واحِد

        # ── 3. مُنادى — بَعد يا/أَيا/هَيا (+ أَيُّها/أَيَّتُها) ──
        for i, t in enumerate(tokens):
            tk = getattr(t, "token", "") or ""
            if tk in self._VOCATIVE_MARKERS:
                # المُنادى = الـ token التَّالي إِذا كانَ اسمًا
                # حالَة خاصَّة: يا أَيُّها النَّاسُ → نَتَخَطّى «أَيُّها»/«أَيَّتُها»
                target_j = None
                for k in range(i + 1, min(i + 4, len(tokens))):
                    next_tok = tokens[k]
                    next_text = getattr(next_tok, "token", "") or ""
                    if next_text in ("أَيُّها", "أَيُّهَا", "أَيَّتُها", "أَيَّتُهَا",
                                     "أيها", "أيتها"):
                        # «أَيّ» وَسيط — المُنادى الفِعليّ يَأتي بَعده
                        continue
                    if next_tok.word_class in ("ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM"):
                        target_j = k
                        break
                if target_j is not None:
                    g.add_relation(self._build_relation(
                        name="vocative_of",
                        kind_type="vocative",
                        source_id=f"t{target_j}",
                        target_id=f"t{i}",
                        role_kind="Certificate",
                        source_of_claim=f"post_detect: nida_marker:{tk} + next_ism:{target_j}",
                    ))

        # ── 5b. الأَفعال الأَجوَف الماضِيَة (جاءَ، قالَ، صارَ، باتَ، ساءَ، شاءَ...) ──
        # الـ engine يَفوتها لأنّها 3 حُروف فَقَط، يُصَنِّفها ISM_MUARAB خَطَأً
        HOLLOW_PAST_VERBS = {
            "جاءَ", "جاء", "قالَ", "قال", "كانَ", "كان", "صارَ", "صار",
            "باتَ", "بات", "ساءَ", "ساء", "شاءَ", "شاء", "ماتَ", "مات",
            "نامَ", "نام", "قامَ", "قام", "خافَ", "خاف", "خانَ", "خان",
            "زالَ", "زال", "مالَ", "مال", "طالَ", "طال", "نالَ", "نال",
            "دامَ", "دام", "حانَ", "حان", "بانَ", "بان", "هانَ", "هان",
            "رامَ", "رام", "فازَ", "فاز", "جازَ", "جاز", "دارَ", "دار",
            "ثارَ", "ثار", "سارَ", "سار", "غارَ", "غار", "زارَ", "زار",
        }
        for i, t in enumerate(tokens):
            tk = getattr(t, "token", "") or ""
            if t.word_class == "FIIL":
                continue
            if tk not in HOLLOW_PAST_VERBS:
                continue
            # ابحَث عَن المَرفوع التَّالي = فاعِل
            for j in range(i + 1, min(i + 4, len(tokens))):
                tj = tokens[j]
                if tj.word_class not in ("ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM"):
                    continue
                ts = getattr(tj, "token", "") or ""
                if not ts.endswith(("ٌ", "ُ", "ون", "ونَ", "ان", "انِ")):
                    continue
                # عَلِّمه فِعل + فاعِل
                g.add_relation(self._build_relation(
                    name="verb_in_clause", kind_type="clause_anchor",
                    source_id=f"t{i}", target_id="—",
                    role_kind="Hypothesis",
                    source_of_claim=f"post_detect: hollow past verb:{tk}",
                ))
                # عَبر AgentAgreementContract
                _rel_hp = self._build_agent_via_contract(
                    x_token=tokens[j], v_token=tokens[i],
                    source_id=f"t{j}", target_id=f"t{i}",
                    position_evidence=f"post_detect: rafa after hollow_past:{tk}",
                )
                if _rel_hp is not None:
                    g.add_relation(_rel_hp)
                break

        # ── 5. الأَفعال الَّتي يَفوتها الـ engine (ضَمير المُتَكَلِّم/المُخاطَب) ──
        # ظَنَنتُ، حَسِبتُ، كَتَبتُ، عَلِمنا، أَخَذتُم... يُصَنَّفها الـ engine خَطَأً
        PAST_VERB_SUFFIXES = ("تُ", "تَ", "تِ", "نا", "تُم", "تُن", "تما")
        for i, t in enumerate(tokens):
            surface = getattr(t, "token", "") or ""
            # تَخَطّى الَّذي صُنِّف FIIL بالفِعل
            if t.word_class == "FIIL":
                continue
            # هَل يَنتَهي بِلاحِقَة فِعليَّة + لا يَبدَأ بِال؟
            if not any(surface.endswith(sfx) for sfx in PAST_VERB_SUFFIXES):
                continue
            if surface.startswith("ال") or surface.startswith("الـ"):
                continue
            # يَجِب أَن يَكون أَوَّل token تَقريبًا (i ≤ 1)
            if i > 1:
                continue
            # ابحَث عَن مَنصوبَين بَعده
            nasb_positions = []
            for j in range(i + 1, min(i + 5, len(tokens))):
                tj = tokens[j]
                if tj.word_class not in ("ISM_MUARAB", "JAMID", "AALAM"):
                    continue
                ts = getattr(tj, "token", "") or ""
                if ts.endswith(("ًا", "اً", "ةً", "َ")):
                    nasb_positions.append(j)
            # نَحذِف أَيّ attribute بَين الـ nasbs (إِنشاء patient + patient2)
            for j in nasb_positions:
                g.relations = [r for r in g.relations
                                if not (r.name == "attribute_of" and r.source_id == f"t{j}")]
            # نُسَجِّل: الفِعل verb_in_clause + patient + patient2
            if nasb_positions:
                g.add_relation(self._build_relation(
                    name="verb_in_clause", kind_type="clause_anchor",
                    source_id=f"t{i}", target_id="—",
                    role_kind="Hypothesis",
                    source_of_claim=f"post_detect: past verb by suffix:{surface}",
                ))
                # عَبر PatientAgreementContract
                _np = nasb_positions[0]
                _prev = tokens[_np - 1] if _np > 0 else None
                _rel_p = self._build_patient_via_contract(
                    x_token=tokens[_np], v_token=tokens[i],
                    source_id=f"t{_np}", target_id=f"t{i}",
                    prev_token=_prev,
                    position_evidence="post_detect: nasb after past_verb",
                )
                if _rel_p is not None:
                    g.add_relation(_rel_p)
                if len(nasb_positions) >= 2:
                    g.add_relation(self._build_relation(
                        name="patient2_of", kind_type="subj_pred",
                        source_id=f"t{nasb_positions[1]}", target_id=f"t{i}",
                        role_kind="Hypothesis",
                        source_of_claim=f"post_detect: second nasb after past_verb",
                    ))

        # ── 6. فاعِل-بَعد-فِعل (heuristic) — لِحالات الـ engine يُسَمّيها خَبَر خَطَأً ──
        # رَفع بَعد فِعل + قَبل ظَرف/أَداة عَطف = فاعِل
        existing_agents = {r.source_id for r in g.relations if r.name == "agent_of"}
        for verb_idx in [int(r.source_id[1:]) for r in g.relations if r.name == "verb_in_clause"]:
            # ابحَث عَن أَوَّل اسم مَرفوع بَعد الفِعل
            for j in range(verb_idx + 1, min(verb_idx + 4, len(tokens))):
                tj = tokens[j]
                if tj.word_class not in ("ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM"):
                    continue
                if f"t{j}" in existing_agents:
                    break  # agent مَوجود فِعلًا
                # heuristic: مَرفوع لَو يَنتَهي بِـ ٌ/ُ/ون/ان
                ts = getattr(tj, "token", "") or ""
                is_rafa = ts.endswith(("ٌ", "ُ", "ون", "ونَ", "ان", "انِ"))
                if not is_rafa:
                    continue
                # تَخَطّى لَو لَه role صَريح فاعِل/خَبَر/مُبتَدَأ
                role_p = (getattr(tj, "role_phrase", "") or "")
                # MC FIX 2026-05-25: AgentWindowContract — يَفحَص الـwindow
                # قَبل إِصدار agent_of (يَكشِف خَبَر إِنَّ، مَنصوب فاصِل…).
                try:
                    from agent_window_contract import evaluate_agent_window
                    _aw_pd = evaluate_agent_window(
                        v_token=tokens[verb_idx], x_token=tj,
                        all_tokens=tokens,
                        verb_idx=verb_idx, noun_idx=j,
                    )
                    if _aw_pd.kind == "Zero":
                        try:
                            from agent_agreement_contract import mark_suppressed
                            mark_suppressed()
                        except ImportError:
                            pass
                        break
                except ImportError:
                    pass
                # عَبر AgentAgreementContract
                _rel_pd = self._build_agent_via_contract(
                    x_token=tj, v_token=tokens[verb_idx],
                    source_id=f"t{j}", target_id=f"t{verb_idx}",
                    position_evidence=f"post_detect: first rafa after verb (engine said:{role_p})",
                )
                if _rel_pd is not None:
                    g.add_relation(_rel_pd)
                break

        # ── 7. نَعت-مُتَتالي (engine يُسَمّيه خَبَر بَين أَسماء مَع ال) ──
        for i in range(1, len(tokens)):
            t1 = tokens[i - 1]
            t2 = tokens[i]
            if t1.word_class not in ("ISM_MUARAB", "JAMID", "AALAM"):
                continue
            if t2.word_class not in ("ISM_MUARAB", "JAMID", "AALAM"):
                continue
            s1 = getattr(t1, "token", "") or ""
            s2 = getattr(t2, "token", "") or ""
            # كِلاهُما يَبدَأ بِـ ال + نَفس الحالَة (rafa شائِع لِلنَّعت)
            if not (s1.startswith("ال") and s2.startswith("ال")):
                continue
            # كِلاهُما مَرفوع (heuristic مِن السَّطح)
            both_rafa = s1.endswith(("ٌ", "ُ")) and s2.endswith(("ٌ", "ُ"))
            if not both_rafa:
                continue
            # تَأَكَّد لَيس مُسَجَّل كَ substitute (لِأنّ كِلَيهما مَعرِفَة)
            already_sub = any(
                r.name == "substitute_of" and r.source_id == f"t{i}"
                for r in g.relations
            )
            if already_sub:
                # نَستَبدِل: substitute → attribute (النَّعت أَكثَر شيوعًا)
                g.relations = [r for r in g.relations
                                if not (r.name == "substitute_of" and r.source_id == f"t{i}")]
            g.add_relation(self._build_relation(
                name="attribute_of",
                kind_type="attribute",
                source_id=f"t{i}",
                target_id=f"t{i-1}",
                role_kind="Hypothesis",
                source_of_claim=f"post_detect: 2 def nouns same case → نَعت",
            ))

        # ── 8. ضَمائر النَّصب المُنفَصِلَة (إِيَّا*) → patient_of لِفِعل تالٍ ──
        # «إِيَّاكَ نَعبُدُ» → patient_of(إِيَّاكَ, نَعبُدُ)
        # «وَإِيَّاكَ نَستَعينُ» → patient_of(وَإِيَّاكَ, نَستَعينُ)
        # نَستَخدِم detached_pronouns.csv فَقَط لِضَمائر النَّصب
        detached = self._load_detached_pronouns()
        for i, t in enumerate(tokens):
            surface = getattr(t, "token", "") or ""
            # تَخَطّى الـ prefixes الشائعة (و، ف، أ) قَبل المُطابَقَة
            stripped = surface
            for pref in ("وَ", "فَ", "أَوَ", "أَفَ"):
                if stripped.startswith(pref):
                    stripped = stripped[len(pref):]
                    break
            # المُطابَقَة عَلى السَّطح أَو المُجَرَّد
            row = detached.get(stripped) or detached.get(self._strip_diac_static(stripped))
            if row is None:
                continue
            # نَأخُذ فَقَط ضَمائر النَّصب (case=نصب)
            if row.get("case", "").strip() != "نصب":
                continue
            # ابحَث عَن فِعل في الـ tokens التَّاليَة (داخِل نافِذَة قَصيرَة)
            verb_idx = None
            for j in range(i + 1, min(i + 4, len(tokens))):
                if tokens[j].word_class == "FIIL":
                    verb_idx = j
                    break
            if verb_idx is None:
                continue
            # تَأَكَّد لَم نَكتُب patient_of مُسبَقًا لِهذا الزَّوج
            already = any(
                r.name == "patient_of" and r.source_id == f"t{i}" and r.target_id == f"t{verb_idx}"
                for r in g.relations
            )
            if already:
                continue
            g.add_relation(self._build_relation(
                name="patient_of",
                kind_type="subj_pred",
                source_id=f"t{i}",
                target_id=f"t{verb_idx}",
                role_kind="Certificate",
                source_of_claim=(
                    f"post_detect: detached_pronoun({row.get('person','')}/{row.get('number','')}/"
                    f"{row.get('gender','')}) preceding FIIL → patient_of "
                    f"[detached_pronouns.csv]"
                ),
            ))

        # ── 9. الفاعِل المُستَتِر — مِن بادِئَة المُضارِع + لاحِقَة الفِعل ──
        # كُلّ FIIL لا يَملِك agent_of صَريح → نَستَنبِط الضَّمير المُستَتِر
        # مِن بادِئَتي ن/أ/ي/ت + اللاحِقَة (ون/ين/ان/ن/—)
        # المَصدَر: implicit_agents.csv (لا inline)
        verbs_with_explicit_agent = {
            r.target_id for r in g.relations if r.name == "agent_of"
        }
        implicit_rules = self._load_implicit_agents()
        # نَحتَفِظ بِالعَدّاد لِـ ids المُستَتِرَة
        implicit_counter = 0
        for i, t in enumerate(tokens):
            if t.word_class != "FIIL":
                continue
            verb_id = f"t{i}"
            if verb_id in verbs_with_explicit_agent:
                continue
            surface = getattr(t, "token", "") or ""
            surface_plain = self._strip_diac_static(surface)
            # نَزع clitics البادِئَة الشائِعَة (و، ف، أَ)
            for clitic in ("و", "ف", "أ"):
                if surface_plain.startswith(clitic):
                    surface_plain = surface_plain[len(clitic):]
                    break
            # المُطابَقَة عَلى قَواعِد implicit_agents
            # السِّياسَة: اللاحِقَة الصَّريحَة (PAST: تُم، نا، وا) أَولَى مِن البادِئَة
            # لِأَنَّها تُحَدِّد الشَّخص/العَدَد بِلا غُموض.
            matched_row = None
            # PATCH 7 — implicit-agent guard.
            # Do NOT apply PAST-suffix rules (تُم / نا / وا) when the verb
            # surface starts with an IV prefix (ي/ت/ن/أ). Target case:
            # يَكُونَا (dual jussive with نَا dual-marker, kept attached by
            # PATCH 3C) was wrongly matching the past-suffix `نا` rule
            # and getting ⊕نَحْنُ as implicit agent. Same defensive
            # behavior for ت-prefixed verbs ending in ـتُم / ـتُمَا / etc.
            _has_iv_prefix = _p7_has_iv_prefix_surface(surface_plain)
            # المُحاوَلَة الأولى: قاعِدَة بِلاحِقَة فَقَط (PAST)
            for row in implicit_rules:
                iv_pref = row.get("iv_prefix_plain", "").strip()
                suf_pat = row.get("verb_suffix_pattern", "").strip()
                if iv_pref or not suf_pat:
                    continue
                if _has_iv_prefix:
                    continue  # PATCH 7: skip PAST rules on IV-prefixed verbs
                if surface_plain.endswith(suf_pat):
                    matched_row = row
                    break
            # المُحاوَلَة الثَّانيَة: قاعِدَة بِبادِئَة (IV)
            if matched_row is None:
                for row in implicit_rules:
                    iv_pref = row.get("iv_prefix_plain", "").strip()
                    suf_pat = row.get("verb_suffix_pattern", "").strip()
                    if not iv_pref:
                        continue
                    if not surface_plain.startswith(iv_pref):
                        continue
                    if suf_pat and not surface_plain.endswith(suf_pat):
                        continue
                    matched_row = row
                    break
            if matched_row is None:
                continue
            # نَبني EntityNode مُستَتِر — virtual
            implicit_counter += 1
            implicit_id = f"implicit_t{i}_{implicit_counter}"
            implicit_pronoun = matched_row.get("implicit_pronoun", "").strip()
            g.add_node(EntityNode(
                entity_id=implicit_id,
                surface=implicit_pronoun,
                surface_plain=self._strip_diac_static(implicit_pronoun),
                position=-1,  # -1 = مُستَتِر، غَير ظاهِر في النَّصّ
                root="—",
                wazn="—",
                status="implicit_pronoun",
                word_class="ISM_DAMIR",
                role_phrase="فاعل مُستَتِر",
                case_name="مَرفوع",
                source_of_claim=(
                    f"implicit_agent: iv_prefix={matched_row.get('iv_prefix_plain')} "
                    f"+ suffix={matched_row.get('verb_suffix_pattern') or '—'} "
                    f"+ person={matched_row.get('person')}/number={matched_row.get('number')}/"
                    f"gender={matched_row.get('gender')} [implicit_agents.csv]"
                ),
                contract="EntityNode:implicit:v1",
            ))
            # عَبر AgentAgreementContract (implicit branch)
            _rel_imp = self._build_agent_via_contract(
                x_token=None,
                v_token=tokens[i],
                source_id=implicit_id,
                target_id=verb_id,
                position_evidence=(
                    f"implicit_agent: iv_prefix={matched_row.get('iv_prefix_plain')}, "
                    f"verb={surface} → {implicit_pronoun}"
                ),
                is_implicit=True,
                csv_row=matched_row,
            )
            if _rel_imp is not None:
                g.add_relation(_rel_imp)

        # ── 4. بَدَل — اسمان مُتَتالِيان بِنَفس الحالَة بِدون «و/أو» بَينهما ──
        for i in range(len(tokens) - 1):
            t1 = tokens[i]
            t2 = tokens[i + 1]
            if t1.word_class not in ("ISM_MUARAB", "JAMID", "AALAM"):
                continue
            if t2.word_class not in ("ISM_MUARAB", "JAMID", "AALAM"):
                continue
            s1 = getattr(t1, "token", "") or ""
            s2 = getattr(t2, "token", "") or ""
            # نَفس الحالَة (نِهايَة الكَلِمَة) + كِلاهُما مَعرِفَة
            # heuristic: كِلاهُما يَبدَأ بِـ ال أَو كِلاهُما عَلَم
            both_def = s1.startswith("ال") and s2.startswith("ال")
            both_proper = (t1.word_class == "AALAM" and t2.word_class == "AALAM")
            if not (both_def or both_proper):
                continue
            # تَأَكَّد لَم يَكُن نَعت
            role2 = (getattr(t2, "role_phrase", "") or "")
            if "نعت" in role2 or "مضاف" in role2:
                continue
            # candidate بَدَل
            g.add_relation(self._build_relation(
                name="substitute_of",
                kind_type="apposition",
                source_id=f"t{i+1}",
                target_id=f"t{i}",
                role_kind="Hypothesis",
                source_of_claim=f"post_detect: apposition heuristic at {i}:{i+1}",
            ))

    # ------------------------------------------------------------------
    # builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_entity(t, i: int) -> EntityNode:
        is_singular = (t.word_class == "JALALAH") or (
            t.word_class_source and "singular_term" in t.word_class_source
        )
        return EntityNode(
            entity_id=f"t{i}",
            surface=t.token,
            surface_plain=t.token_plain or "",
            position=i,
            root=t.root or "—",
            wazn=t.wazn or "—",
            status=("singular_term" if is_singular else ""),
            word_class=t.word_class,
            role_phrase=t.role_phrase or "",
            case_name=(t.token and ""),  # filled later if needed
            is_singular_term=is_singular,
            is_divine_name=is_singular,
            source_of_claim=t.word_class_source or "",
        )

    @staticmethod
    def _build_relation(*, name: str, kind_type: str, source_id: str, target_id: str,
                       role_kind: str, source_of_claim: str, operator: Optional[str] = None) -> Relation:
        return Relation(
            name=name,
            kind_type=kind_type,
            source_id=source_id,
            target_id=target_id,
            operator=operator,
            kind=role_kind or "Hypothesis",
            source_of_claim=source_of_claim,
            contract=CONTRACT_NAME,
        )

    @staticmethod
    def _build_patient_via_contract(*, x_token, v_token, source_id: str, target_id: str,
                                    prev_token=None,
                                    position_evidence: str = "") -> Optional[Relation]:
        """يُصدِر patient_of عَبر PatientAgreementContract.

        MC FIX 2026-05-25: DefectiveVerbContract — لَو الفِعل ناقِص،
        المَنصوب هُو خَبَر كان لا مَفعول.
        """
        # === DefectiveVerbContract guard ===
        try:
            from defective_verb_contract import check_defective_verb
            v_surface = getattr(v_token, "token", "") or "" if v_token else ""
            v_lemma = getattr(v_token, "lemma", "") or "" if v_token else ""
            _dv = check_defective_verb(v_surface, lemma_hint=v_lemma)
            if _dv.is_defective:
                return Relation(
                    name=_dv.comment_relation or "khabar_of_kana",
                    kind_type="kana_comment",
                    source_id=source_id,
                    target_id=target_id,
                    kind="Hypothesis",
                    source_of_claim=(
                        f"DefectiveVerbContract:{_dv.lemma}"
                        f" → routed patient → {_dv.comment_relation}"
                    ),
                    contract="DefectiveVerbContract:v1",
                )
        except ImportError:
            pass

        try:
            from patient_agreement_contract import evaluate_patient, mark_suppressed
        except ImportError:
            return Relation(
                name="patient_of", kind_type="subj_pred",
                source_id=source_id, target_id=target_id,
                kind="Hypothesis", source_of_claim="legacy_no_contract",
                blockers=["PatientAgreementContract unavailable"],
                contract=CONTRACT_NAME,
            )
        verdict = evaluate_patient(x_token, v_token,
                                    prev_token=prev_token,
                                    position_evidence=position_evidence)
        if verdict.kind == "Zero":
            mark_suppressed()
            return None
        return Relation(
            name="patient_of",
            kind_type="subj_pred",
            source_id=source_id,
            target_id=target_id,
            kind=verdict.kind,
            source_of_claim=" + ".join(verdict.evidence[:3]) if verdict.evidence else "",
            blockers=list(verdict.blockers),
            alternatives=list(verdict.residuals),
            contract=verdict.contract,
        )

    @staticmethod
    def _build_agent_via_contract(*, x_token, v_token, source_id: str, target_id: str,
                                  position_evidence: str = "",
                                  is_implicit: bool = False,
                                  csv_row: Optional[dict] = None) -> Optional[Relation]:
        """يُصدِر agent_of عَبر AgentAgreementContract.

        - يَرُدّ None إِذا الحُكم Zero (لا تُضاف العَلاقَة)
        - يَرُدّ Relation بِـ kind = Certificate أَو Hypothesis وَ blockers صَريحَة

        MC FIX 2026-05-25: DefectiveVerbContract — لَو الفِعل ناقِص
        (كان/ليس/صار…)، agent_of غَير مُنطَبِق. نُحَوِّل إلى ism_of_kana.
        """
        # === DefectiveVerbContract guard ===
        try:
            from defective_verb_contract import check_defective_verb
            v_surface = getattr(v_token, "token", "") or "" if v_token else ""
            v_lemma = getattr(v_token, "lemma", "") or "" if v_token else ""
            _dv = check_defective_verb(v_surface, lemma_hint=v_lemma)
            # PATCH 12 — also reject ism_of_kana routing here when the
            # source noun is apodosis-headed (فَرَجُلٌ → يَكُونَا).
            _p12_skip_kana = (x_token is not None
                              and _p12_source_is_apodosis_fa(x_token))
            if _dv.is_defective and not is_implicit and not _p12_skip_kana:
                # كان وَأَخواتُها → ism_of_kana لا agent_of
                return Relation(
                    name=_dv.topic_relation or "ism_of_kana",
                    kind_type="kana_topic",
                    source_id=source_id,
                    target_id=target_id,
                    kind="Hypothesis",
                    source_of_claim=(
                        f"DefectiveVerbContract:{_dv.lemma}"
                        f" → routed agent → {_dv.topic_relation}"
                    ),
                    contract="DefectiveVerbContract:v1",
                )
            if _dv.is_defective and _p12_skip_kana:
                # apodosis-headed noun, not ism — return None so no
                # ism_of_kana relation is added.
                return None
        except ImportError:
            pass

        # === AgentWindowContract guard — تَوصيَة المُستَخدِم 2026-05-25 ===
        # فِعل الأَمر / لام الأَمر → الفاعِل المُستَتِر أَقوى مِن أَيّ
        # اسم ظاهِر بَعيد أَو تابِع. نَرفُض agent_of صَريح في هَذه الحالَة.
        # (يُطَبَّق عَلى كُلّ call sites — لَيس فَقَط role=فاعل.)
        if not is_implicit:
            try:
                from agent_window_contract import _verb_has_command_or_jussive_form
                if _verb_has_command_or_jussive_form(v_token):
                    try:
                        from agent_agreement_contract import mark_suppressed
                        mark_suppressed()
                    except ImportError:
                        pass
                    return None  # لا تُصدِر agent_of لِفِعل أَمر/جَزم
            except ImportError:
                pass

        try:
            from agent_agreement_contract import (
                evaluate_agent, evaluate_implicit_agent,
            )
        except ImportError:
            # fallback: legacy behavior (Hypothesis مَع blocker)
            return Relation(
                name="agent_of", kind_type="subj_pred",
                source_id=source_id, target_id=target_id,
                kind="Hypothesis",
                source_of_claim="legacy_no_contract",
                blockers=["AgentAgreementContract unavailable"],
                contract=CONTRACT_NAME,
            )

        if is_implicit and csv_row is not None:
            verdict = evaluate_implicit_agent(
                pronoun=csv_row.get("implicit_pronoun", ""),
                v_token=v_token,
                csv_row=csv_row,
            )
        else:
            verdict = evaluate_agent(x_token, v_token,
                                      position_evidence=position_evidence)

        if verdict.kind == "Zero":
            # mark this Zero as suppressed (caller dropping the relation)
            try:
                from agent_agreement_contract import mark_suppressed
                mark_suppressed()
            except ImportError:
                pass
            return None  # لا تُضاف

        return Relation(
            name="agent_of",
            kind_type="subj_pred",
            source_id=source_id,
            target_id=target_id,
            kind=verdict.kind,
            source_of_claim=" + ".join(verdict.evidence[:3]) if verdict.evidence else "",
            blockers=list(verdict.blockers),
            alternatives=list(verdict.residuals),
            contract=verdict.contract,
        )


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    from i3rab_engine.engine import I3rabEngine

    engine = I3rabEngine()
    extractor = RelationExtractor()

    tests = [
        "كَتَبَ الْوَلَدُ كِتَابًا",
        "ذَهَبَ زَيْدٌ إِلَى الْمَسْجِدِ",
        "إِنَّ اللَّهَ غَفُورٌ رَحِيمٌ",
        "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
        "يَا أَيُّهَا النَّاسُ اعْبُدُوا رَبَّكُمْ",
    ]
    for s in tests:
        print(f"\n=== {s} ===")
        sent = engine.analyze_sentence(s)
        g = extractor.extract(sent)
        for i, t in enumerate(sent.tokens):
            print(f"  [{i}] {t.token:<18} wc={t.word_class:<12} role={t.role_phrase}")
        print(f"  --- {len(g.relations)} relations ---")
        for r in g.relations:
            op = f" via «{r.operator}»" if r.operator else ""
            print(f"  • {r.name}: {r.source_id} → {r.target_id}{op}")
            print(f"      src={r.source_of_claim}")
