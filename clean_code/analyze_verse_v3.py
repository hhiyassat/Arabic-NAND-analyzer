"""analyze_verse_v3.py — مُحَلِّل آيَة شامِل بِكُلّ الـ7 phases.

يَعرِض الطَّبَقات اختياريًّا بِالـ flags:
  --morph         Phase A: تَطبيع + تَقطيع + جَذر + وَزن
  --i3rab         Layers 1+2+3: WordClass + Case + Role
  --samarrai      Maani KB (المُجَلَّدات الأَربَعَة)
  --relations     Phase C: RelationGraph
  --events        Phase D: EventGraph + Transformations
  --resolution    Phase E: Anaphora + Deixis + Relative + Bridging
  --meaning       Phase F: MeaningGraph الكامِل
  --reasoning     Phase G: تَجريب أَسئلَة عَلى الآيَة
  --all           كُلّ الطَّبَقات
  --quiet         بِدون أَيّ طَبَقَة (فَقَط النَّصّ)

CLI:
  python3 analyze_verse_v3.py --verse 1:5 --all
  python3 analyze_verse_v3.py --verse 2:255 --i3rab --relations --meaning
  python3 analyze_verse_v3.py --verse 1:5 --reasoning
  python3 analyze_verse_v3.py "نَصّ مُشَكَّل" --all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
QURAN_PATH = _HERE.parent / "data" / "quran-uthmani-with-pause-mark.txt"


# ─────────────────────────────────────────────────────────────────
# تَحميل الآيَة
# ─────────────────────────────────────────────────────────────────

def load_verse(ref: str) -> str | None:
    surah, ayah = ref.split(":")
    if not QURAN_PATH.exists():
        return None
    with open(QURAN_PATH, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) >= 3 and parts[0] == str(int(surah)) and parts[1] == str(int(ayah)):
                return parts[2]
    return None


# ─────────────────────────────────────────────────────────────────
# عَرض الطَّبَقات
# ─────────────────────────────────────────────────────────────────

SEPARATOR = "─" * 70


def _heading(title: str, emoji: str = "📍") -> str:
    return f"\n{emoji} {title}\n{SEPARATOR}"


def show_morph(text: str):
    """L0-L2: normalizer + segmenter + root + wazn."""
    print(_heading("L1 — التَّقطيع (Segmentation) + L2 — الصَّرف (Morphology)", "🔤"))
    try:
        from segmenter import segment
        # كُلّ كَلِمَة عَلى حِدَة
        for word in text.split():
            r = segment(word)
            # SegmentationResult: prefixes/suffixes (strings) + parallel _tags
            prefs_pairs = list(zip(r.prefixes, r.prefix_tags))
            sufs_pairs = list(zip(r.suffixes, r.suffix_tags))
            prefs = "+".join(f"{form}({tag})" for form, tag in prefs_pairs) or "—"
            stem = r.stem or "—"
            sufs = "+".join(f"{form}({tag})" for form, tag in sufs_pairs) or "—"
            print(f"  {word:20s} ← prefixes={prefs} | stem={stem} | suffixes={sufs}")
    except Exception as e:
        print(f"  ⚠ تَخَطّي: {e}")


def show_i3rab(text: str, sent):
    """L3 — i3rab: WordClass + Case + Role."""
    print(_heading("L3 — الإِعراب (I3rab: WordClass + Case + Role)", "🔍"))
    for t in sent.tokens:
        tk = getattr(t, "token", "?")
        wc = t.word_class
        role = getattr(t, "role_phrase", "") or "—"
        root = t.root or "—"
        wazn = t.wazn or "—"
        print(f"  {tk:20s} → class={wc:18s} | role={role:25s} | root={root} | wazn={wazn}")


def show_samarrai(text: str):
    """KB.SAM — Maani al-Samarra'i (4 vols) + constructions."""
    print(_heading("KB.SAM — مَعاني السَّامَرّائيّ (4 مُجَلَّدات + التَّراكيب)", "📚"))
    try:
        from samarrai_analyzer import analyze
        ta = analyze(text)
        # PATCH 4 (2026-05-26) — Certified Operator Gate.
        # Filter KB.SAM claims against the production segmenter so that
        # operator meanings (الكاف لِلتَّشبيه / واو القَسَم / السين تَنفيس / ...)
        # are emitted only when the corresponding clitic is actually
        # certified by L1 prefix/suffix tags. See samarrai_certified_operator_gate.py.
        try:
            from samarrai_certified_operator_gate import gate_text_analysis
            gate_text_analysis(ta)
        except Exception:
            pass  # gate unavailable → fall back to ungated KB.SAM
        for wa in ta.words:
            if not wa.claims:
                continue
            print(f"  «{wa.word}»:")
            for c in wa.claims[:3]:  # أَوَّل 3 ادِّعاءات
                if c.proof_kind == "Zero":
                    continue
                sym = "✓" if c.proof_kind == "Certificate" else "?"
                print(f"      {sym} [ج{c.source_part}] {c.meaning_ar[:60]}")
        if ta.constructions:
            print(f"\n  التَّراكيب المَكشوفَة:")
            for cm in ta.constructions:
                print(f"      ▸ {cm.construction_id}: {cm.pattern_name}")
    except Exception as e:
        print(f"  ⚠ تَخَطّي: {e}")


