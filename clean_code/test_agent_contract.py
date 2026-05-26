#!/usr/bin/env python3
"""test_agent_contract.py — اختبار AgentAgreementContract.

تَنفيذ التَّوصيَة الـ9 لِلمُستَخدِم:
  test_no_prep_as_agent
  test_no_harf_as_agent
  test_no_punctuation_as_agent
  test_no_agent_for_non_certified_verb
  test_tum_suffix_promotes_antum
  test_ta_ambiguous_without_suffix_suppressed
  test_relative_pronoun_not_agent_without_sila
  test_event_remains_hypothesis_when_agent_hypothesis
"""

from __future__ import annotations

from i3rab_engine.engine import I3rabEngine
from relation_extractor import RelationExtractor
from event_extractor import EventExtractor

ENGINE = I3rabEngine()
REL = RelationExtractor()
EV = EventExtractor()


def analyze(text):
    sent = ENGINE.analyze_sentence(text)
    rg = REL.extract(sent)
    eg = EV.extract(sent, rg)
    return sent, rg, eg


def find_relation(rg, name, source_substr=None, target_substr=None):
    """Return relation matching name + optional source/target substring."""
    for r in rg.relations:
        if r.name != name:
            continue
        if source_substr and source_substr not in r.source_id:
            continue
        if target_substr and target_substr not in r.target_id:
            continue
        return r
    return None


def has_agent_with_source(rg, source_token, sent):
    """True if any agent_of relation's source token text matches."""
    for r in rg.relations:
        if r.name != "agent_of":
            continue
        if r.source_id.startswith("t"):
            try:
                idx = int(r.source_id[1:])
                tok = sent.tokens[idx].token if 0 <= idx < len(sent.tokens) else ""
                if source_token in tok:
                    return True
            except (ValueError, IndexError):
                pass
    return False


# ═══════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════

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


def test_no_prep_as_agent():
    sent, rg, _ = analyze("ذَهَبَ الْوَلَدُ بِالْمَفَاتِيحِ إِلَى البَيتِ")
    # بِالْمَفَاتِيحِ يَبدَأ بِـ ب — يَجِب أَلّا يَكون agent
    assert not has_agent_with_source(rg, "بِال", sent), "PREP بِ leaked as agent"


def test_no_harf_as_agent():
    sent, rg, _ = analyze("ٱلَّذِينَ ءَامَنُوٓا۟ كَتَبُوا")
    # ٱلَّذِينَ هو ISM_MAWSOOL الآن (لا HARF) — الفِعل ءامَنوا
    # نَتَأَكَّد أَنّ HARF حَقيقيّ (مَثَلًا الَّذِينَ قَبل الإِصلاح كانَ HARF)
    # لا يَظهَر كَ agent. حاليًّا agent المُعبَّر هو الضَّمير الوَاو في
    # «ءامَنوا»، أَو ٱلَّذِينَ كَ Hypothesis.
    # نَطلُب: لا agent مَصدَره HARF
    for r in rg.relations:
        if r.name != "agent_of":
            continue
        if not r.source_id.startswith("t"):
            continue
        idx = int(r.source_id[1:])
        if 0 <= idx < len(sent.tokens):
            assert sent.tokens[idx].word_class != "HARF", \
                f"HARF leaked as agent: {sent.tokens[idx].token}"


def test_no_punctuation_as_agent():
    # عَلامات الوَقف يَجِب أَن تَكون مُجَرَّدَة قَبل i3rab أَصلًا
    text = "كَتَبَ ۚ الْوَلَدُ"
    sent, rg, _ = analyze(text)
    # لا token = ۚ
    for t in sent.tokens:
        assert "ۚ" not in t.token, f"pause mark in token: {t.token}"


def test_no_agent_for_non_certified_verb():
    """إِن لَم يَكُن target فِعلًا، لا agent."""
    sent, rg, _ = analyze("الْكِتَابُ الْجَدِيدُ")  # لا فِعل
    n_agents = sum(1 for r in rg.relations if r.name == "agent_of")
    assert n_agents == 0, f"agent created without FIIL target: {n_agents}"


def test_tum_suffix_promotes_antum():
    """تَ + تُم → ⊕أَنْتُمْ Hypothesis (لا Zero)."""
    sent, rg, _ = analyze("تَبَايَعْتُمْ بِالْعَدْلِ")
    # نُريد agent_of(⊕أَنْتُم → تَبَايَعْتُم)
    found = False
    for r in rg.relations:
        if r.name != "agent_of":
            continue
        if r.source_id.startswith("implicit_"):
            node = rg.nodes.get(r.source_id)
            if node and "أَنْتُم" in node.surface:
                found = True
                break
    assert found, "expected ⊕أَنْتُمْ on تَبَايَعْتُمْ"


