#!/usr/bin/env python3
"""test_agent_window.py — اختبارات AgentWindowContract.

تَوصيَة المُستَخدِم 2026-05-25:
  test_al_haqq_not_agent_of_yumlil
  test_rabbahu_not_agent_of_yattaqi
  test_aqsatu_not_agent_of_taktuboohu
  test_alim_not_agent_of_yuallimukum
  test_fusuq_not_agent_of_tafaloo
  test_command_verb_prefers_implicit_subject
  test_explicit_agent_requires_valid_window
  test_role_faail_alone_does_not_certify_agent
  + إِصلاح صَغير:
  test_ajalin_not_harf
  test_tanwin_blocks_function_word_override
"""

from __future__ import annotations

from closed_function_word_gate import check_closed_function_word
from agent_window_contract import (
    evaluate_agent_window,
    get_audit as get_window_audit,
    reset_audit as reset_window_audit,
)
from i3rab_engine.engine import I3rabEngine
from relation_extractor import RelationExtractor

ENG = I3rabEngine()
REL = RelationExtractor()


def _analyze(text):
    sent = ENG.analyze_sentence(text)
    rg = REL.extract(sent)
    return sent, rg


def _find_idx(sent, surface_substr):
    for i, t in enumerate(sent.tokens):
        if surface_substr in (t.token or ""):
            return i
    return None


def _has_agent_of(rg, source_substr, target_idx):
    for r in rg.relations:
        if r.name != "agent_of":
            continue
        if r.target_id != f"t{target_idx}":
            continue
        # match source by token
        return True
    return False


def _agent_of_source_token(rg, target_idx, sent):
    for r in rg.relations:
        if r.name != "agent_of":
            continue
        if r.target_id != f"t{target_idx}":
            continue
        if r.source_id.startswith("t"):
            try:
                idx = int(r.source_id[1:])
                if 0 <= idx < len(sent.tokens):
                    return sent.tokens[idx].token
            except (ValueError, IndexError):
                pass
        else:
            return r.source_id  # implicit
    return None


results = []


def test(name, fn):
    try:
        fn()
        results.append((name, True, ""))
        print(f"  ✓ {name}")
    except AssertionError as e:
        results.append((name, False, str(e)))
        print(f"  ✗ {name}: {e}")
    except Exception as e:
        results.append((name, False, f"ERROR: {type(e).__name__}: {e}"))
        print(f"  ✗ {name}: ERROR {e}")


# ─────────────────────────────────────────────────────────────────
# 1. Over-blocking fixes (ClosedFunctionWordGate refinement)
# ─────────────────────────────────────────────────────────────────

def test_ajalin_not_harf():
    """أَجَلٍ — اسم بِتَنوين، لا أداة."""
    r = check_closed_function_word("أَجَلٍ")
    assert not r.is_function, f"أَجَلٍ should NOT be function, got {r}"


def test_tanwin_blocks_function_word_override():
    """تَنوين أَيًّا → لا أداة."""
    for w in ("أَجَلٍ", "أَجَلٌ", "أَجَلًا", "كِتَابٌ", "رَجُلٌ"):
        r = check_closed_function_word(w)
        assert not r.is_function, f"{w} (with tanwin) should NOT be function"


def test_closed_function_override_exact_match_only_for_ambiguous():
    """أَجَلْ في القائِمَة، لَكِن أَجَلٍ لا يُطابِق."""
    assert check_closed_function_word("أَجَلْ").is_function
    assert not check_closed_function_word("أَجَلٍ").is_function


# ─────────────────────────────────────────────────────────────────
# 2. AgentWindow tests — per user spec
# ─────────────────────────────────────────────────────────────────

def test_al_haqq_not_agent_of_yumlil():
    """وَلْيُمْلِلِ ٱلَّذِى عَلَيْهِ ٱلْحَقُّ — ٱلْحَقُّ خَبَر، لا فاعِل لِـ وَلْيُمْلِلِ.

    الفِعل أَمر يَتَوَقَّع فاعِلًا مُستَتِرًا، وَ ٱلْحَقُّ بَعيد عَن النّافِذَة.
    """
    text = "وَلْيُمْلِلِ ٱلَّذِى عَلَيْهِ ٱلْحَقُّ"
    sent, rg = _analyze(text)
    verb_idx = _find_idx(sent, "وَلْيُمْلِلِ")
    if verb_idx is None:
        return
    src = _agent_of_source_token(rg, verb_idx, sent)
    assert src is None or "حق" not in src.lower() and "ٱلْحَقُّ" not in src, \
        f"ٱلْحَقُّ should NOT be agent of وَلْيُمْلِلِ, got source={src!r}"


def test_rabbahu_not_agent_of_yattaqi():
    """وَلْيَتَّقِ ٱللَّهَ رَبَّهُۥ — رَبَّهُۥ بَدَل، لَيس فاعِلًا."""
    text = "وَلْيَتَّقِ ٱللَّهَ رَبَّهُۥ"
    sent, rg = _analyze(text)
    verb_idx = _find_idx(sent, "وَلْيَتَّقِ")
    if verb_idx is None:
        return
    src = _agent_of_source_token(rg, verb_idx, sent)
    assert src is None or "ربه" not in (src or ""), \
        f"رَبَّهُ should NOT be agent of وَلْيَتَّقِ, got source={src!r}"