def show_relations(sent, rg):
    """L4 — Relations: RelationGraph."""
    print(_heading("L4 — العَلاقات (Relations — 17 type)", "🔗"))
    if not rg.relations:
        print("  لا عَلاقات مَكشوفَة")
        return
    for r in rg.relations:
        sym = "✓" if r.kind == "Certificate" else "?"
        op = f"[{r.operator}]" if r.operator else ""
        # نَصّ الـ source / target — يَتَفَحَّص أَوَّلًا عُقَد الـ graph
        # (تَشمَل العُقَد المُستَتِرَة implicit_t...)
        src_name = _resolve_id(sent, r.source_id, rg)
        tgt_name = _resolve_id(sent, r.target_id, rg)
        # عَلامَة لِلمُستَتِر
        if r.source_id.startswith("implicit_"):
            src_name = f"⊕{src_name}"
        print(f"  {sym} {r.name:18s}{op} : {src_name} → {tgt_name}")


def show_events(text: str, sent, rg):
    """L5 — Events: EventGraph + Transformations."""
    print(_heading("L5 — الأَحداث (Events + Transformations)", "⚡"))
    try:
        from event_extractor import EventExtractor
        eg = EventExtractor().extract(sent, rg)
        if not eg.events:
            print("  لا أَحداث مَكشوفَة")
            return
        for e in eg.events:
            sym = "✓" if e.kind == "Certificate" else "?"
            kind_word = "Transformation" if hasattr(e, "subject") and e.subject else "Event"
            print(f"  {sym} {kind_word}[{e.type}]")
            if e.agent: print(f"      agent={e.agent}")
            if e.patient: print(f"      patient={e.patient}")
            if e.location: print(f"      location={e.location}")
            if e.tense != "unknown": print(f"      tense={e.tense}")
            # PATCH 5 — show mood / speech_act when CommandLamEventMood fired.
            if getattr(e, "mood", ""): print(f"      mood={e.mood}")
            if getattr(e, "speech_act", ""): print(f"      speech_act={e.speech_act}")
            if e.time_value: print(f"      time={e.time_value}")
            if hasattr(e, "subject") and e.subject:
                sb = e.state_before
                sa = e.state_after
                print(f"      transformation: {sb} → {sa}")
    except Exception as e:
        print(f"  ⚠ تَخَطّي: {e}")


def show_resolution(sent, eg=None, prior_context=None):
    """L6 — Resolution: Anaphora + Deixis + Relative + Bridging + Transformation + Detached."""
    print(_heading("L6 — التَّعيين (Resolution — 6 type)", "🎯"))
    try:
        from resolution_engine import ResolutionEngine
        res = ResolutionEngine().resolve(sent, eg, prior_context=prior_context or [])
        if not res.resolutions:
            print("  لا تَعيينات مَكشوفَة")
            return
        for r in res.resolutions:
            sym = "✓" if r.kind == "Certificate" else ("?" if r.kind == "Hypothesis" else "✗")
            tgt = r.target_surface if r.has_target else "بِلا مَرجِع"
            alts = f" (+{len(r.candidates)-1} alts)" if len(r.candidates) > 1 else ""
            print(f"  {sym} {r.resolution_type:18s}: {r.referent} → {tgt}{alts}")
    except Exception as e:
        print(f"  ⚠ تَخَطّي: {e}")


