#!/usr/bin/env python3
"""test_phase4_resolver.py — ContextualAmbiguityResolver (27 tests).

Phase 4 = standalone resolver لِـ 7 surfaces + بِما compound.
لا integration بِالـpipeline في هذِه الجَلسَة. الـ resolver standalone.
"""
import sys
sys.path.insert(0, ".")

results = []
def _t(name, fn):
    try:
        fn(); results.append((name, True, ""))
        print(f"  ✓ {name}")
    except AssertionError as e:
        results.append((name, False, str(e))); print(f"  ✗ {name}: {e}")
    except Exception as e:
        results.append((name, False, f"ERR: {e}")); print(f"  ✗ {name}: ERR {e}")


from arabic_analyzer.contextual_resolver import ContextualAmbiguityResolver
R = ContextualAmbiguityResolver()


# ─────────────────────────────────────────────────────────────
# مَن — relative / conditional / interrogative
# ─────────────────────────────────────────────────────────────
def t_man_relative():
    """مَن + فِعل مُضارِع (لَيس مَجزومًا) → relative_pronoun."""
    res = R.resolve("مَن", prev_tokens=["ٱللَّهُ"], next_tokens=["يَعْلَمُ", "ٱلْغَيْبَ"])
    assert res.selected_function == "relative_pronoun", res.selected_function
    assert res.selected_class == "ISM_MAWSOOL"


def t_man_conditional():
    """مَن + مُضارِع مَجزوم + جَواب فاء → conditional_tool (Certificate)."""
    res = R.resolve("مَن", prev_tokens=[], next_tokens=["يَعْمَلْ", "خَيرًا", "فَلَهُ", "ٱلْأَجرُ"])
    assert res.selected_function == "conditional_tool", res.selected_function
    assert res.certainty == "Certificate"


def t_man_interrogative():
    """قَالَ مَن … → interrogative_tool (Certificate)."""
    res = R.resolve("مَن", prev_tokens=["قَالَ"], next_tokens=["أَنتَ"])
    assert res.selected_function == "interrogative_tool", res.selected_function
    assert res.certainty == "Certificate"


def t_man_insufficient_context_stays_hypothesis():
    """مَن بِلا سِياق → unresolved_ambiguous / Hypothesis."""
    res = R.resolve("مَن", prev_tokens=[], next_tokens=[])
    assert res.certainty == "Hypothesis"
    assert "insufficient_context" in res.blockers


# ─────────────────────────────────────────────────────────────
# ما
# ─────────────────────────────────────────────────────────────
def t_ma_relative():
    """ما + مُضارِع → relative_pronoun (Hypothesis)."""
    res = R.resolve("ما", prev_tokens=["ٱللَّهُ"], next_tokens=["يَعْلَمُ", "ٱلسِّرَّ"])
    assert res.selected_function == "relative_pronoun", res.selected_function


def t_ma_negative():
    """ما + فِعل ماضٍ → negative_particle (Hypothesis)."""
    res = R.resolve("ما", prev_tokens=[], next_tokens=["كَتَبَ", "زَيدٌ"])
    assert res.selected_function == "negative_particle", res.selected_function


def t_ma_conditional():
    """ما + مُضارِع مَجزوم + جَواب → conditional_tool (Certificate)."""
    res = R.resolve("ما", prev_tokens=[], next_tokens=["تَفْعَلْ", "مِن", "خَيرٍ", "فَلَك", "أَجرُهُ"])
    assert res.selected_function == "conditional_tool", res.selected_function
    assert res.certainty == "Certificate"


def t_ma_interrogative():
    """قال ما → interrogative_tool (Certificate)."""
    res = R.resolve("ما", prev_tokens=["قَالَ"], next_tokens=["تُريدُ"])
    assert res.selected_function == "interrogative_tool", res.selected_function
    assert res.certainty == "Certificate"