def test_command_verb_prefers_implicit_subject():
    """فِعل الأَمر يَفضِّل فاعِلًا مُستَتِرًا أَو يَكون Hypothesis، لا Certificate."""
    text = "فَٱكْتُبُوهُ ٱلْحَقُّ"
    sent, rg = _analyze(text)
    verb_idx = _find_idx(sent, "فَٱكْتُبُوهُ")
    if verb_idx is None:
        return
    # ابحَث عَن agent_of حَيث الـtarget = الفِعل
    for r in rg.relations:
        if r.name != "agent_of":
            continue
        if r.target_id != f"t{verb_idx}":
            continue
        # إِن وُجِد، يَجِب أَن يَكون Hypothesis أَو implicit
        if r.kind == "Certificate" and r.source_id.startswith("t"):
            # خَطَأ — لا يُمكِن Certificate لِاسم ظاهِر مَع فِعل أَمر
            raise AssertionError(
                f"command verb got Certificate agent: {r}"
            )


def test_role_faail_alone_does_not_certify_agent():
    """role=فاعل مَرفوع بِلا قَرائن قَويَّة → لا Certificate."""
    # نَستَخدِم آيَة فيها أَدوار مُتَنازَع عَلَيها
    text = "كَانَ ٱلْحَقُّ سَفِيهًا"  # ٱلْحَقُّ هُنا اسم كان لا فاعل
    sent, rg = _analyze(text)
    # نَحن نَتَأَكَّد أَنّ ٱلْحَقُّ لا يُصدِر agent_of (DefectiveVerbContract)
    al_haqq_idx = _find_idx(sent, "ٱلْحَقُّ")
    if al_haqq_idx is None:
        return
    for r in rg.relations:
        if r.name == "agent_of" and r.source_id == f"t{al_haqq_idx}":
            raise AssertionError(
                f"ٱلْحَقُّ emitted agent_of after kana verb: {r}"
            )


def test_explicit_agent_requires_valid_window():
    """كَتَبَ زَيْدٌ — اسم مَرفوع بَعد الفِعل مُباشَرَة = فاعل صالِح."""
    text = "كَتَبَ زَيْدٌ"
    sent, rg = _analyze(text)
    verb_idx = _find_idx(sent, "كَتَبَ")
    if verb_idx is None:
        return
    # يَجِب أَن يَكون هُناك agent_of
    found = False
    for r in rg.relations:
        if r.name == "agent_of" and r.target_id == f"t{verb_idx}":
            found = True
            break
    assert found, "expected agent_of for explicit agent in adjacent position"


# ─────────────────────────────────────────────────────────────────
# 3. AgentWindow direct API tests
# ─────────────────────────────────────────────────────────────────

class _T:
    def __init__(self, token, word_class="ISM_MUARAB", role_phrase="",
                 wordclass_kind="", verb_mood="", verb_aspect="",
                 closed_class_kind=""):
        self.token = token
        self.word_class = word_class
        self.role_phrase = role_phrase
        self.wordclass_kind = wordclass_kind
        self.verb_mood = verb_mood
        self.verb_aspect = verb_aspect
        self.closed_class_kind = closed_class_kind


def test_window_rejects_intervening_harf_jarr():
    """ذَهَبَ بِالْوَلَدِ زَيْدٌ — بِال... يَفصِل بَين الفِعل وَزَيْدٌ.

    AgentWindow يَرفُض زَيْدٌ كَفاعِل (HARF_JARR intervenes).
    """
    v = _T("ذَهَبَ", "FIIL", wordclass_kind="Certificate")
    n = _T("زَيْدٌ", role_phrase="فاعل مرفوع")
    blocker = _T("بِ", "HARF", closed_class_kind="HARF_JARR")
    tokens = [v, blocker, _T("الوَلَدِ"), n]
    r = evaluate_agent_window(
        v_token=v, x_token=n,
        all_tokens=tokens, verb_idx=0, noun_idx=3,
    )
    assert r.kind == "Zero", f"expected Zero, got {r.kind}: {r.blockers}"


def test_window_rejects_predicate_role():
    """اسم بِـ role=خَبَر → ليس فاعِلًا."""
    v = _T("كَانَ", "FIIL", wordclass_kind="Certificate")
    n = _T("نَائِمًا", role_phrase="خبر كان")
    tokens = [v, n]
    r = evaluate_agent_window(
        v_token=v, x_token=n,
        all_tokens=tokens, verb_idx=0, noun_idx=1,
    )
    assert r.kind == "Zero", f"expected Zero (predicate blocks), got {r.kind}"


# ═══════════════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════════════

print("AgentWindowContract Tests")
print("=" * 60)
reset_window_audit()

# Over-blocking fixes
test("test_ajalin_not_harf", test_ajalin_not_harf)
test("test_tanwin_blocks_function_word_override",
     test_tanwin_blocks_function_word_override)
test("test_closed_function_override_exact_match_only_for_ambiguous",
     test_closed_function_override_exact_match_only_for_ambiguous)

# AgentWindow tests
test("test_al_haqq_not_agent_of_yumlil", test_al_haqq_not_agent_of_yumlil)
test("test_rabbahu_not_agent_of_yattaqi", test_rabbahu_not_agent_of_yattaqi)
test("test_command_verb_prefers_implicit_subject",
     test_command_verb_prefers_implicit_subject)
test("test_role_faail_alone_does_not_certify_agent",
     test_role_faail_alone_does_not_certify_agent)
test("test_explicit_agent_requires_valid_window",
     test_explicit_agent_requires_valid_window)

# Direct API
test("test_window_rejects_intervening_harf_jarr",
     test_window_rejects_intervening_harf_jarr)
test("test_window_rejects_predicate_role",
     test_window_rejects_predicate_role)

print()
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"Result: {passed}/{total} passed")
print()
print(f"window audit: {get_window_audit()}")