def test_ta_ambiguous_without_suffix_suppressed():
    """تَضِلَّ (تَ بِلا لاحِقَة) لا يَنبَغي أَن يُولِّد ⊕أَنْتَ."""
    sent, rg, _ = analyze("أَن تَضِلَّ إِحْدَىٰهُمَا")
    # نَبحَث عَن ⊕أَنْتَ مَع تَضِلَّ
    for r in rg.relations:
        if r.name != "agent_of":
            continue
        if not r.source_id.startswith("implicit_"):
            continue
        node = rg.nodes.get(r.source_id)
        if node and "أَنْتَ" in node.surface and not "أَنْتُمْ" in node.surface:
            # نَفحَص الـ target
            if r.target_id.startswith("t"):
                idx = int(r.target_id[1:])
                if 0 <= idx < len(sent.tokens):
                    tok = sent.tokens[idx].token
                    assert "تَضِلَّ" not in tok, \
                        f"تَ-ambiguous fabricated ⊕أَنْتَ on {tok}"


def test_relative_pronoun_not_agent_without_sila():
    """ٱلَّذِينَ كَ ISM_MAWSOOL يَجِب أَن يَكون Hypothesis لا Certificate."""
    sent, rg, _ = analyze("ٱلَّذِينَ ءَامَنُوٓا۟ كَتَبُوا")
    for r in rg.relations:
        if r.name != "agent_of":
            continue
        if r.source_id.startswith("t"):
            idx = int(r.source_id[1:])
            if 0 <= idx < len(sent.tokens):
                if sent.tokens[idx].word_class == "ISM_MAWSOOL":
                    assert r.kind != "Certificate", \
                        f"ISM_MAWSOOL got Certificate: {r}"


def test_event_remains_hypothesis_when_agent_hypothesis():
    """Event.kind == Hypothesis بِشَكل افتراضيّ."""
    sent, rg, eg = analyze("كَتَبَ الْوَلَدُ كِتَابًا")
    for e in eg.events:
        assert e.kind != "Certificate", \
            f"Event got Certificate without strict proof: {e}"


# ═══════════════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════════════

def test_no_prep_as_patient():
    sent, rg, _ = analyze("ذَهَبَ الْوَلَدُ بِالْمَفَاتِيحِ")
    # المَفَاتِيحِ هي مَجرور (بعد ب) لا مَفعول
    for r in rg.relations:
        if r.name != "patient_of":
            continue
        if r.source_id.startswith("t"):
            idx = int(r.source_id[1:])
            tok = sent.tokens[idx].token if 0 <= idx < len(sent.tokens) else ""
            assert "مَفَاتِيح" not in tok, f"مَجرور بِالباء أُصدِر كَ مَفعول: {tok}"


def test_no_harf_as_patient():
    sent, rg, _ = analyze("كَتَبَ الْوَلَدُ كِتَابًا فِي البَيتِ")
    for r in rg.relations:
        if r.name != "patient_of":
            continue
        if not r.source_id.startswith("t"):
            continue
        idx = int(r.source_id[1:])
        if 0 <= idx < len(sent.tokens):
            assert sent.tokens[idx].word_class != "HARF", \
                f"HARF أُصدِر كَ مَفعول: {sent.tokens[idx].token}"


def test_mansub_patient_emitted():
    """كِتَابًا (تَنوين فَتح) يَجِب أَن يُصدِر patient_of
    (kind = Hypothesis مَقبول لِأَنّ FIIL نَفسه Hypothesis).
    """
    sent, rg, _ = analyze("كَتَبَ الْوَلَدُ كِتَابًا")
    found = False
    for r in rg.relations:
        if r.name != "patient_of":
            continue
        if r.source_id.startswith("t"):
            idx = int(r.source_id[1:])
            if 0 <= idx < len(sent.tokens) and "كِتَاب" in sent.tokens[idx].token:
                found = True
                # نَتَأَكَّد أَنّه إِمّا Certificate أَو Hypothesis (لَيس Zero)
                assert r.kind in ("Certificate", "Hypothesis"), \
                    f"كِتَابًا got Zero: {r}"
                break
    assert found, "no patient_of emitted for كِتَابًا"


print("Agent + Patient Contract Tests")
print("=" * 60)

test("test_no_prep_as_agent", test_no_prep_as_agent)
test("test_no_harf_as_agent", test_no_harf_as_agent)
test("test_no_punctuation_as_agent", test_no_punctuation_as_agent)
test("test_no_agent_for_non_certified_verb", test_no_agent_for_non_certified_verb)
test("test_tum_suffix_promotes_antum", test_tum_suffix_promotes_antum)
test("test_ta_ambiguous_without_suffix_suppressed", test_ta_ambiguous_without_suffix_suppressed)
test("test_relative_pronoun_not_agent_without_sila", test_relative_pronoun_not_agent_without_sila)
test("test_event_remains_hypothesis_when_agent_hypothesis", test_event_remains_hypothesis_when_agent_hypothesis)
test("test_no_prep_as_patient", test_no_prep_as_patient)
test("test_no_harf_as_patient", test_no_harf_as_patient)
test("test_mansub_patient_emitted", test_mansub_patient_emitted)

print()
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"Result: {passed}/{total} passed")
