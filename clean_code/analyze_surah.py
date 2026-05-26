"""analyze_surah.py — تَحليل سُورَة كامِلَة مَع تَتَبُّع الخِطاب عَبر الآيات.

الِاستخدام:
    python analyze_surah.py 1            # الفاتِحَة
    python analyze_surah.py 112          # الإِخلاص
    python analyze_surah.py 1 --json     # JSON output
"""

from __future__ import annotations

import argparse
import json
import sys
import re
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from surah_processor import SurahProcessor
from clause_segmenter import _strip_pause_marks


def _find_quran_path():
    candidates = [
        Path("/Users/husseinhiyassat/fractal/hussein/data/quran-uthmani-with-pause-mark.txt"),
        _HERE.parent.parent / "data" / "quran-uthmani-with-pause-mark.txt",
        _HERE.parent / "data" / "quran-uthmani-with-pause-mark.txt",
        Path("/sessions/nice-epic-cannon/mnt/hussein/data/quran-uthmani-with-pause-mark.txt"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def load_surah(surah: int) -> list:
    path = _find_quran_path()
    if not path:
        raise FileNotFoundError("Quran file not found")
    verses = []
    prefix = f"{surah}|"
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.startswith(prefix):
                parts = line.strip().split("|", 2)
                if len(parts) == 3:
                    s, v, text = parts
                    verses.append((int(v), _strip_pause_marks(text)))
    return verses


def format_arabic_report(surah_num: int, verses: list, results: list) -> str:
    out = []
    out.append("═" * 78)
    out.append(f"  تَحليل سُورَة {surah_num} ({len(verses)} آية) — مَع تَتَبُّع الخِطاب عَبر الآيات")
    out.append("═" * 78)

    for (v_num, text), r in zip(verses, results):
        out.append("")
        out.append(f"  ── الآية {surah_num}:{v_num} ──")
        out.append(f"  {text}")
        if r.get("active_addressee"):
            out.append(f"    ▸ المُخاطَب المُستَمِرّ: «{r['active_addressee'].get('text', '')}»  "
                       f"(مِن: {r['active_addressee'].get('source_of_claim', '')[:60]})")
        for f in r.get("frames", []):
            speaker_txt = f.speaker.text if f.speaker else "—"
            addressee_txt = f.addressee.text if f.addressee else "—"
            out.append(f"    ◆ frame [{f.speech_type}]  قائِل=«{speaker_txt}»  مُخاطَب=«{addressee_txt}»")
            if f.parent_frame_id:
                out.append(f"        أَب: {f.parent_frame_id}")
        for ref in r.get("pronoun_refs", []):
            host = ref.get("host_token", "?")
            referent = ref.get("referent_text") or "—"
            src = ref.get("referent_source", "")
            out.append(f"    ⤺ «{ref.get('clitic', '?')}» في «{host}» → «{referent}»  [{src}]")

    out.append("")
    out.append("═" * 78)
    out.append("  انتَهى.")
    out.append("═" * 78)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("surah", type=int, help="رَقم السُّورَة (1-114)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    verses = load_surah(args.surah)
    if not verses:
        print(f"السُّورَة {args.surah} غَير مَوجودَة", file=sys.stderr)
        sys.exit(1)

    sp = SurahProcessor()
    results = []
    for v_num, text in verses:
        r = sp.process_verse(text, ref=f"{args.surah}:{v_num}")
        results.append(r)

    if args.json:
        out = {
            "surah": args.surah,
            "n_verses": len(verses),
            "verses": [
                {
                    "ref": r["ref"],
                    "frames": [f.to_dict() for f in r["frames"]],
                    "active_addressee": r["active_addressee"],
                    "active_speaker": r["active_speaker"],
                    "pronoun_refs": r["pronoun_refs"],
                }
                for r in results
            ],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2,
                         default=lambda o: str(o)))
    else:
        print(format_arabic_report(args.surah, verses, results))


if __name__ == "__main__":
    main()