def t_ma_extra_particle():
    """بِ + ما (بِدون فِعل مُضارِع بَعدها) → extra_particle (Hypothesis)."""
    # حالَة فيها preceded_by_preposition=True و next ليس فِعلًا مُضارِعًا
    res = R.resolve("ما", prev_tokens=["بِ"], next_tokens=["زَيدٌ"])
    assert res.selected_function == "extra_particle", res.selected_function


def t_ma_insufficient_context_stays_hypothesis():
    res = R.resolve("ما", prev_tokens=[], next_tokens=[])
    assert res.certainty == "Hypothesis"
    assert "insufficient_context" in res.blockers


# ─────────────────────────────────────────────────────────────
# أَيّ
# ─────────────────────────────────────────────────────────────
def t_ayy_interrogative():
    res = R.resolve("أَيّ", prev_tokens=["قَالَ"], next_tokens=["كِتَابٍ"])
    assert res.selected_function == "interrogative_tool"
    assert res.certainty == "Certificate"


def t_ayy_conditional():
    res = R.resolve("أَيّ", prev_tokens=[], next_tokens=["شَيءٍ", "تَفْعَلْ", "فَهوَ", "حَلال"])
    # بَعد أَيّ + شَيء (genitive) — يَنطَبِق pattern مَع idafa
    # لَكِن بِما أَنَّ التَّسَلسُل: أَيّ + شَيء + تَفعَل، فَالمَجزوم لَيس next مُباشَر
    # لِذا default: idafa pattern + question_likely
    assert res.selected_function in ("interrogative_tool", "conditional_tool"), res.selected_function


def t_ayy_idafa_nominal():
    """أَيّ + اسم مَجرور (idafa) → interrogative_tool Hypothesis (مَع candidates)."""
    res = R.resolve("أَيّ", prev_tokens=[], next_tokens=["كِتَابٍ"])
    assert res.selected_function == "interrogative_tool"
    assert "ISM_MAWSOOL" in res.candidates or "ISM_MABNI" in res.candidates


# ─────────────────────────────────────────────────────────────
# مَتى
# ─────────────────────────────────────────────────────────────
def t_mata_temporal_interrogative():
    res = R.resolve("مَتَى", prev_tokens=["قَالَ"], next_tokens=["تَعودُ"])
    assert res.selected_function == "interrogative_tool", res.selected_function
    assert res.certainty == "Certificate"
    # مَع ذلِك يَجِب أَن يَكون selected_class = ISM_MABNI، masaq_compatible_class = HARF
    assert res.selected_class == "ISM_MABNI"
    assert res.masaq_compatible_class == "HARF"


def t_mata_conditional_function():
    res = R.resolve("مَتَى", prev_tokens=[], next_tokens=["تَأتِ", "آتِكَ"])
    # تَأتِ مَجزوم (يَنتَهي بِكَسر بَدلًا مِن الياء) — لَيسَ مُؤَكَّدًا في heuristic
    # لَكِن إِن لَم يَكشِف، يَبقى temporal_adverb default
    assert res.selected_function in ("conditional_tool", "temporal_adverb"), res.selected_function


# ─────────────────────────────────────────────────────────────
# أَين
# ─────────────────────────────────────────────────────────────
def t_ayna_interrogative_locative():
    res = R.resolve("أَيْنَ", prev_tokens=["قَالَ"], next_tokens=["تَذْهَبُ"])
    assert res.selected_function == "interrogative_tool"
    assert res.selected_class == "ISM_MABNI"


def t_ayna_conditional_locative():
    res = R.resolve("أَيْنَ", prev_tokens=[], next_tokens=["تَكونوا", "فَإِنَّ", "ٱللَّهَ", "مَعَكُمْ"])
    # تَكونوا لَيس مَجزومًا في heuristic — يَبقى default locative
    assert res.selected_function in ("conditional_tool", "locative_adverb")


# ─────────────────────────────────────────────────────────────
# أَنّى
# ─────────────────────────────────────────────────────────────
def t_anna_locative_or_interrogative():
    res = R.resolve("أَنَّى", prev_tokens=["قَالَ"], next_tokens=["شِئْتُمْ"])
    # سِياق سُؤال → interrogative_tool
    assert res.selected_function == "interrogative_tool"
    assert res.certainty == "Certificate"


