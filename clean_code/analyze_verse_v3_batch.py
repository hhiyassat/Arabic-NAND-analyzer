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
from collections import Counter, defaultdict
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




def load_quran_index() -> list[tuple[str, str, str]]:
    """يُعيد القرآن كاملًا كقائمة: (surah, ayah, text)."""
    rows: list[tuple[str, str, str]] = []
    if not QURAN_PATH.exists():
        return rows
    with open(QURAN_PATH, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) >= 3:
                rows.append((str(int(parts[0])), str(int(parts[1])), parts[2]))
    return rows


def _parse_ref(ref: str) -> tuple[int, int]:
    try:
        surah, ayah = ref.strip().split(":", 1)
        return int(surah), int(ayah)
    except Exception as e:
        raise ValueError(f"صيغة الآية غير صحيحة: {ref!r}. استخدم مثل 2:282") from e


def _expand_ref_range(part: str) -> list[str]:
    """يدعم: 2:255 أو 2:255-2:257 أو 2:255-257."""
    part = part.strip()
    if not part:
        return []
    if "-" not in part:
        s, a = _parse_ref(part)
        return [f"{s}:{a}"]

    start, end = [x.strip() for x in part.split("-", 1)]
    s1, a1 = _parse_ref(start)
    if ":" in end:
        s2, a2 = _parse_ref(end)
    else:
        s2, a2 = s1, int(end)
    if (s1, a1) > (s2, a2):
        raise ValueError(f"مدى الآيات معكوس: {part!r}")

    refs: list[str] = []
    for s, a, _text in load_quran_index():
        si, ai = int(s), int(a)
        if (s1, a1) <= (si, ai) <= (s2, a2):
            refs.append(f"{si}:{ai}")
    return refs


def parse_verse_targets(args) -> list[tuple[str, str]]:
    """يُعيد قائمة (ref, text) من --verse/--verses/--range/--surah/--quran."""
    quran_rows = None
    refs: list[str] = []

    if args.quran:
        quran_rows = load_quran_index()
        refs.extend(f"{s}:{a}" for s, a, _ in quran_rows)

    if args.surah:
        quran_rows = quran_rows or load_quran_index()
        wanted = int(args.surah)
        refs.extend(f"{s}:{a}" for s, a, _ in quran_rows if int(s) == wanted)

    if args.range:
        refs.extend(_expand_ref_range(args.range))

    if args.verses:
        for part in args.verses.split(","):
            refs.extend(_expand_ref_range(part))

    if args.verse:
        refs.extend(_expand_ref_range(args.verse))

    # حافظ على الترتيب مع إزالة التكرار
    seen: set[str] = set()
    clean_refs: list[str] = []
    for ref in refs:
        if ref not in seen:
            seen.add(ref)
            clean_refs.append(ref)

    if args.max_verses is not None:
        clean_refs = clean_refs[: max(0, args.max_verses)]

    targets: list[tuple[str, str]] = []
    cache = {f"{s}:{a}": text for s, a, text in (quran_rows or load_quran_index())}
    for ref in clean_refs:
        text = cache.get(ref) or load_verse(ref)
        if text:
            targets.append((ref, text))
        else:
            print(f"⚠ لَم نَجِد {ref}", file=sys.stderr)
    return targets


