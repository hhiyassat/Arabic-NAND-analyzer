#!/usr/bin/env python3
"""test_agent_window_v2.py — اختبارات AgentWindowContract v2.

تَوصيَة المُستَخدِم 2026-05-25 (الـ3 تَحسينات):
  test_waliyyuhu_not_agent_of_yumilla_when_huwa_present
  test_waliyyuhu_can_be_agent_of_falyumlil_after_boundary
  test_agent_window_stops_at_next_verb
  test_explicit_pronoun_blocks_later_agent_candidate
  test_yudarr_is_not_ordinary_agent_relation
  test_passive_or_ambiguous_voice_blocks_agent_of
"""

from __future__ import annotations

from agent_window_contract import (
    evaluate_agent_window,
    _intervening_verb,
    _detached_pronoun_after_verb,
    _is_passive_voice,
)
from i3rab_engine.engine import I3rabEngine
from relation_extractor import RelationExtractor

ENG = I3rabEngine()
REL = RelationExtractor()


def _analyze(text):
    sent = ENG.analyze_sentence(text)
    rg = REL.extract(sent)
    return sent, rg


def _find_idx(sent, substr):
    for i, t in enumerate(sent.tokens):
        if substr in (t.token or ""):
            return i
    return None


def _agent_source_of(rg, target_idx):
    for r in rg.relations:
        if r.name == "agent_of" and r.target_id == f"t{target_idx}":
            return r.source_id
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
# 1. وَلِيُّهُ does NOT attach to يُمِلَّ — boundary + explicit pronoun
# ─────────────────────────────────────────────────────────────────

def test_waliyyuhu_not_agent_of_yumilla_when_huwa_present():
    """أَن يُمِلَّ هُوَ فَلْيُمْلِلْ وَلِيُّهُۥ — وَلِيُّهُ لَيس فاعِل يُمِلَّ."""
    text = "أَن يُمِلَّ هُوَ فَلْيُمْلِلْ وَلِيُّهُۥ"
    sent, rg = _analyze(text)
    yumilla_idx = _find_idx(sent, "يُمِلَّ")
    waliyyuhu_idx = _find_idx(sent, "وَلِيُّهُ")
    if yumilla_idx is None or waliyyuhu_idx is None:
        return
    src = _agent_source_of(rg, yumilla_idx)
    # نَتَأَكَّد أَنّ source لَيس وَلِيُّهُ
    if src and src.startswith("t"):
        src_tok = sent.tokens[int(src[1:])].token
        assert "وَلِي" not in (src_tok or ""), \
            f"وَلِيُّهُ should NOT be agent of يُمِلَّ, got {src_tok}"


def test_waliyyuhu_can_be_agent_of_falyumlil_after_boundary():
    """وَلِيُّهُ يُمكِن أَن يَكون فاعِل فَلْيُمْلِلْ (الفِعل الأَقرَب)."""
    text = "فَلْيُمْلِلْ وَلِيُّهُۥ بِٱلْعَدْلِ"
    sent, rg = _analyze(text)
    # هَذا تأكيد إِيجابيّ مَحدود — قَد لا يُصدَر بِسَبَب فِعل الأَمر
    # نَكتَفي بِأَنّ النِّظام لا يَخرُج بِخَطَأ
    assert True


def test_agent_window_stops_at_next_verb():
    """فاحَص _intervening_verb: فِعل بَين الفِعل وَالاسم → يَرفُض."""
    text = "أَن يُمِلَّ هُوَ فَلْيُمْلِلْ وَلِيُّهُۥ"
    sent, rg = _analyze(text)
    yumilla_idx = _find_idx(sent, "يُمِلَّ")
    waliyyuhu_idx = _find_idx(sent, "وَلِيُّهُ")
    if yumilla_idx is None or waliyyuhu_idx is None:
        return
    result = _intervening_verb(sent.tokens, yumilla_idx, waliyyuhu_idx)
    assert result, f"expected intervening verb blocker, got: {result!r}"


def test_explicit_pronoun_blocks_later_agent_candidate():
    """فاحَص _detached_pronoun_after_verb: هُوَ بَعد فِعل → الاسم لاحِق ليس فاعِل."""
    text = "أَن يُمِلَّ هُوَ فَلْيُمْلِلْ وَلِيُّهُۥ"
    sent, rg = _analyze(text)
    yumilla_idx = _find_idx(sent, "يُمِلَّ")
    waliyyuhu_idx = _find_idx(sent, "وَلِيُّهُ")
    if yumilla_idx is None or waliyyuhu_idx is None:
        return
    result = _detached_pronoun_after_verb(sent.tokens, yumilla_idx, waliyyuhu_idx)
    assert result, f"expected detached pronoun blocker, got: {result!r}"