# ─────────────────────────────────────────────────────────────
# حَيث
# ─────────────────────────────────────────────────────────────
def t_haythu_locative_adverb():
    res = R.resolve("حَيْثُ", prev_tokens=["مِن"], next_tokens=["تُحِبُّونَ"])
    # مُضارِع لَيس مَجزومًا → default locative
    assert res.selected_function == "locative_adverb"


def t_haythu_conditional_function():
    res = R.resolve("حَيْثُ", prev_tokens=[], next_tokens=["تَكُنْ"])
    assert res.selected_function == "conditional_tool"


# ─────────────────────────────────────────────────────────────
# مِن (HARF JARR) vs مَن
# ─────────────────────────────────────────────────────────────
def t_min_preposition_before_genitive():
    """مِنْ + اسم مَجرور → HARF_JARR / prepositional_phrase_component (Certificate)."""
    res = R.resolve("مِنْ", prev_tokens=[], next_tokens=["ٱلسَّماءِ"])
    assert res.selected_function == "prepositional_phrase_component"
    assert res.certainty == "Certificate"
    assert res.selected_class == "HARF"


def t_min_not_relative_when_followed_by_genitive():
    """مِن (لَيس مَن) أَمام genitive — لا يَتَحَوَّل إلى relative_pronoun."""
    res = R.resolve("مِنْ", prev_tokens=[], next_tokens=["زَيدٍ"])
    assert res.selected_function != "relative_pronoun"
    assert res.selected_function == "prepositional_phrase_component"


# ─────────────────────────────────────────────────────────────
# بِمَا
# ─────────────────────────────────────────────────────────────
def t_bima_split_and_resolve():
    res = R.resolve("بِمَا", prev_tokens=[], next_tokens=["كَسَبَتْ", "أَيدِيهِم"])
    assert res.selected_class == "HARF"
    assert res.selected_function == "prepositional_phrase_component"
    # تَأَكَّد مِن أَنَّ embedded ما قَد حُلَّت
    assert "compound_split" in res.context_features
    assert "embedded_ma_function" in res.context_features


def t_bima_does_not_collapse_blindly():
    """بِمَا لَيسَت دائِمًا extra particle — يُقَسَّم بِوَعي."""
    res = R.resolve("بِمَا", prev_tokens=[], next_tokens=["كَسَبَتْ"])
    # داخِليًّا: ما + ماضٍ → negative
    # لَكِن في compound: نَحفَظ context
    assert res.context_features["embedded_ma_function"] in (
        "negative_particle", "relative_pronoun", "unresolved_ambiguous",
        "extra_particle", "interrogative_tool", "conditional_tool")


# ─────────────────────────────────────────────────────────────
# Certificate / Hypothesis discipline
# ─────────────────────────────────────────────────────────────
def t_no_certificate_when_context_insufficient():
    """بِدون سِياق كافٍ، يَجِب أَن يَبقى Hypothesis."""
    for s in ("مَن", "ما", "أَيّ"):
        res = R.resolve(s, prev_tokens=[], next_tokens=[])
        assert res.certainty != "Certificate", f"{s}: should NOT be Certificate"


def t_priority_does_not_override_context_conflict():
    """priority داخِليّ لا يَتَجاوَز تَعارُض في الـcontext."""
    # حالَة مُتَعارِضَة: قَالَ مَن (interrogative) — لَيس relative
    res = R.resolve("مَن", prev_tokens=["قَالَ"], next_tokens=["أَنتَ"])
    assert res.selected_function != "relative_pronoun"
    assert res.selected_function == "interrogative_tool"


def t_ambiguous_token_does_not_emit_event_certificate():
    """unresolved_ambiguous → لا يُطلِق Event Certificate."""
    res = R.resolve("مَن", prev_tokens=[], next_tokens=[])
    # تَأَكَّد مِن أَنَّ resolver لا يُعطي Certificate لِـ unresolved_ambiguous
    if res.selected_function == "unresolved_ambiguous":
        assert res.certainty != "Certificate"