class AggregateReport:
    """تقرير تجميعي خفيف لا يغيّر منطق التحليل نفسه."""

    def __init__(self) -> None:
        self.total = 0
        self.ok = 0
        self.failed = 0
        self.failures: list[tuple[str, str]] = []
        self.tokens = 0
        self.word_classes = Counter()
        self.roles = Counter()
        self.relation_names = Counter()
        self.relation_kinds = Counter()
        self.event_kinds = Counter()
        self.event_tenses = Counter()
        self.events_total = 0
        self.meaning_nodes = 0
        self.meaning_edges = 0
        self.meaning_contradictions = 0
        self.consistent = 0
        self.coverage_sum = 0.0
        self.entropy_sum = 0.0
        self.meaning_count = 0

    def add_failure(self, ref: str, error: Exception | str) -> None:
        self.total += 1
        self.failed += 1
        self.failures.append((ref, str(error)))

    def add_success(self, ref: str, sent=None, rg=None, eg=None, meaning_stats=None) -> None:
        self.total += 1
        self.ok += 1
        if sent is not None:
            toks = getattr(sent, "tokens", [])
            self.tokens += len(toks)
            for t in toks:
                self.word_classes[getattr(t, "word_class", "UNKNOWN") or "UNKNOWN"] += 1
                self.roles[getattr(t, "role_phrase", "—") or "—"] += 1
        if rg is not None:
            for r in getattr(rg, "relations", []):
                self.relation_names[getattr(r, "name", "unknown")] += 1
                self.relation_kinds[getattr(r, "kind", "unknown")] += 1
        if eg is not None:
            for e in getattr(eg, "events", []):
                self.events_total += 1
                self.event_kinds[getattr(e, "kind", "unknown")] += 1
                self.event_tenses[getattr(e, "tense", "unknown")] += 1
        if meaning_stats:
            self.meaning_count += 1
            self.meaning_nodes += int(meaning_stats.get("nodes", 0) or 0)
            self.meaning_edges += int(meaning_stats.get("edges", 0) or 0)
            self.meaning_contradictions += int(meaning_stats.get("contradictions", 0) or 0)
            if meaning_stats.get("is_consistent"):
                self.consistent += 1
            self.coverage_sum += float(meaning_stats.get("coverage_pct", 0) or 0)
            self.entropy_sum += float(meaning_stats.get("entropy", 0) or 0)

    def print(self) -> None:
        print(f"\n{'='*70}")
        print("📊 التَّقرير المُجَمَّع")
        print(f"{'='*70}")
        print(f"  الآيات المطلوبة      : {self.total}")
        print(f"  نجح التحليل          : {self.ok}")
        print(f"  فشل التحليل          : {self.failed}")
        print(f"  مجموع الكلمات/العناصر: {self.tokens}")

        def show_counter(title: str, counter: Counter, limit: int = 12):
            print(f"\n  {title}:")
            if not counter:
                print("    —")
                return
            for k, v in counter.most_common(limit):
                print(f"    {k:24s}: {v}")

        show_counter("WordClass", self.word_classes)
        show_counter("Relations by name", self.relation_names)
        show_counter("Relations by proof kind", self.relation_kinds)
        show_counter("Events by proof kind", self.event_kinds)
        show_counter("Events by tense", self.event_tenses)

        if self.meaning_count:
            avg_cov = self.coverage_sum / self.meaning_count
            avg_ent = self.entropy_sum / self.meaning_count
            print("\n  MeaningGraph:")
            print(f"    graphs analyzed        : {self.meaning_count}")
            print(f"    total nodes            : {self.meaning_nodes}")
            print(f"    total edges            : {self.meaning_edges}")
            print(f"    avg coverage           : {avg_cov:.2f}%")
            print(f"    avg entropy            : {avg_ent:.2f}")
            print(f"    contradictions         : {self.meaning_contradictions}")
            print(f"    consistent graphs      : {self.consistent}/{self.meaning_count}")

        if self.failures:
            print("\n  الإخفاقات:")
            for ref, err in self.failures[:20]:
                print(f"    {ref}: {err}")
        print(f"{'='*70}\n")


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


def _show_all_enabled(args) -> bool:
    return args.all or not any([
        args.morph, args.i3rab, args.samarrai, args.relations,
        args.events, args.resolution, args.meaning, args.reasoning,
    ])


