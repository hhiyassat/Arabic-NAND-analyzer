"""singular_term_detector.py — كاشِف لَفظ مُنفَرِد (data-driven).

CONSTITUTIONAL: قَواعد كَشف الجَلالة كانَت inline في 4 مَلَفّات (root_pipeline،
root_by_alignment، i3rab_engine/layer1، pronoun_clitic_resolver). نَقلتُها إلى
ثَلاثَة contracts:

  • `data/contracts/lists/singular_terms.csv` — الأَشكال القَنونيَّة
  • `data/contracts/lists/singular_term_prefixes.csv` — البَوادِئ المَسموحَة
  • `data/contracts/lists/quran_recitation_marks.csv` — عَلامات التِّلاوة

كُلّ ادّعاء بِأَنّ كَلِمَة لَفظ مُنفَرِد يَحمِل:
  • source_of_claim: "singular_terms:<canonical> + prefix:<prefix>" (إن وُجِدَت)
  • kind: Certificate (لَفظ مُنفَرِد مُطابِق) | Hypothesis (مُطابِقَة بِشَبَه)

لا قَوائم inline في الكود — كُلّ شَيء مِن CSV.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows


CONTRACT_NAME = "SingularTermDetector:v1"


@dataclass
class SingularTermResult:
    is_singular_term: bool = False
    canonical_form: str = ""
    matched_prefix: str = ""
    kind: str = "Zero"               # Certificate | Hypothesis | Zero
    source_of_claim: str = ""
    contract: str = CONTRACT_NAME


def _strip_diacritics(s: str) -> str:
    """نَزع التَّشكيلات (لِلمُطابَقَة، لَيس لِلتَّحويل النِّهائيّ)."""
    return "".join(c for c in s if c not in "ًٌٍَُِّْـ")


class SingularTermDetector:
    """كاشِف لَفظ مُنفَرِد قابِل لِلتَّوسعَة عَبر CSVs."""

    def __init__(self) -> None:
        terms_rows = _load_rows("singular_terms.csv", subdir="lists")
        prefix_rows = _load_rows("singular_term_prefixes.csv", subdir="lists")
        recitation_rows = _load_rows("quran_recitation_marks.csv", subdir="lists")
        self._canonical_forms: set[str] = {
            r["canonical_form"] for r in terms_rows if r.get("canonical_form")
        }
        # رَتِّب البَوادِئ بِالأَطوَل أَوّلًا لِيُجَرَّب «ولل» قَبل «ول» قَبل «و»
        self._prefixes: list[dict] = sorted(
            (r for r in prefix_rows if r.get("prefix")),
            key=lambda r: -len(r.get("prefix", "")),
        )
        self._recitation_marks: set[str] = {
            r["mark"] for r in recitation_rows if r.get("mark")
        }

    # ------------------------------------------------------------------
    # نَزع عَلامات التِّلاوة — مُشتَرَك بَين كُلّ المُكَوِّنات
    # ------------------------------------------------------------------

    def strip_recitation_marks(self, text: str) -> str:
        """يَنزَع عَلامات التِّلاوة الصَّغيرَة (ۢ ۤ ۥ ۦ ۧ ۨ ۭ) — مَصدَرُها
        `data/contracts/lists/quran_recitation_marks.csv`."""
        if not text:
            return text
        return "".join(c for c in text if c not in self._recitation_marks)

    # ------------------------------------------------------------------
    # كَشف لَفظ مُنفَرِد (مَع تَوَسُّع لِبَوادِئ)
    # ------------------------------------------------------------------

    def detect(self, word: str) -> SingularTermResult:
        """يَتَفَحَّص ما إذا كانَت `word` لَفظًا مُنفَرِدًا (بِبَوادِئ أَو بِدونها).

        خُوارِزميَّة:
          1. نَزع عَلامات التِّلاوة
          2. نَزع التَّشكيلات
          3. تَطبيع ٱ → ا (alif wasla)
          4. مُطابَقَة مَع الأَشكال القَنونيَّة (Certificate)
          5. لِكُلّ prefix (الأَطوَل أَوّلًا):
             - حَذف الـ prefix → stem
             - تَجريب stem و "ا"+stem (لِإِعادَة هَمزَة الوَصل المَحذوفَة)
             - إِن طابَق → Certificate (لأَنّ الـ prefix مَسموح في الـ CSV)
        """
        if not word:
            return SingularTermResult()
        clean = self.strip_recitation_marks(word)
        plain = _strip_diacritics(clean).replace("ٱ", "ا")

        # 1. مُطابَقَة مُباشَرَة
        if plain in self._canonical_forms:
            return SingularTermResult(
                is_singular_term=True,
                canonical_form=plain,
                matched_prefix="",
                kind="Certificate",
                source_of_claim=f"singular_terms:{plain}",
            )

        # 2. مُطابَقَة مَع prefix (اعتمادًا على restore_strategy من CSV)
        for prefix_row in self._prefixes:
            prefix = prefix_row["prefix"]
            strategy = prefix_row.get("restore_strategy", "direct_or_alif_wasl")
            if not plain.startswith(prefix):
                continue
            stem = plain[len(prefix):]
            # المُحاوَلَة 1: stem كَما هو
            if stem in self._canonical_forms:
                return SingularTermResult(
                    is_singular_term=True,
                    canonical_form=stem,
                    matched_prefix=prefix,
                    kind="Certificate",
                    source_of_claim=(
                        f"singular_terms:{stem} + singular_term_prefixes:{prefix} (strategy:direct)"
                    ),
                )
            # المُحاوَلَة 2: إِعادَة هَمزَة الوَصل («بِالله» plain=«بالله» → strip "ب" → "الله» ✓ بِالمُباشَر؛
            # لَكِنّ «وَالله» plain=«والله» → strip "و" → «الله» ✓ بِالمُباشَر؛
            # تُفيد لو حُذِفَت الـ ا بَعد التَّشكيل — أَقَلّ شُيوعًا في النَّصّ القياسيّ)
            if strategy in ("direct_or_alif_wasl", "alif_lam_assimilation"):
                with_alif = "ا" + stem
                if with_alif in self._canonical_forms:
                    return SingularTermResult(
                        is_singular_term=True,
                        canonical_form=with_alif,
                        matched_prefix=prefix,
                        kind="Certificate",
                        source_of_claim=(
                            f"singular_terms:{with_alif} + "
                            f"singular_term_prefixes:{prefix} (strategy:alif_wasl_restore)"
                        ),
                    )
            # المُحاوَلَة 3: إِدغام لام-لام («لِلَّه» = لـ + الـ + الله = «لله»)
            # نُعيد بِناء: «ا» + prefix + stem لِنَستَردّ هَمزَة الوَصل + لام «ال»
            if strategy == "alif_lam_assimilation":
                with_alif_lam = "ا" + prefix + stem
                if with_alif_lam in self._canonical_forms:
                    return SingularTermResult(
                        is_singular_term=True,
                        canonical_form=with_alif_lam,
                        matched_prefix=prefix,
                        kind="Certificate",
                        source_of_claim=(
                            f"singular_terms:{with_alif_lam} + "
                            f"singular_term_prefixes:{prefix} (strategy:alif_lam_assimilation)"
                        ),
                    )

        return SingularTermResult()


# ============================================================================
# نُسخَة مُشتَرَكَة (lazy singleton)
# ============================================================================

_INSTANCE: Optional[SingularTermDetector] = None


def get_singular_term_detector() -> SingularTermDetector:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = SingularTermDetector()
    return _INSTANCE


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    d = get_singular_term_detector()
    cases = [
        ("الله", True), ("اللهم", True),
        ("ٱللَّهُ", True), ("اللَّهِ", True), ("اللَّهَ", True),
        ("وَٱللَّهُ", True), ("فَٱللَّهُ", True), ("بِٱللَّهِ", True),
        ("لِلَّهِ", True), ("فَلِلَّهِ", True), ("وَلِلَّهِ", True),
        ("كَاللَّهِ", True),
        # سَلبيَّات
        ("كِتَابٌ", False), ("بَيْتٌ", False), ("الرَّحْمَنُ", False),
        # تَجارِب عَلامات التِّلاوة
        ("ٱللَّهٌۥ", True),  # مع ۥ
    ]
    print(f"contract: {d}")
    print(f"canonical_forms: {sorted(d._canonical_forms)}")
    print(f"prefixes: {d._prefixes}")
    print(f"recitation_marks: {sorted(d._recitation_marks)}")
    print()
    ok = 0
    for word, expected in cases:
        r = d.detect(word)
        mark = "✓" if r.is_singular_term == expected else "✗"
        if r.is_singular_term == expected:
            ok += 1
        print(f"  {mark} {word:<14} → is_singular={r.is_singular_term}  "
              f"prefix={r.matched_prefix or '—'}  src={r.source_of_claim or '—'}")
    print(f"\n{ok}/{len(cases)} ✓")