def _build_prior_context_for_verse(verse_ref: str | None) -> list[dict]:
    """يَبني سِياقًا أَوَّليًّا لِلآيَة: مَن القائِل + مَن المُخاطَب.

    لِلفاتِحَة (سُورَة 1): العَبد يُخاطِب اللَّه.
      • speaker = العَبد (نَحن)
      • addressee = اللَّه (مُستَنبَط مِن آيات 1:1-1:4)
    لِبَقيَّة السُّوَر: لا context تِلقائيّ — يَترُك فارِغًا.
    """
    if not verse_ref:
        return []
    try:
        surah_num = int(verse_ref.split(":")[0])
    except (ValueError, IndexError):
        return []
    if surah_num == 1:
        return [
            {
                "id": "speaker_servant",
                "role": "speaker",
                "surface": "العَبد",
                "gender": "M",
                "number": "PL",
                "source": "الفاتِحَة 1:5 — العَبد يَدعو",
            },
            {
                "id": "addressee_allah",
                "role": "addressee",
                "surface": "اللَّه",
                "gender": "M",
                "number": "SG",
                "source": "الفاتِحَة 1:1-1:4 — المَدعُوّ هو اللَّه",
            },
        ]
    return []


def show_meaning(text: str):
    """L7 — MeaningGraph: full unified graph."""
    print(_heading("L7 — شَبَكَة المَعنى (MeaningGraph)", "🧠"))
    try:
        from meaning_assembler import MeaningAssembler
        graph = MeaningAssembler().assemble(text)
        s = graph.stats()
        print(f"  العُقَد: {s['nodes']} ({s['certificate_nodes']}C + {s['hypothesis_nodes']}H)")
        print(f"  الرَّوابِط: {s['edges']} ({s['certificate_edges']}C + {s['hypothesis_edges']}H)")
        print(f"  التَّغطيَة: {s['coverage_pct']}%")
        print(f"  Entropy (الغُموض): {s['entropy']}")
        contradictions_count = s['contradictions']
        cons_text = 'نَعَم ✓' if s['is_consistent'] else f'لا — {contradictions_count} تَناقُض'
        print(f"  مُتَّسِق: {cons_text}")
        if graph.contradictions:
            print(f"\n  التَّناقُضات:")
            for c in graph.contradictions:
                print(f"    ✗ [{c.severity}] {c.description}")
    except Exception as e:
        print(f"  ⚠ تَخَطّي: {e}")


def show_reasoning_interactive(text: str):
    """L8 — Reasoning: Q/A + out-of-scope rejection."""
    print(_heading("L8 — الِاستِدلال (Reasoning Q/A)", "❓"))
    try:
        from reasoning_engine import ReasoningEngine
        eng = ReasoningEngine()
        # أَسئلَة قِياسيَّة لِكُلّ آيَة
        questions = [
            "مَن الفاعِل؟",
            "ماذا حَدَث؟",
            "أَين حَدَث؟",
            "متى حَدَث؟",
            "ما تَسَلسُل الأَحداث؟",
            "إلى ماذا تَحَوَّلَ شَيء؟",
            "ما تَفسير هذه الآيَة؟",  # يَجِب رَفض
        ]
        for q in questions:
            a = eng.answer(text, q)
            sym = a.symbol
            scope = "✅" if a.query.is_in_scope else "🚫"
            ans = a.answer if a.answer else a.rejected_reason
            print(f"  {scope} {q}")
            print(f"      {sym} [{a.kind}] {ans[:80] if ans else ''}")
    except Exception as e:
        print(f"  ⚠ تَخَطّي: {e}")


