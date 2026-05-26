#!/usr/bin/env python3
"""showcase_fractal_coord.py — عرض الإحداثيّة الـ fractal لكل token.

يُظهِر كيف أنّ نفس الكلمة في سياقات مختلفة تأخذ إحداثيّات مختلفة،
مع تطابق المستويات التي لم يتغيّر مكوّنها (مثل L2 = الصرف).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "clean_code"))

from i3rab_engine import I3rabEngine  # type: ignore
from wazn_data import DIACRITICS  # type: ignore


def _strip(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def main() -> int:
    print("\n" + "═" * 72)
    print("  عرض FractalCoordinate — نفس الكلمة، سياقات مختلفة")
    print("═" * 72)

    eng = I3rabEngine()

    # ثلاث جمل: «الكتاب» فيها بأدوار نحوية مختلفة
    cases = [
        ("بعد حرف جر",         "فِي الْكِتَابِ"),
        ("مفعول به بعد فعل",   "قَرَأَ الطَّالِبُ الْكِتَابَ"),
        ("مبتدأ بعد اسم إشارة", "هَذَا الْكِتَابُ نَافِعٌ"),
    ]

    rows = []
    for label, text in cases:
        s = eng.analyze_sentence(text)
        for t in s.tokens:
            if "الكتاب" in _strip(t.token):
                rows.append((label, text, t))

    # عرض بسطر واحد لكل ظهور
    print()
    print(f"{'السياق':<28} {'السطح':<14} {'الدور':<22} {'hash (24 hex)'}")
    print("─" * 100)
    for label, text, t in rows:
        print(
            f"{label:<28} {t.token:<14} {t.role_phrase:<22} {t.coord_hash_dotted}"
        )

    print()
    print("لاحظ تطابق L2 (المستوى الصرفي):")
    l2s = [t.coord_hash_dotted.split(".")[2] for _, _, t in rows]
    print(f"  L2 hashes: {l2s}")
    print(f"  متطابقة؟ {len(set(l2s)) == 1}")
    print()
    print("ولاحظ اختلاف L3 (المستوى النحوي):")
    l3s = [t.coord_hash_dotted.split(".")[3] for _, _, t in rows]
    print(f"  L3 hashes: {l3s}")
    print(f"  متمايزة؟ {len(set(l3s)) == len(l3s)}")
    print()
    print("هذا هو المعنى البنيوي لـ fractal: ثبات الجوهر، تغيّر السياق.")
    print()

    # عرض المستويات الستّة بالتفصيل لـ token واحد
    print("─" * 72)
    print("التفصيل الكامل للحالة الأولى:")
    print("─" * 72)
    label, text, t = rows[0]
    print(f"\nالجملة: {text}")
    print(f"الكلمة: {t.token}\n")
    levels = t.coord_path.split("·L")
    print("  L0 (الحامل):       ", levels[0].replace("L0[", "").rstrip("]"))
    for lvl in levels[1:]:
        idx = lvl[0]
        body = lvl[2:].rstrip("]")
        names = {
            "1": "L1 (البنية):       ",
            "2": "L2 (الصرف):        ",
            "3": "L3 (النحو):        ",
            "4": "L4 (الجوار):       ",
            "5": "L5 (العقود):       ",
        }
        print(f"  {names.get(idx, 'L?')}", body[:80] + ("…" if len(body) > 80 else ""))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
