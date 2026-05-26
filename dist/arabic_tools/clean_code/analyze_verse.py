"""analyze_verse.py — تَحليل آية كَامِل (M1 + RootPipeline).

يَأخُذ نَصّ آية (مِن CLI أو stdin) ويُجري كُلّ التَّحلِيلات الَّتِي طَوَّرنَاهَا:

  ① RootPipeline لِكُلّ كَلِمَة:
       jalalah / closed_class / jamid / open_class
       جذر + وزن + ProofObject (Certificate | Hypothesis | Zero)

  ② M1Pipeline لِلنَّصّ كَامِلًا:
       A. ClauseSegmenter      — تَقطيع الجُمَل (مع pause marks)
       B. SpeechActDetector    — نَوع الفِعل الكَلامِيّ (خَبَر/أمر/استفهام/نِداء)
       C. NegationDetector     — أَدوات النَّفي + النِّطاق
       D. ModalDetector        — أَدوات الجِهَة (قَد، لَن، سَوف، ...)

الاستخدام:
    python analyze_verse.py "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ"
    python analyze_verse.py 1:1                  # بِرَقم الآية (سورة:آية)
    python analyze_verse.py 2:285
    echo "..." | python analyze_verse.py
    python analyze_verse.py --json 1:1           # JSON output
    python analyze_verse.py --verbose "..."      # عرض البَدائل

العَقد: per 14_Minimal_Complete_Theory — لا قَواعد inline. كُلّ القَرارات
تَمُرّ عَبر العُقود (data/contracts/*.csv) وتَحمِل source_of_claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from m1_pipeline import M1Pipeline, M1Result
from root_pipeline import RootPipeline
from clause_segmenter import _strip_pause_marks
from text_graph_assembler import TextGraphAssembler


CONTRACT_NAME = "VerseAnalyzer:v2"

# المَصدَر القَطعِيّ لِنَصّ القرآن (بِعَلامات الوَقف).
# نَبحَث في عِدَّة مَواقِع مُحتَمَلَة لِيَعمَل في بِيئات مُختلِفَة.
def _find_quran_path() -> Optional[Path]:
    from typing import Optional, Tuple as _O  # local
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

QURAN_TEXT_PATH = _find_quran_path()


# ============================================================================
# Ayah lookup (surah:ayah → verse text)
# ============================================================================

import re as _re

_AYAH_REF = _re.compile(r"^\s*(\d+)\s*[:.\-]\s*(\d+)\s*$")


def _load_ayah(surah: int, ayah: int) -> str:
    """يَقرَأ آية مُحَدَّدة مِن المَصدَر القَطعِيّ (uthmani بِعَلامات الوَقف).

    التَّنسِيق: surah|ayah|text  (6,236 سَطرًا)
    """
    if QURAN_TEXT_PATH is None or not QURAN_TEXT_PATH.exists():
        raise FileNotFoundError(
            "المَصدَر القَطعِيّ لِنَصّ القرآن غَير مَوجود "
            "(quran-uthmani-with-pause-mark.txt)."
        )
    prefix = f"{surah}|{ayah}|"
    with QURAN_TEXT_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if line.startswith(prefix):
                return line[len(prefix):].rstrip("\n")
    raise ValueError(f"لَم تُوجَد الآية {surah}:{ayah} في المَصدَر.")


def _resolve_input(arg: str) -> tuple[str, str]:
    """يُمَيِّز بَين رَقم آية (1:1) ونَصّ مُباشَر.

    Returns (verse_text, source_label).
    """
    m = _AYAH_REF.match(arg)
    if m:
        s, a = int(m.group(1)), int(m.group(2))
        text = _load_ayah(s, a)
        return text, f"quran:{s}:{a}"
    return arg, "inline_text"


# ============================================================================
# Tokenizer (whitespace + filter punctuation)
# ============================================================================

_PUNCTUATION = set(".،؛؟!:()[]{}«»\"'،؛؟")


def _tokenize_words(text: str) -> list[str]:
    """تَقسيم النَّصّ إلى كَلِمات (بِناءً على المَسافات). تُحذَف عَلامات
    التَّرقِيم في الأَطراف، تُحفَظ التَّشكِيلات والحَركات داخل الكَلِمة.
    عَلامات الوَقف القرآنيّة تُنزَع قَبل التَّقسيم — ground truth، لا مَدخَل."""
    text = _strip_pause_marks(text)
    raw = text.split()
    out: list[str] = []
    for w in raw:
        # strip trailing/leading punctuation but keep internal characters
        w_clean = w
        while w_clean and w_clean[0] in _PUNCTUATION:
            w_clean = w_clean[1:]
        while w_clean and w_clean[-1] in _PUNCTUATION:
            w_clean = w_clean[:-1]
        if w_clean:
            out.append(w_clean)
    return out


# ============================================================================
# Full analysis
# ============================================================================

def analyze_verse(verse: str, source: str = "inline_text") -> dict:
    """يَجمَع كُلّ التَّحلِيلات في dict واحد."""
    root_pipe = RootPipeline()
    m1_pipe = M1Pipeline()
    text_graph_asm = TextGraphAssembler()

    # ① كُلّ كَلِمَة → جذر + وزن + ProofObject
    words = _tokenize_words(verse)
    word_analyses = []
    for w in words:
        po = root_pipe.analyze(w)
        word_analyses.append({
            "word": w,
            "word_plain": getattr(po, "word_plain", ""),
            "status": getattr(po, "status", "?"),
            "root": getattr(po, "root", "—"),
            "wazn": getattr(po, "wazn", "—"),
            "kind": getattr(po, "kind", "?"),
            "contract": getattr(po, "contract", ""),
            "source_of_claim": getattr(po, "source_of_claim", ""),
            "blockers": list(getattr(po, "blockers", []) or []),
        })

    # ② النَّصّ كَامِلًا → M1 (clauses + speech act + negation + modal)
    m1: M1Result = m1_pipe.analyze(verse)

    # ③ Phase C — RelationGraph + inter-clause + ضَمائر (جَلسات 14-23)
    text_graph = text_graph_asm.assemble(_strip_pause_marks(verse))

    return {
        "contract": CONTRACT_NAME,
        "source": source,
        "input": verse,
        "tokens": {
            "n_words": len(word_analyses),
            "words": word_analyses,
        },
        "m1": m1.to_dict(),
        "phase_c": text_graph.to_dict(),
    }


# ============================================================================
# Arabic pretty-printer
# ============================================================================

def _line(ch: str = "─", n: int = 78) -> str:
    return ch * n


_STATUS_AR = {
    "singular_term": "لَفظ مُنفَرِد",  # اللَّه — خارِج التَّصنيف
    "jalalah": "لَفظ مُنفَرِد",          # legacy alias
    "closed_class": "حَرف/مَبني (لا جَذر)",
    "jamid": "جامِد (لا جَذر اشتقاقيّ)",
    "open_class": "مُشتَقّ (مفتوح)",
    "no_match": "لَم يُحاذِ وَزن",
}

_KIND_AR = {
    "Certificate": "شَهادة",
    "Hypothesis": "فَرضِيَّة",
    "Zero": "صِفر",
}

_ACT_AR = {
    "assertion": "خَبَر",
    "command": "أَمر",
    "question": "استفهام",
    "vocative": "نِداء",
}


def format_arabic(result: dict) -> str:
    out = []
    out.append(_line("═"))
    out.append(f"  تَحليل آية — {result['contract']}")
    out.append(_line("═"))
    out.append(f"  المَصدَر: {result.get('source', '?')}")
    out.append(f"  النَّصّ:  {result['input']}")
    out.append("")

    # ─── ① تَحليل الكَلِمات ───
    words = result["tokens"]["words"]
    out.append(_line())
    out.append(f"  ① تَحليل الكَلِمات ({len(words)} كَلِمَة)")
    out.append(_line())
    out.append(f"  {'#':>2}  {'الكَلِمَة':<18} {'الحالة':<22} {'الجَذر':<8} {'الوَزن':<14} {'النَّوع':<10}")
    out.append(_line("·"))
    for i, w in enumerate(words):
        status_ar = _STATUS_AR.get(w["status"], w["status"])
        kind_ar = _KIND_AR.get(w["kind"], w["kind"])
        out.append(
            f"  {i+1:>2}  {w['word']:<18} {status_ar:<22} "
            f"{w['root']:<8} {w['wazn']:<14} {kind_ar:<10}"
        )
    out.append("")

    # ─── ② تَحليل M1 (الجُمَل + الفِعل الكَلامِيّ + النَّفي + الجِهَة) ───
    m1 = result["m1"]
    clauses = m1["clauses"]
    out.append(_line())
    out.append(f"  ② تَحليل M1 — الجُمَل والمَعنى ({len(clauses)} جُملة)")
    out.append(_line())

    for i, ca in enumerate(clauses):
        c = ca["clause"]
        sa = ca["speech_act"]
        out.append("")
        out.append(f"  ◆ الجُملة [{i+1}]: «{c['text']}»")
        out.append(f"     • نَوع الجُملة:  {c.get('type', '?')}")
        if c.get("connective"):
            out.append(f"     • الرَّابِط:     {c['connective']}")
        out.append(f"     • مَصدَر القَطع: {c.get('source_of_claim', '?')}  ({_KIND_AR.get(c.get('kind',''), c.get('kind',''))})")

        # Speech act
        act_ar = _ACT_AR.get(sa["act_type"], sa["act_type"])
        out.append(f"     • الفِعل الكَلامِيّ: {act_ar} — {sa.get('source_of_claim','')}  ({_KIND_AR.get(sa.get('kind',''), sa.get('kind',''))})")

        # Embedding
        if ca.get("embedding"):
            emb = ca["embedding"]
            out.append(f"     • تَضمِين: {emb.get('verb_kind','')} → {emb.get('creates_embedded','')}  rule={emb.get('name','')}")

        # Negations
        for n in ca.get("negations", []):
            out.append(
                f"     • نَفي @ {n.get('marker_position','?')}: "
                f"«{n.get('marker','')}»  أَثر={n.get('polarity_effect','')}  "
                f"({_KIND_AR.get(n.get('kind',''), n.get('kind',''))})"
            )

        # Modals
        for mod in ca.get("modals", []):
            out.append(
                f"     • جِهَة @ {mod.get('marker_position','?')}: "
                f"«{mod.get('marker','')}»  نَوع={mod.get('modal_type','')}  "
                f"قُوَّة={mod.get('strength','')}  "
                f"({_KIND_AR.get(mod.get('kind',''), mod.get('kind',''))})"
            )

    # ─── ③ تَحليل Phase C — العَلاقات + بَين الجُمَل + الضَّمائر ───
    pc = result.get("phase_c", {})
    if pc:
        out.append("")
        out.append(_line())
        out.append(
            f"  ③ تَحليل العَلاقات (Phase C) — "
            f"{pc.get('n_nodes', 0)} عُقدَة · "
            f"{pc.get('n_intra_relations', 0)} عَلاقَة داخِل جُمَل · "
            f"{pc.get('n_inter_clause_relations', 0)} عَلاقَة بَين جُمَل · "
            f"{pc.get('n_pronoun_references', 0)} ضَمير"
        )
        out.append(_line())

        # العَلاقات داخِل الجُمَل
        intra = pc.get("intra_relations", [])
        if intra:
            out.append("")
            out.append(f"  ▸ العَلاقات داخِل الجُمَل ({len(intra)})")
            out.append(_line("·"))
            for r in intra:
                src_id = r.get("source_id", "?")
                tgt_id = r.get("target_id", "?")
                src_surf = pc.get("nodes", {}).get(src_id, {}).get("surface", src_id)
                tgt_surf = pc.get("nodes", {}).get(tgt_id, {}).get("surface", tgt_id) if tgt_id != "—" else "—"
                op = r.get("operator")
                op_str = f"  via «{op}»" if op else ""
                kind_ar = _KIND_AR.get(r.get("kind", ""), r.get("kind", ""))
                out.append(
                    f"     • {r.get('name', '?'):<22} "
                    f"«{src_surf}» → «{tgt_surf}»{op_str}  ({kind_ar})"
                )

        # العَلاقات بَين الجُمَل
        inter = pc.get("inter_clause_relations", [])
        if inter:
            out.append("")
            out.append(f"  ▸ العَلاقات بَين الجُمَل ({len(inter)})")
            out.append(_line("·"))
            for r in inter:
                src_idx = r.get("source_clause_idx", -1)
                tgt_idx = r.get("target_clause_idx", -1)
                trigger = r.get("trigger", "")
                kind_ar = _KIND_AR.get(r.get("kind", ""), r.get("kind", ""))
                out.append(
                    f"     ◆ {r.get('name', '?'):<22} "
                    f"الجُملة[{src_idx+1}] ← الجُملة[{tgt_idx+1}]  via «{trigger}»  ({kind_ar})"
                )

        # الضَّمائر
        prefs = pc.get("pronoun_references", [])
        if prefs:
            out.append("")
            out.append(f"  ▸ إِحالات الضَّمائر ({len(prefs)})")
            out.append(_line("·"))
            for p in prefs:
                host = p.get("host_surface", "?")
                ref = p.get("referent_surface") or "—"
                cl = p.get("clitic", "?")
                gnp = f"{p.get('gender','')}/{p.get('number','')}/{p.get('person','')}"
                out.append(f"     ⤺ «{cl}» في «{host}» → «{ref}»  [{gnp}]")

    out.append("")
    out.append(_line("═"))
    out.append("  انتَهى التَّحلِيل.")
    out.append(_line("═"))
    return "\n".join(out)


# ============================================================================
# CLI
# ============================================================================

def main():
    ap = argparse.ArgumentParser(
        description="تَحليل آية كَامِل: RootPipeline + M1Pipeline"
    )
    ap.add_argument(
        "verse",
        nargs="?",
        help=(
            "إِمَّا نَصّ الآية مُباشَرَة، أَو رَقم الآية بِصِيغة (سُورة:آية) "
            "مِثل 1:1 أَو 2:285. لَو لَم يُمَرَّر، يُقرَأ مِن stdin."
        ),
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="إخراج JSON بَدَل التَّقرير العَرَبِيّ.",
    )
    ap.add_argument(
        "--verbose",
        action="store_true",
        help="إظهار البَدائل وَتَفاصِيل المَصدَر.",
    )
    args = ap.parse_args()

    if args.verse:
        raw = args.verse
    else:
        raw = sys.stdin.read().strip()

    if not raw:
        print("خطأ: لَم يُمَرَّر نَصّ ولا رَقم آية.", file=sys.stderr)
        sys.exit(1)

    try:
        verse, source = _resolve_input(raw)
    except (FileNotFoundError, ValueError) as e:
        print(f"خطأ: {e}", file=sys.stderr)
        sys.exit(2)

    result = analyze_verse(verse, source=source)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_arabic(result))


if __name__ == "__main__":
    main()
