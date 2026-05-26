"""Show i3rab analysis on Al-Fatiha — full table per token.

Demonstrates the v1 i3rab engine output on every Fatiha word.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "clean_code"))

from i3rab_engine import I3rabEngine  # type: ignore
from i3rab_engine.types import CASE_IDS, MARK_IDS  # type: ignore


FATIHA = [
    "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ",
    "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
    "الرَّحْمَنِ الرَّحِيمِ",
    "مَالِكِ يَوْمِ الدِّينِ",
    "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ",
    "اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ",
    "صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ",
]


def main() -> int:
    eng = I3rabEngine()
    for n, ayah in enumerate(FATIHA, start=1):
        print(f"\n══════════════════════════════════════════════════════════════════════")
        print(f"  [1:{n}]  {ayah}")
        print(f"══════════════════════════════════════════════════════════════════════")
        s = eng.analyze_sentence(ayah)
        print(f"{'الكلمة':<22} {'نوع':<11} {'حالة':<10} {'علامة':<10} {'الدور الإعرابي':<32}")
        print("-" * 100)
        for t in s.tokens:
            case_name = CASE_IDS.get(t.case_id, "—") if t.case_id else "—"
            mark_name = MARK_IDS[t.mark_id][0] if t.mark_id else "—"
            print(
                f"{t.token:<22} {t.word_class:<11} {case_name:<10} "
                f"{mark_name:<10} {t.role_phrase:<32}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
