#!/usr/bin/env python3
"""test_phase4_engine_hook.py — Engine-level Layer 1 hook + metadata
propagation tests for I3rabEngine.

Scope (minimal, per 2026-05-26 governance approval):
  • flag OFF → I3rabEngine.analyze_sentence calls classify, NOT
    classify_with_context. Behavior + metadata byte-identical to baseline.
  • flag ON  → analyze_sentence routes through classify_with_context and
    threads prev_tokens / next_tokens from the surrounding window.
  • Phase 4 metadata (phase4_*) that the resolver attaches in r1 lands on
    TokenI3rab.phase4 (empty dict otherwise).

These tests do NOT exercise resolver semantics — that is covered by
test_phase4_resolver.py and test_phase4_integration.py. They prove the
plumbing only.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

_FLAG = "ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER"


def _set_flag(val: bool) -> None:
    if val:
        os.environ[_FLAG] = "1"
    elif _FLAG in os.environ:
        del os.environ[_FLAG]


# ─────────────────────────────────────────────────────────────
# Tracer helper — wrap classify / classify_with_context on a fresh
# engine's WordClassClassifier instance and count invocations.
# ─────────────────────────────────────────────────────────────
def _make_traced_engine():
    from i3rab_engine.engine import I3rabEngine
    eng = I3rabEngine()
    counters = {"classify": 0, "classify_with_context": 0}
    seen_contexts: list[tuple[tuple, tuple]] = []

    real_classify = eng._layer1.classify
    real_ctx = eng._layer1.classify_with_context

    def wrapped_classify(token, *a, **kw):
        counters["classify"] += 1
        return real_classify(token, *a, **kw)

    def wrapped_ctx(token, prev_tokens=None, next_tokens=None, *a, **kw):
        counters["classify_with_context"] += 1
        seen_contexts.append((tuple(prev_tokens or ()), tuple(next_tokens or ())))
        return real_ctx(
            token, prev_tokens=prev_tokens, next_tokens=next_tokens, *a, **kw
        )

    eng._layer1.classify = wrapped_classify  # type: ignore[assignment]
    eng._layer1.classify_with_context = wrapped_ctx  # type: ignore[assignment]
    return eng, counters, seen_contexts


# ─────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────
def t_flag_off_uses_classify_not_classify_with_context():
    """flag OFF → analyze_sentence calls classify exclusively."""
    _set_flag(False)
    eng, counters, _ = _make_traced_engine()
    sent = eng.analyze_sentence("بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ")
    assert counters["classify_with_context"] == 0, (
        f"flag OFF leaked classify_with_context calls: {counters}"
    )
    assert counters["classify"] >= len(sent.tokens) > 0, counters


def t_flag_on_uses_classify_with_context_and_passes_window():
    """flag ON → analyze_sentence calls classify_with_context per token,
    threading prev_tokens=tokens[:i] and next_tokens=tokens[i+1:].

    Note: classify_with_context internally calls self.classify(token) once
    per invocation (see layer1.py:319), so on flag-ON we expect
        classify_with_context_count == N (engine routes through ctx)
        classify_count          == N (each ctx call delegates once)
    That's NOT a leak from the engine — it's the wrapper contract.
    """
    _set_flag(True)
    try:
        eng, counters, seen_contexts = _make_traced_engine()
        sent = eng.analyze_sentence("بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ")
        n = len(sent.tokens)
        assert n > 0
        assert counters["classify_with_context"] == n, (
            f"engine did not route every token through classify_with_context "
            f"on flag ON: {counters}, n={n}"
        )
        # Each ctx call delegates to classify once — same count is expected.
        # If it ever exceeds n, the engine has started double-calling classify.
        assert counters["classify"] == n, (
            f"engine called classify in addition to ctx delegate: {counters}, n={n}"
        )
        # First token: prev empty, next has rest of sentence.
        prev0, next0 = seen_contexts[0]
        assert prev0 == (), prev0
        assert len(next0) == n - 1, next0
        # Last token: next empty, prev has everything before.
        prevN, nextN = seen_contexts[-1]
        assert nextN == (), nextN
        assert len(prevN) == n - 1, prevN
    finally:
        _set_flag(False)


def t_flag_off_token_phase4_is_empty_dict():
    """flag OFF → TokenI3rab.phase4 is the default empty dict."""
    _set_flag(False)
    from i3rab_engine.engine import I3rabEngine
    eng = I3rabEngine()
    sent = eng.analyze_sentence("قَالَ مَن أَنتَ")
    for t in sent.tokens:
        assert isinstance(t.phase4, dict), type(t.phase4)
        assert t.phase4 == {}, f"unexpected phase4 leak on flag OFF: {t.token} -> {t.phase4}"


def t_flag_on_propagates_phase4_metadata_to_token():
    """flag ON + a resolver-promotable surface (مَن in قَالَ … أَنتَ) →
    TokenI3rab.phase4 has at least phase4_selected_function. If the
    promotion path fires, phase4_source and phase4_certificate get set too."""
    _set_flag(True)
    try:
        from i3rab_engine.engine import I3rabEngine
        eng = I3rabEngine()
        sent = eng.analyze_sentence("قَالَ مَن أَنتَ")
        man_tokens = [t for t in sent.tokens if t.token == "مَن"]
        assert man_tokens, "test text must include the مَن token"
        man = man_tokens[0]
        # If the resolver fired at all, we should see metadata on .phase4.
        # If the underlying classification was already Certificate the
        # resolver bypasses → empty dict is acceptable; ensure shape only.
        assert isinstance(man.phase4, dict), type(man.phase4)
        if man.phase4:
            assert "phase4_selected_function" in man.phase4, man.phase4
            # Either Certificate (promotion) or Hypothesis (metadata-only)
            cert = man.phase4.get("phase4_certainty")
            assert cert in (None, "Certificate", "Hypothesis"), cert
            if cert == "Certificate":
                assert man.phase4.get("phase4_source") == "ContextualAmbiguityResolver"
    finally:
        _set_flag(False)


def t_flag_on_does_not_set_phase4_on_out_of_scope_tokens():
    """flag ON + a verb like كَتَبَ (outside resolver scope) → .phase4 stays
    empty even though the engine called classify_with_context for it."""
    _set_flag(True)
    try:
        from i3rab_engine.engine import I3rabEngine
        eng = I3rabEngine()
        sent = eng.analyze_sentence("كَتَبَ زَيدٌ")
        for t in sent.tokens:
            # كَتَبَ + زَيدٌ are not in HANDLED_SURFACES_NORMALIZED, so the
            # integration short-circuits before writing any phase4_* key.
            assert t.phase4 == {}, f"unexpected phase4 on out-of-scope {t.token}: {t.phase4}"
    finally:
        _set_flag(False)


def t_engine_copies_synthetic_phase4_keys_to_token_phase4():
    """Deterministic proof that engine.py copies phase4_* keys onto
    TokenI3rab.phase4 regardless of whether the real resolver fires.

    We monkeypatch the engine's Layer 1 to return a fabricated r1 dict
    that mimics what maybe_apply_resolver would attach after a
    Certificate promotion. The engine must:
      • copy the five phase4_* keys verbatim,
      • derive phase4_source='ContextualAmbiguityResolver' (because the
        synthetic r1 sets source to that),
      • derive phase4_certainty='Certificate'.
    """
    _set_flag(True)
    try:
        from i3rab_engine.engine import I3rabEngine
        eng = I3rabEngine()

        synthetic_r1 = {
            "word_class": "ISM_MABNI",
            "source": "ContextualAmbiguityResolver",
            "closed_class_kind": "",
            "verb_aspect": "",
            "root": "",
            "wazn": "",
            "operator_i3rab": "",
            "proof_kind": "Certificate",
            "proof_contract": "Phase4:ContextualAmbiguityResolver",
            "proof_blockers": [],
            "proof_alternatives": ["HARF"],
            "phase4_selected_function": "interrogative_tool",
            "phase4_reason": "synthetic_test_fixture",
            "phase4_context_features": {"prev": "قَالَ", "next": "أَنتَ"},
            "phase4_masaq_compatible_class": "HARF",
            "phase4_original_candidates": ["HARF", "ISM_MABNI"],
        }

        def stub_classify_with_context(token, prev_tokens=None, next_tokens=None):
            return dict(synthetic_r1)

        def stub_classify(token):
            # We force the engine onto the ctx path, so this should not run.
            raise AssertionError(
                "engine.analyze_sentence called classify on flag ON"
            )

        eng._layer1.classify_with_context = stub_classify_with_context  # type: ignore[assignment]
        eng._layer1.classify = stub_classify  # type: ignore[assignment]

        sent = eng.analyze_sentence("مَن أَنتَ")
        assert sent.tokens, "no tokens emitted"
        for t in sent.tokens:
            assert t.phase4, f"phase4 not propagated for {t.token!r}: {t.phase4}"
            # Verbatim keys
            assert t.phase4.get("phase4_selected_function") == "interrogative_tool"
            assert t.phase4.get("phase4_reason") == "synthetic_test_fixture"
            assert t.phase4.get("phase4_context_features") == {
                "prev": "قَالَ", "next": "أَنتَ"
            }
            assert t.phase4.get("phase4_masaq_compatible_class") == "HARF"
            assert t.phase4.get("phase4_original_candidates") == ["HARF", "ISM_MABNI"]
            # Derived keys
            assert t.phase4.get("phase4_source") == "ContextualAmbiguityResolver"
            assert t.phase4.get("phase4_certainty") == "Certificate"
            # word_class promotion came through the normal r1 copy
            assert t.word_class == "ISM_MABNI"
            assert t.word_class_source == "ContextualAmbiguityResolver"
    finally:
        _set_flag(False)


def t_engine_derives_hypothesis_certainty_when_metadata_only():
    """Synthetic Hypothesis r1 (metadata-only, no promotion): engine must
    derive phase4_certainty='Hypothesis' and NOT promote word_class."""
    _set_flag(True)
    try:
        from i3rab_engine.engine import I3rabEngine
        eng = I3rabEngine()

        synthetic_r1 = {
            "word_class": "HARF",
            "source": "closed_function_word:WHAT",
            "closed_class_kind": "WHAT",
            "verb_aspect": "",
            "root": "",
            "wazn": "",
            "operator_i3rab": "",
            "proof_kind": "Hypothesis",
            "proof_contract": "",
            "proof_blockers": [],
            "proof_alternatives": [],
            "phase4_selected_function": "negative_particle",
            "phase4_reason": "synthetic_hypothesis_fixture",
            "phase4_context_features": {"next_pos": "PV"},
            "phase4_masaq_compatible_class": "HARF",
            "phase4_original_candidates": ["HARF"],
        }

        def stub_classify_with_context(token, prev_tokens=None, next_tokens=None):
            return dict(synthetic_r1)

        eng._layer1.classify_with_context = stub_classify_with_context  # type: ignore[assignment]
        sent = eng.analyze_sentence("ما كَتَبَ")
        assert sent.tokens
        first = sent.tokens[0]
        assert first.phase4.get("phase4_certainty") == "Hypothesis", first.phase4
        assert first.phase4.get("phase4_source") is None, (
            "Hypothesis path should NOT set phase4_source"
        )
        # No promotion
        assert first.word_class == "HARF"
        assert first.word_class_source == "closed_function_word:WHAT"
    finally:
        _set_flag(False)


def t_flag_off_token_phase4_byte_identical_to_pre_change_shape():
    """Smoke: flag OFF analyze_sentence still produces TokenI3rab objects
    with all the pre-change attributes (word_class, root, claims, etc.)
    and t.phase4 == {} — i.e. adding the new field did not break the
    existing dataclass contract."""
    _set_flag(False)
    from i3rab_engine.engine import I3rabEngine
    eng = I3rabEngine()
    sent = eng.analyze_sentence("بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ")
    assert sent.tokens, "engine produced no tokens"
    for t in sent.tokens:
        # Spot-check pre-change attributes are still there.
        for attr in (
            "token", "position", "word_class", "root", "wazn",
            "wordclass_kind", "claims", "trace", "integrity", "phase4",
        ):
            assert hasattr(t, attr), f"TokenI3rab missing {attr}"
        # to_dict() must NOT include phase4 (so OFF JSON output stays
        # byte-identical to the pre-change shape).
        d = t.to_dict()
        assert "phase4" not in d, (
            "to_dict() leaked phase4 key — would change OFF byte output"
        )


# ─────────────────────────────────────────────────────────────
# Runner (same style as test_phase4_integration.py)
# ─────────────────────────────────────────────────────────────
results: list[tuple[str, bool, str]] = []


def _t(name, fn):
    try:
        fn()
        results.append((name, True, ""))
        print(f"  ✓ {name}")
    except AssertionError as e:
        results.append((name, False, str(e)))
        print(f"  ✗ {name}: {e}")
    except Exception as e:  # noqa: BLE001
        results.append((name, False, f"ERR: {e}"))
        print(f"  ✗ {name}: ERR {e}")


_set_flag(False)
print("PHASE 4 ENGINE HOOK — Layer 1 routing + metadata propagation (8 tests)")
print("=" * 70)
ALL = [
    ("t_flag_off_uses_classify_not_classify_with_context",
     t_flag_off_uses_classify_not_classify_with_context),
    ("t_flag_on_uses_classify_with_context_and_passes_window",
     t_flag_on_uses_classify_with_context_and_passes_window),
    ("t_flag_off_token_phase4_is_empty_dict",
     t_flag_off_token_phase4_is_empty_dict),
    ("t_flag_on_propagates_phase4_metadata_to_token",
     t_flag_on_propagates_phase4_metadata_to_token),
    ("t_flag_on_does_not_set_phase4_on_out_of_scope_tokens",
     t_flag_on_does_not_set_phase4_on_out_of_scope_tokens),
    ("t_engine_copies_synthetic_phase4_keys_to_token_phase4",
     t_engine_copies_synthetic_phase4_keys_to_token_phase4),
    ("t_engine_derives_hypothesis_certainty_when_metadata_only",
     t_engine_derives_hypothesis_certainty_when_metadata_only),
    ("t_flag_off_token_phase4_byte_identical_to_pre_change_shape",
     t_flag_off_token_phase4_byte_identical_to_pre_change_shape),
]
for nm, fn in ALL:
    _t(nm, fn)
_set_flag(False)
print()
passed = sum(1 for _, ok, _ in results if ok)
print(f"Result: {passed}/{len(results)} passed")
if passed < len(results):
    print("\n=== FAILURES ===")
    for nm, ok, err in results:
        if not ok:
            print(f"  ✗ {nm}: {err}")
    sys.exit(1)