def _analyze_core(text: str, verse_ref: str | None, args, render: bool = True):
    """يُشغّل التحليل لآية واحدة، ويُعيد الكائنات اللازمة للتقرير المجمع."""
    show_all = _show_all_enabled(args)
    sent = None
    rg = None
    eg = None
    meaning_stats = None

    if args.morph or show_all:
        if render:
            show_morph(text)

    needs_i3rab = (
        args.i3rab or args.relations or args.events or args.resolution
        or args.meaning or show_all or args.summary
    )
    if needs_i3rab:
        from i3rab_engine.engine import I3rabEngine
        sent = I3rabEngine().analyze_sentence(text)

    if (args.i3rab or show_all) and render:
        show_i3rab(text, sent)

    if (args.samarrai or show_all) and render:
        show_samarrai(text)

    needs_relations = args.relations or args.events or args.meaning or show_all or args.summary
    if needs_relations:
        from relation_extractor import RelationExtractor
        rg = RelationExtractor().extract(sent)

    if (args.relations or show_all) and render:
        show_relations(sent, rg)

    needs_events = args.events or args.meaning or show_all or args.summary
    if needs_events:
        try:
            from event_extractor import EventExtractor
            eg = EventExtractor().extract(sent, rg)
        except Exception:
            eg = None

    if (args.events or show_all) and render:
        show_events(text, sent, rg)

    if (args.resolution or show_all) and render:
        prior_ctx = _build_prior_context_for_verse(verse_ref)
        show_resolution(sent, eg, prior_context=prior_ctx)

    if args.meaning or show_all or args.summary:
        try:
            from meaning_assembler import MeaningAssembler
            graph = MeaningAssembler().assemble(text)
            meaning_stats = graph.stats()
            if render and (args.meaning or show_all):
                print(_heading("L7 — شَبَكَة المَعنى (MeaningGraph)", "🧠"))
                s = meaning_stats
                print(f"  العُقَد: {s['nodes']} ({s['certificate_nodes']}C + {s['hypothesis_nodes']}H)")
                print(f"  الرَّوابِط: {s['edges']} ({s['certificate_edges']}C + {s['hypothesis_edges']}H)")
                print(f"  التَّغطيَة: {s['coverage_pct']}%")
                print(f"  Entropy (الغُموض): {s['entropy']}")
                contradictions_count = s['contradictions']
                cons_text = 'نَعَم ✓' if s['is_consistent'] else f'لا — {contradictions_count} تَناقُض'
                print(f"  مُتَّسِق: {cons_text}")
                if getattr(graph, "contradictions", None):
                    print(f"\n  التَّناقُضات:")
                    for c in graph.contradictions:
                        print(f"    ✗ [{c.severity}] {c.description}")
        except Exception as e:
            if render and (args.meaning or show_all):
                print(_heading("L7 — شَبَكَة المَعنى (MeaningGraph)", "🧠"))
                print(f"  ⚠ تَخَطّي: {e}")

    if (args.reasoning or show_all) and render:
        show_reasoning_interactive(text)

    return sent, rg, eg, meaning_stats


def _print_verse_header(title: str, text: str) -> None:
    print(f"\n{'='*70}")
    print(title)
    print(f"{'='*70}")
    print(f"\n{text}\n")


def _run_single_text(args) -> None:
    if args.verse:
        text = load_verse(args.verse)
        if not text:
            print(f"⚠ لَم نَجِد {args.verse}")
            sys.exit(1)
        title = f"📖 الآيَة {args.verse}"
        verse_ref = args.verse
    elif args.text:
        text = args.text
        title = "📝 نَصّ مُباشَر"
        verse_ref = None
    else:
        raise ValueError("لا يوجد نص أو آية للتحليل")

    _print_verse_header(title, text)
    if args.quiet:
        return
    _analyze_core(text, verse_ref, args, render=True)
    print(f"\n{'='*70}")
    print(f"✅ التَّحليل الكامِل مُكتَمِل")
    print(f"{'='*70}\n")