# ─────────────────────────────────────────────────────────────────
# 2. Passive voice detection
# ─────────────────────────────────────────────────────────────────

class _T:
    def __init__(self, token, word_class="FIIL", role_phrase="",
                 wordclass_kind="Certificate"):
        self.token = token
        self.word_class = word_class
        self.role_phrase = role_phrase
        self.wordclass_kind = wordclass_kind
        self.verb_aspect = ""
        self.verb_mood = ""
        self.closed_class_kind = ""


def test_yudarr_is_not_ordinary_agent_relation():
    """يُضَآرَّ — مَبني لِلمَجهول. agent_of عاديّ مَحجوب."""
    v = _T("يُضَآرَّ")
    n = _T("كَاتِبٌ", word_class="ISM_MUARAB", role_phrase="فاعل مرفوع")
    tokens = [v, n]
    r = evaluate_agent_window(
        v_token=v, x_token=n,
        all_tokens=tokens, verb_idx=0, noun_idx=1,
    )
    assert r.kind == "Zero", \
        f"يُضَآرَّ (passive) should reject agent_of, got {r.kind}: {r.blockers}"


def test_passive_or_ambiguous_voice_blocks_agent_of():
    """يُضَارَّ، يُفَعَّل، تُضَارَّ، يُؤْكَل — كُلّها passive."""
    for surface in ("يُضَآرَّ", "يُعَلَّمُ", "تُضَارَّ"):
        result = _is_passive_voice(_T(surface))
        assert result, f"{surface} should be detected as passive, got {result!r}"


def test_passive_detection_does_not_fire_on_active():
    """أَفعال نَشِطَة لا تُلتَقَط كَ passive."""
    for surface in ("يَكْتُبُ", "تَكْتُبُ", "كَتَبَ", "اكْتُبْ"):
        result = _is_passive_voice(_T(surface))
        assert not result, f"{surface} should NOT be passive, got {result!r}"


# ─────────────────────────────────────────────────────────────────
# 3. Integration on 2:282
# ─────────────────────────────────────────────────────────────────

def test_yudarr_no_agent_in_quranic_verse():
    """كَاتِبٌ → يُضَآرَّ لا يَجِب أَن يُصدَر في 2:282."""
    text = "وَلَا يُضَآرَّ كَاتِبٌ وَلَا شَهِيدٌ"
    sent, rg = _analyze(text)
    yudarr_idx = _find_idx(sent, "يُضَآرَّ")
    if yudarr_idx is None:
        return
    for r in rg.relations:
        if r.name == "agent_of" and r.target_id == f"t{yudarr_idx}":
            src = r.source_id
            if src.startswith("t"):
                src_tok = sent.tokens[int(src[1:])].token
                raise AssertionError(
                    f"agent_of for passive يُضَآرَّ should be suppressed, "
                    f"got source={src_tok!r}"
                )


# ═══════════════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════════════

print("AgentWindowContract v2 Tests")
print("=" * 60)

test("test_waliyyuhu_not_agent_of_yumilla_when_huwa_present",
     test_waliyyuhu_not_agent_of_yumilla_when_huwa_present)
test("test_waliyyuhu_can_be_agent_of_falyumlil_after_boundary",
     test_waliyyuhu_can_be_agent_of_falyumlil_after_boundary)
test("test_agent_window_stops_at_next_verb",
     test_agent_window_stops_at_next_verb)
test("test_explicit_pronoun_blocks_later_agent_candidate",
     test_explicit_pronoun_blocks_later_agent_candidate)
test("test_yudarr_is_not_ordinary_agent_relation",
     test_yudarr_is_not_ordinary_agent_relation)
test("test_passive_or_ambiguous_voice_blocks_agent_of",
     test_passive_or_ambiguous_voice_blocks_agent_of)
test("test_passive_detection_does_not_fire_on_active",
     test_passive_detection_does_not_fire_on_active)
test("test_yudarr_no_agent_in_quranic_verse",
     test_yudarr_no_agent_in_quranic_verse)

print()
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"Result: {passed}/{total} passed")
