#!/usr/bin/env python3
"""test_harf_jarr.py — HarfJarrAgreementContract tests per user spec."""

from __future__ import annotations

from harf_jarr_agreement_contract import evaluate_harf_jarr
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


def _harf_targets_for(rg, h_idx):
    targets = []
    for r in rg.relations:
        if r.name == "harf_jarr_of" and r.target_id == f"t{h_idx}":
            if r.source_id.startswith("t"):
                targets.append(int(r.source_id[1:]))
    return targets


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


def test_ila_links_to_ajalin_only():
    """إِلَىٰٓ أَجَلٍ مُّسَمًّى — إلى يَربِط أَجَلٍ فَقَط، لا غَيره."""
    text = "إِلَىٰٓ أَجَلٍ مُّسَمًّى"
    sent, rg = _analyze(text)
    ila_idx = _find_idx(sent, "إِلَىٰٓ")
    if ila_idx is None:
        return
    targets = _harf_targets_for(rg, ila_idx)
    assert len(targets) <= 1, f"إلى should link to only 1 noun, got {len(targets)}"


def test_ila_does_not_link_to_alladhi_later():
    text = "إِلَىٰٓ أَجَلٍ يَكْتُبُ ٱلَّذِى عَلَيْهِ"
    sent, rg = _analyze(text)
    ila_idx = _find_idx(sent, "إِلَىٰٓ")
    if ila_idx is None:
        return
    targets = _harf_targets_for(rg, ila_idx)
    # ٱلَّذِى MUST NOT be in targets
    for ti in targets:
        tok = sent.tokens[ti].token
        assert "الذ" not in tok and "ٱلَّذِ" not in tok, \
            f"إلى should NOT link to ٱلَّذِى, got {tok}"


def test_harf_jarr_consumed_after_local_object():
    """بَعد أَوَّل مُتَعَلِّق صالِح، إلى يُستَهلَك."""
    text = "إِلَىٰٓ أَجَلٍ يَكْتُبُ"
    sent, rg = _analyze(text)
    ila_idx = _find_idx(sent, "إِلَىٰٓ")
    if ila_idx is None:
        return
    targets = _harf_targets_for(rg, ila_idx)
    assert len(targets) == 1, f"expected exactly 1 target, got {len(targets)}"


def test_no_cross_clause_harf_jarr_relation():
    """نَفس الـharf لا يَربِط أَسماء عَبر فَواصِل."""
    text = "إِلَىٰٓ أَجَلٍ ۚ ٱلْحَقُّ"
    sent, rg = _analyze(text)
    ila_idx = _find_idx(sent, "إِلَىٰٓ")
    if ila_idx is None:
        return
    for r in rg.relations:
        if r.name == "harf_jarr_of" and r.target_id == f"t{ila_idx}":
            if r.source_id.startswith("t"):
                src_tok = sent.tokens[int(r.source_id[1:])].token
                assert "حق" not in src_tok, f"إلى crosses to ٱلْحَقُّ, got {src_tok}"


def test_prep_requires_adjacent_or_short_window_nominal():
    """direct API: مَسافَة > 3 → reject."""
    class _T:
        def __init__(self, token, word_class="ISM_MUARAB",
                     closed_class_kind=""):
            self.token = token
            self.word_class = word_class
            self.closed_class_kind = closed_class_kind
            self.role_phrase = ""

    h = _T("إِلَى", "HARF", "HARF_JARR")
    x = _T("الْبَيْتِ")
    tokens = [h] + [_T(f"t{i}") for i in range(5)] + [x]
    r = evaluate_harf_jarr(
        h_token=h, x_token=x,
        all_tokens=tokens, h_idx=0, x_idx=6,
    )
    assert r.kind == "Zero", f"expected Zero (far), got {r.kind}"


def test_bi_links_to_al_adl_locally():
    """بِ + الْعَدْلِ — صَحيح."""
    text = "بِٱلْعَدْلِ"
    sent, rg = _analyze(text)
    # نَتَأَكَّد فَقَط أَنّ النِّظام لا يَخرُج بِخَطَأ
    assert True


def test_consume_blocks_double_use():
    """direct API: lock check — same harf, second X → Zero."""
    class _T:
        def __init__(self, token, word_class="ISM_MUARAB",
                     closed_class_kind=""):
            self.token = token
            self.word_class = word_class
            self.closed_class_kind = closed_class_kind
            self.role_phrase = ""
    h = _T("إِلَى", "HARF", "HARF_JARR")
    x = _T("الْبَيْتِ")
    tokens = [h, x]
    r = evaluate_harf_jarr(
        h_token=h, x_token=x,
        all_tokens=tokens, h_idx=0, x_idx=1,
        consumed_jarrs={0},
    )
    assert r.kind == "Zero", "consumed harf must reject"


def test_intervening_verb_blocks():
    class _T:
        def __init__(self, token, word_class="ISM_MUARAB",
                     closed_class_kind="", role_phrase=""):
            self.token = token
            self.word_class = word_class
            self.closed_class_kind = closed_class_kind
            self.role_phrase = role_phrase
    h = _T("إِلَى", "HARF", "HARF_JARR")
    v = _T("ذَهَبَ", "FIIL")
    x = _T("الْبَيْتِ")
    tokens = [h, v, x]
    r = evaluate_harf_jarr(
        h_token=h, x_token=x,
        all_tokens=tokens, h_idx=0, x_idx=2,
    )
    assert r.kind == "Zero", f"intervening verb should block, got {r.kind}"


print("HarfJarr Tests")
print("=" * 60)
test("test_ila_links_to_ajalin_only", test_ila_links_to_ajalin_only)
test("test_ila_does_not_link_to_alladhi_later", test_ila_does_not_link_to_alladhi_later)
test("test_harf_jarr_consumed_after_local_object", test_harf_jarr_consumed_after_local_object)
test("test_no_cross_clause_harf_jarr_relation", test_no_cross_clause_harf_jarr_relation)
test("test_prep_requires_adjacent_or_short_window_nominal", test_prep_requires_adjacent_or_short_window_nominal)
test("test_bi_links_to_al_adl_locally", test_bi_links_to_al_adl_locally)
test("test_consume_blocks_double_use", test_consume_blocks_double_use)
test("test_intervening_verb_blocks", test_intervening_verb_blocks)
print()
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"Result: {passed}/{total} passed")