def _run_batch(args, targets: list[tuple[str, str]]) -> None:
    if not targets:
        print("⚠ لا توجد آيات مطابقة للمدخلات")
        sys.exit(1)

    report = AggregateReport()
    render_each = not args.summary_only

    for ref, text in targets:
        try:
            if render_each:
                _print_verse_header(f"📖 الآيَة {ref}", text)
                if not args.quiet:
                    sent, rg, eg, meaning_stats = _analyze_core(text, ref, args, render=True)
                else:
                    sent = rg = eg = meaning_stats = None
                print(f"\n{'='*70}")
                print(f"✅ تَحليل {ref} مُكتَمِل")
                print(f"{'='*70}\n")
            else:
                sent, rg, eg, meaning_stats = _analyze_core(text, ref, args, render=False)
            report.add_success(ref, sent, rg, eg, meaning_stats)
        except Exception as e:
            report.add_failure(ref, e)
            print(f"⚠ فَشَل تحليل {ref}: {e}", file=sys.stderr)
            if args.stop_on_error:
                raise

    if args.summary:
        report.print()


def main():
    p = argparse.ArgumentParser(
        description="مُحَلِّل آيَة شامِل بِكُلّ الـ7 phases — يدعم آية/دفعة/سورة/القرآن كاملًا",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أَمثِلَة مفردة:
  python3 analyze_verse_v3.py --verse 1:5 --all
  python3 analyze_verse_v3.py --verse 2:255 --i3rab --relations
  python3 analyze_verse_v3.py "إِيَّاكَ نَعْبُدُ" --meaning --reasoning

أَمثِلَة دفعات:
  python3 analyze_verse_v3.py --verses 2:255,2:256,3:100 --all > out.txt
  python3 analyze_verse_v3.py --range 2:255-2:257 --all > out.txt
  python3 analyze_verse_v3.py --surah 1 --all > out-surah1.txt
  python3 analyze_verse_v3.py --quran --summary-only --summary > quran-report.txt
""",
    )
    p.add_argument("text", nargs="?", help="النَّصّ مُباشَرَةً")
    p.add_argument("--verse", help="آيَة واحدة (سُورة:آية) — السلوك القديم كما هو")
    p.add_argument("--verses", help="قائمة آيات/مديات: 2:255,2:256,3:100 أو 2:255-2:257")
    p.add_argument("--range", help="مدى آيات: 2:255-2:257 أو 2:255-257")
    p.add_argument("--surah", type=int, help="تحليل سورة كاملة برقمها")
    p.add_argument("--quran", action="store_true", help="تحليل القرآن كاملًا")
    p.add_argument("--max-verses", type=int, help="حد أقصى لعدد الآيات في الدفعة، مفيد للتجربة")

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
    p.add_argument("--summary", action="store_true", default=True, help="طباعة تقرير مجمع في نهاية الدفعات (افتراضيًا مُفعّل للدفعات)")
    p.add_argument("--no-summary", dest="summary", action="store_false", help="إلغاء التقرير المجمع")
    p.add_argument("--summary-only", action="store_true", help="لا تطبع تفاصيل كل آية؛ اطبع التقرير المجمع فقط")
    p.add_argument("--stop-on-error", action="store_true", help="توقف عند أول خطأ بدل متابعة الدفعة")

    args = p.parse_args()

    has_batch_selector = bool(args.verses or args.range or args.surah or args.quran)
    if has_batch_selector:
        if args.text:
            print("⚠ لا يمكن الجمع بين نص مباشر وخيارات الدفعات", file=sys.stderr)
            sys.exit(1)
        targets = parse_verse_targets(args)
        _run_batch(args, targets)
        return

    if args.summary_only:
        print("⚠ --summary-only يعمل فقط مع --verses أو --range أو --surah أو --quran", file=sys.stderr)
        sys.exit(1)

    if not args.verse and not args.text:
        p.print_help()
        sys.exit(1)
    _run_single_text(args)


if __name__ == "__main__":
    main()