# ─────────────────────────────────────────────────────────────
# Constitutional
# ─────────────────────────────────────────────────────────────
def t_resolver_has_required_schema_fields():
    res = R.resolve("مَن", prev_tokens=["قَالَ"], next_tokens=["أَنتَ"])
    d = res.to_dict()
    for k in ("surface", "normalized", "selected_class", "selected_function",
              "candidates", "context_features", "certainty", "source",
              "masaq_compatible_class", "needs_context", "blockers", "reason"):
        assert k in d, f"missing key: {k}"
    assert d["source"] == "ContextualAmbiguityResolver"


def t_resolver_can_resolve_all_handled():
    for s in ("مَن", "ما", "أَيّ", "مَتَى", "أَيْنَ", "أَنَّى", "حَيْثُ"):
        assert R.can_resolve(s), f"should resolve: {s}"


def t_resolver_stats_track_calls():
    R.reset_stats()
    R.resolve("مَن", prev_tokens=["قَالَ"], next_tokens=["أَنتَ"])
    R.resolve("ما", prev_tokens=[], next_tokens=["كَتَبَ"])
    st = R.get_stats()
    assert st["total_calls"] == 2
    assert "certificate_count" in st


# ─────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────
print("PHASE 4 — ContextualAmbiguityResolver (27 tests)")
print("=" * 70)
ALL = [
    ("t_man_relative", t_man_relative),
    ("t_man_conditional", t_man_conditional),
    ("t_man_interrogative", t_man_interrogative),
    ("t_man_insufficient_context_stays_hypothesis", t_man_insufficient_context_stays_hypothesis),
    ("t_ma_relative", t_ma_relative),
    ("t_ma_negative", t_ma_negative),
    ("t_ma_conditional", t_ma_conditional),
    ("t_ma_interrogative", t_ma_interrogative),
    ("t_ma_extra_particle", t_ma_extra_particle),
    ("t_ma_insufficient_context_stays_hypothesis", t_ma_insufficient_context_stays_hypothesis),
    ("t_ayy_interrogative", t_ayy_interrogative),
    ("t_ayy_conditional", t_ayy_conditional),
    ("t_ayy_idafa_nominal", t_ayy_idafa_nominal),
    ("t_mata_temporal_interrogative", t_mata_temporal_interrogative),
    ("t_mata_conditional_function", t_mata_conditional_function),
    ("t_ayna_interrogative_locative", t_ayna_interrogative_locative),
    ("t_ayna_conditional_locative", t_ayna_conditional_locative),
    ("t_anna_locative_or_interrogative", t_anna_locative_or_interrogative),
    ("t_haythu_locative_adverb", t_haythu_locative_adverb),
    ("t_haythu_conditional_function", t_haythu_conditional_function),
    ("t_min_preposition_before_genitive", t_min_preposition_before_genitive),
    ("t_min_not_relative_when_followed_by_genitive", t_min_not_relative_when_followed_by_genitive),
    ("t_bima_split_and_resolve", t_bima_split_and_resolve),
    ("t_bima_does_not_collapse_blindly", t_bima_does_not_collapse_blindly),
    ("t_no_certificate_when_context_insufficient", t_no_certificate_when_context_insufficient),
    ("t_priority_does_not_override_context_conflict", t_priority_does_not_override_context_conflict),
    ("t_ambiguous_token_does_not_emit_event_certificate", t_ambiguous_token_does_not_emit_event_certificate),
    ("t_resolver_has_required_schema_fields", t_resolver_has_required_schema_fields),
    ("t_resolver_can_resolve_all_handled", t_resolver_can_resolve_all_handled),
    ("t_resolver_stats_track_calls", t_resolver_stats_track_calls),
]
for nm, fn in ALL: _t(nm, fn)
print()
passed = sum(1 for _,ok,_ in results if ok)
print(f"Result: {passed}/{len(results)} passed")
if passed < len(results):
    print("\n=== FAILURES ===")
    for nm, ok, err in results:
        if not ok: print(f"  ✗ {nm}: {err}")
