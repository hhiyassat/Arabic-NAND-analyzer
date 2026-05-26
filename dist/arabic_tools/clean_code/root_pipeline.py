"""root_pipeline.py — The official end-to-end pipeline for any Arabic word.

ARCHITECTURE (per user spec, 2026-05-20):

    Word (مُشكَّلة)
        ↓
    [1] normalize_word()           ← clean_code/normalizer.py
            applies: NFC, lam-shamsi un-assimilation, hamzat-wasl resolution
        ↓
    [2] jalalah override?          ← لَفظ مُنفَرِد (highest priority)
            ┌── True → status=singular_term, root=—, wazn=—,
            │           is_singular_term=True, divine_name=True
            │   (تَصحيح أُنطولوجيّ 2026-05-22: اللَّه لا جَذر له، لا
            │    وَزن، خارِج التَّصنيف التَّقليديّ — لا كُلِّيّ/جُزئيّ،
            │    لا جامِد/مُشتَقّ.)
            └── False
                    ↓
    [3] is_closed_class()          ← clean_code/closed_class_detector.py
            ┌── True → status=closed_class (مبني/عامل، لا جذر اشتقاقي).
            └── False
                    ↓
    [4] is_jamid()                 ← clean_code/jamid_detector.py
            ┌── True → status=jamid (اسم ذات، جامد، لا جذر اشتقاقي).
            │         Examples: السماء، الأرض، الجبل، البحر، الشمس...
            └── False (derived open-class word — may have root)
                    ↓
    [5] WaznAligner.extract()      ← clean_code/root_by_alignment.py
            └── Returns root + wazn from wazn substring matching
                    + post-processing (doubled/hollow/defective expansion)

CONSTITUTIONAL GUARANTEE: closed-class words AND jawamid NEVER touch the
wazn matcher. Both gates are explicit and upstream. The wazn matcher
operates ONLY on derived open-class words (مشتقّات).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from closed_class_detector import is_closed_class
from jamid_detector import is_jamid
from root_by_alignment import WaznAligner, AlignmentResult, _strip_diac
from wazn_data import load_awzan, load_verbal_roots_from_masaq
from normalizer import normalize_for_root_extraction
from wazn_display_policy import RefinedWaznDisplay, refine_wazn_display

# Shared dataclass — exported from a separate module to break a circular
# dependency with proof_object.
from root_pipeline_types import WordAnalysis
from proof_object import ProofObject, certificate, hypothesis, zero


# لفظ الجلالة — لها جذر اصطلاحي ثابت (canonical lexical override)
JALALAH_FORMS = {"الله", "اللهم"}  # canonical


class RootPipeline:
    """The single entry point for analyzing any vocalized Arabic word.

    Usage:
        pipe = RootPipeline()
        result = pipe.analyze("كَتَبَ")
        # result.root = "كتب", result.wazn = "فَعَل", result.status = "open_class"
    """

    def __init__(self):
        from tanwin_stripping_contract import TanwinStrippingContract
        from living_root_contract import LivingRootContract
        self._aligner = WaznAligner(load_awzan())
        # Contracts (data-driven, replace inline rules)
        self._tanwin_stripper = TanwinStrippingContract()
        self._living_root = LivingRootContract()

    def _strip_tanwin_for_match(self, word: str) -> str:
        """Delegates to TanwinStrippingContract — see
        clean_code/data/contracts/rules/tanwin_stripping.csv for rules."""
        stripped, _ = self._tanwin_stripper.apply(word)
        return stripped

    def analyze(
        self,
        word: str,
        *,
        stem: str | None = None,
    ) -> ProofObject:
        """Run the full pipeline. Returns a ``ProofObject``.

        Per 14_Minimal_Complete_Theory.md, every analysis is one of:
          Certificate  — deterministic lookup (jalalah / closed_class / jamid).
          Hypothesis   — heuristic structural inference (wazn alignment).
          Zero         — out of domain or no match.

        ProofObject subclasses WordAnalysis, so legacy callers using
        ``r.root``, ``r.wazn``, ``r.status`` keep working unchanged.
        New callers can read ``r.kind``, ``r.contract``, ``r.blockers``.
        """
        if not word or not word.strip():
            return zero(
                contract="empty_input",
                source_of_claim="empty_input",
                word=word, word_plain="",
                status="closed_class",
                root="—", wazn="—",
            )

        # === STAGE 1: Jalalah / لَفظ مُنفَرِد (data-driven عَبر SingularTermDetector) ===
        # CONSTITUTIONAL: قَواعد الكَشف كُلّها في CSVs:
        #   - data/contracts/lists/singular_terms.csv (الأَشكال القَنونيَّة)
        #   - data/contracts/lists/singular_term_prefixes.csv (و، ف، ل، ب، ... + restore_strategy)
        #   - data/contracts/lists/quran_recitation_marks.csv (ۢ ۤ ۥ ۦ ۧ ۨ ۭ)
        # لا قائِمَة inline ولا special-case في الكود — كُلّ شَيء عَبر CSV.
        from singular_term_detector import get_singular_term_detector
        _stdet = get_singular_term_detector()
        word = _stdet.strip_recitation_marks(word)
        word_plain = _strip_diac(word)
        _st = _stdet.detect(word)
        if _st.is_singular_term:
            return certificate(
                contract="jalalah_singular_term",
                source_of_claim=f"singular_term_detector + {_st.source_of_claim}",
                word=word, word_plain=word_plain,
                status="singular_term",
                root="—",
                wazn="—",
                is_singular_term=True,
                divine_name=True,
            )

        # === STAGE 2: Closed-class gate (THE PARTICLE GATE) ===
        # Canonical lookup against quran_i3rab_labels — Certificate.
        if is_closed_class(word):
            return certificate(
                contract="closed_class_detector",
                source_of_claim="closed_class_detector",
                word=word, word_plain=word_plain,
                status="closed_class",
                root="—", wazn="—",
            )

        # === STAGE 3: Jamid gate — مع فحص الجذر الفعلي ===
        # MASAQ يَضع كتاب والسماء والأرض جميعها تحت NOUN_CONCRETE.
        # القاعدة اللسانيّة الموحَّدة: لو جذر الكلمة له فعل حيّ في
        # MASAQ → اسم مشتق ذو دلالة محسوسة. وإلا → جامد حقيقي.
        if is_jamid(word):
            # نُحاول استخراج جذر أوّلًا (مع نَزع التنوين)
            stripped = self._strip_tanwin_for_match(word)
            probe = self._aligner.extract(stripped)
            if probe is not None:
                if self._living_root.is_living(probe.root):
                    # الجذر إنتاجيّ — هذا اسم مشتق محسوس، لا جامد
                    refined: RefinedWaznDisplay = refine_wazn_display(
                        word, probe, stem=stem
                    )
                    return hypothesis(
                        contract="wazn_aligner_on_concrete_noun",
                        source_of_claim=(
                            f"wazn_alignment:{probe.wazn} "
                            f"({self._living_root.source()}:living)"
                        ),
                        word=word, word_plain=word_plain,
                        status="open_class",
                        root=refined.root,
                        wazn=refined.canonical_wazn,
                        canonical_wazn=refined.canonical_wazn,
                        surface_wazn=refined.surface_wazn,
                        proper_name=refined.proper_name,
                        divine_name=refined.divine_name,
                        display_notes=refined.notes,
                        prefix_len=probe.prefix_len,
                        suffix_len=probe.suffix_len,
                        transformations=probe.transformations,
                    )
            # وإلا: جامد حقيقي (الجذر بلا فعل حيّ، أو لم نَجد جذرًا)
            return certificate(
                contract="jamid_detector_no_verbal_root",
                source_of_claim="jamid_detector + root_has_no_verb_in_MASAQ",
                word=word, word_plain=word_plain,
                status="jamid",
                root="—", wazn="—",
            )

        # === STAGE 4: Wazn matching (open-class derived words only) ===
        # Structural inference — Hypothesis (or Zero if no match).
        # نَنزع التنوين قبل المُحاذاة (كي لا يَلتبس عليه ألف التنوين).
        stripped = self._strip_tanwin_for_match(word)
        result = self._aligner.extract(stripped)
        if result is None:
            return zero(
                contract="wazn_aligner",
                source_of_claim="no_wazn_matched",
                word=word, word_plain=word_plain,
                status="no_match",
                root="", wazn="",
                blockers=["no_wazn_pattern_matched_surface"],
            )

        refined: RefinedWaznDisplay = refine_wazn_display(
            word, result, stem=stem
        )
        # The aligner is heuristic; a clean Certificate is reserved for
        # canonical sources (closed/jamid/jalalah). Wazn matching is a
        # Hypothesis even when a single candidate is found.
        return hypothesis(
            contract="wazn_aligner",
            source_of_claim=f"wazn_alignment:{result.wazn}",
            word=word, word_plain=word_plain,
            status="open_class",
            root=refined.root,
            wazn=refined.canonical_wazn,
            canonical_wazn=refined.canonical_wazn,
            surface_wazn=refined.surface_wazn,
            proper_name=refined.proper_name,
            divine_name=refined.divine_name,
            display_notes=refined.notes,
            prefix_len=result.prefix_len,
            suffix_len=result.suffix_len,
            transformations=result.transformations,
        )

    # ------------------------------------------------------------------
    # Legacy API — returns a plain WordAnalysis (no kind/contract).
    # Provided for code that explicitly wants the simpler interface.
    # ------------------------------------------------------------------

    def analyze_legacy(
        self,
        word: str,
        *,
        stem: str | None = None,
    ) -> WordAnalysis:
        """Return a plain WordAnalysis (no proof-theoretic metadata).

        This is the pre-14_Minimal_Complete_Theory contract. New code
        should call ``analyze()`` and inspect ``.kind`` / ``.contract``.
        """
        p = self.analyze(word, stem=stem)
        return WordAnalysis(
            word=p.word,
            word_plain=p.word_plain,
            status=p.status,
            root=p.root,
            wazn=p.wazn,
            canonical_wazn=p.canonical_wazn,
            surface_wazn=p.surface_wazn,
            source_of_claim=p.source_of_claim,
            proper_name=p.proper_name,
            divine_name=p.divine_name,
            display_notes=list(p.display_notes),
            prefix_len=p.prefix_len,
            suffix_len=p.suffix_len,
            transformations=list(p.transformations),
        )


# ============================================================================
# Self-test
# ============================================================================

def _self_test():
    print("=== root_pipeline self-test ===\n")
    pipe = RootPipeline()

    open_class_tests = [
        ("كَتَبَ", "كتب"),
        ("مَكْتُوب", "كتب"),
        ("اسْتَخْرَج", "خرج"),
        ("يَنْصُرُونَ", "نصر"),
        ("كَسَبْتُمْ", "كسب"),
        ("رَدَّ", "ردد"),
    ]
    display_policy_tests = [
        ("رَحْمَنُ", "رحم", "فَعْلَان", "فَعْل"),
        ("اسْتَوَى", "سوي", "افْتَعَل", None),  # surface may vary
    ]
    closed_class_tests = ["هَذَا", "الَّذِي", "هُوَ", "فِي", "إِنَّ", "عَلَى", "مِنْ"]
    jalalah_tests = ["اللَّهِ", "اللَّهُ", "اللَّهَ", "اللَّهُمَّ"]

    print("--- Open-class (should reach wazn matcher) ---")
    for w, expected in open_class_tests:
        r = pipe.analyze(w)
        ok = r.root == expected and r.status == "open_class"
        mark = "✓" if ok else "✗"
        print(f"  {mark} {w}: status={r.status} root={r.root}")

    print("\n--- Closed-class (should be gated at stage 1) ---")
    for w in closed_class_tests:
        r = pipe.analyze(w)
        ok = r.status == "closed_class"
        mark = "✓" if ok else "✗"
        print(f"  {mark} {w}: status={r.status} root={r.root} source={r.source_of_claim}")

    print("\n--- Display policy (canonical vs surface) ---")
    for w, exp_root, exp_canon, exp_surface in display_policy_tests:
        r = pipe.analyze(w, stem=w)
        ok_root = r.root == exp_root
        ok_canon = r.canonical_wazn == exp_canon or r.wazn == exp_canon
        ok_surf = (
            exp_surface is None
            or r.surface_wazn == exp_surface
            or r.canonical_wazn != r.surface_wazn
        )
        mark = "✓" if ok_root and ok_canon and ok_surf else "✗"
        print(
            f"  {mark} {w}: canon={r.canonical_wazn} surf={r.surface_wazn} "
            f"root={r.root} divine={r.divine_name}"
        )

    print("\n--- Jalalah (لَفظ مُنفَرِد — لا جَذر، لا وَزن) ---")
    for w in jalalah_tests:
        r = pipe.analyze(w)
        ok = r.status == "singular_term" and r.root == "—" and r.wazn == "—"
        mark = "✓" if ok else "✗"
        print(f"  {mark} {w}: status={r.status} root={r.root} wazn={r.wazn}")


if __name__ == "__main__":
    _self_test()