def _resolve_id(sent, tid: str, rg=None) -> str:
    if tid == "—":
        return "—"
    # عُقَد مُستَتِرَة (implicit_t...) — نَستَخرِج surface مِن الـ graph
    if rg is not None and tid in getattr(rg, "nodes", {}):
        node = rg.nodes[tid]
        s = getattr(node, "surface", "") or ""
        if s:
            return s
    if not tid.startswith("t"):
        return tid
    try:
        idx = int(tid[1:])
        if 0 <= idx < len(sent.tokens):
            return getattr(sent.tokens[idx], "token", tid)
    except (ValueError, IndexError):
        pass
    return tid


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="مُحَلِّل آيَة شامِل بِكُلّ الـ7 phases — flags اختياريَّة",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أَمثِلَة:
  python3 analyze_verse_v3.py --verse 1:5 --all
  python3 analyze_verse_v3.py --verse 2:255 --i3rab --relations
  python3 analyze_verse_v3.py "إِيَّاكَ نَعْبُدُ" --meaning --reasoning
""",
    )
    p.add_argument("text", nargs="?", help="النَّصّ مُباشَرَةً")
    p.add_argument("--verse", help="آيَة (سُورة:آية)")

    p.add_argument("--morph", action="store_true", help="L1+L2 — التَّقطيع + الصَّرف")
    p.add_argument("--i3rab", action="store_true", help="L3 — الإِعراب")
    p.add_argument("--samarrai", action="store_true", help="KB.SAM — مَعاني السَّامَرّائيّ")
    p.add_argument("--relations", action="store_true", help="L4 — العَلاقات")
    p.add_argument("--events", action="store_true", help="L5 — الأَحداث")
    p.add_argument("--resolution", action="store_true", help="L6 — التَّعيين")
    p.add_argument("--meaning", action="store_true", help="L7 — شَبَكَة المَعنى")
    p.add_argument("--reasoning", action="store_true", help="L8 — الِاستِدلال")
    p.add_argument("--all", action="store_true", help="كُلّ الـ9 طَبَقات + KB.SAM")
    p.add_argument("--quiet", action="store_true", help="بِدون أَيّ طَبَقَة")

    args = p.parse_args()

    # تَحميل النَّصّ
    if args.verse:
        text = load_verse(args.verse)
        if not text:
            print(f"⚠ لَم نَجِد {args.verse}")
            sys.exit(1)
        title = f"📖 الآيَة {args.verse}"
    elif args.text:
        text = args.text
        title = "📝 نَصّ مُباشَر"
    else:
        p.print_help()
        sys.exit(1)

    # عَرض النَّصّ
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}")
    print(f"\n{text}\n")

    if args.quiet:
        return

    # تَفعيل كُلّ الـflags لَو --all
    show_all = args.all or not any([
        args.morph, args.i3rab, args.samarrai, args.relations,
        args.events, args.resolution, args.meaning, args.reasoning,
    ])

    # تَجهيز الـ engines مَرَّة واحِدَة
    sent = None
    rg = None
    eg = None

    if args.morph or show_all:
        show_morph(text)

    if (args.i3rab or args.relations or args.events or args.resolution
            or args.meaning or show_all):
        try:
            from i3rab_engine.engine import I3rabEngine
            sent = I3rabEngine().analyze_sentence(text)
        except Exception as e:
            print(f"\n⚠ فَشَل i3rab: {e}")
            return

    if args.i3rab or show_all:
        show_i3rab(text, sent)

    if args.samarrai or show_all:
        show_samarrai(text)

    if args.relations or args.events or args.meaning or show_all:
        try:
            from relation_extractor import RelationExtractor
            rg = RelationExtractor().extract(sent)
        except Exception as e:
            print(f"\n⚠ فَشَل relations: {e}")
            return

    if args.relations or show_all:
        show_relations(sent, rg)

    if args.events or args.meaning or show_all:
        try:
            from event_extractor import EventExtractor
            eg = EventExtractor().extract(sent, rg)
        except Exception:
            eg = None

    if args.events or show_all:
        show_events(text, sent, rg)

    if args.resolution or show_all:
        prior_ctx = _build_prior_context_for_verse(args.verse)
        show_resolution(sent, eg, prior_context=prior_ctx)

    if args.meaning or show_all:
        show_meaning(text)

    if args.reasoning or show_all:
        show_reasoning_interactive(text)

    print(f"\n{'='*70}")
    print(f"✅ التَّحليل الكامِل مُكتَمِل")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
