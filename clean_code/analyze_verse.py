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
from speech_frame_extractor import SpeechFrameExtractor
from gender_detector import GenderDetector
from number_detector import NumberDetector
from number_counted_resolver import NumberCountedResolver
from agreement_checker import AgreementChecker
import maani_kb_loader


CONTRACT_NAME = "VerseAnalyzer:v7"  # +Maani KB (Semantic Grammar Authority)

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

def analyze_verse(verse: str, source: str = "inline_text", full: bool = False) -> dict:
    """يَجمَع كُلّ التَّحلِيلات في dict واحد.

    full=True يَضيف:
      • i3rab كامِل (word_class + case + mark + role)
      • Segmentation (prefixes/stem/suffixes)
      • ProofObject details (alternatives + blockers + source chains)
    """
    root_pipe = RootPipeline()
    m1_pipe = M1Pipeline()
    text_graph_asm = TextGraphAssembler()
    i3rab_engine = None
    segmenter_fn = None
    if full:
        try:
            from i3rab_engine.engine import I3rabEngine
            i3rab_engine = I3rabEngine()
        except Exception:
            i3rab_engine = None
        try:
            from segmenter import segment as _seg
            segmenter_fn = _seg
        except Exception:
            segmenter_fn = None

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

    # ⑥ M3 — Speech Frames (تَتَبُّع القائِل/المُخاطَب)
    speech_extractor = SpeechFrameExtractor()
    speech_result = speech_extractor.extract(_strip_pause_marks(verse))

    # ⑧ M3.N — العَدَد والمَعدود
    nc_resolver = NumberCountedResolver()
    nc_phrases = nc_resolver.detect_in_tokens(
        [w["word"] for w in word_analyses]
    )

    # ⑦ M3.G — Gender/Number لِكُلّ كَلِمَة
    gender_det = GenderDetector()
    number_det = NumberDetector()
    gn_table = []
    for w in word_analyses:
        token = w["word"]
        wazn = w.get("wazn", "")
        gr = gender_det.detect(token, wazn=wazn)
        nr = number_det.detect(token, wazn=wazn)
        decomp = gender_det.decompose_demonstrative(token)
        gn_table.append({
            "word": token,
            "gender": gr.gender,
            "gender_source": gr.source,
            "gender_conf": gr.confidence,
            "number": nr.number,
            "number_source": nr.source,
            "decomposition": decomp.to_dict() if decomp else None,
            "warnings": list(gr.warnings) + list(nr.warnings),
        })

    result = {
        "contract": CONTRACT_NAME,
        "source": source,
        "input": verse,
        "tokens": {
            "n_words": len(word_analyses),
            "words": word_analyses,
        },
        "m1": m1.to_dict(),
        "phase_c": text_graph.to_dict(),
        "m3_speech": {
            "contract": speech_result["contract"],
            "n_frames": len(speech_result["frames"]),
            "frames": [f.to_dict() for f in speech_result["frames"]],
            "entities": speech_result["tracker"].to_dict(),
        },
        "m3_gender_number": {
            "contract": "GenderNumberLayer:v1",
            "tokens": gn_table,
        },
        "m3_number_counted": {
            "contract": "NumberCountedResolver:v1",
            "n_phrases": len(nc_phrases),
            "phrases": [p.to_dict() for p in nc_phrases],
        },
    }

    # ─── ⑨ Maani KB layer — lookup constructions ──
    try:
        maani_hits = []
        seen_cids = set()

        # ① مُطابَقَة بِالفِعل/الجَذر (مَع نَزع بَوادِئ + جَذر)
        for w in word_analyses:
            token = w.get("word", "")
            root = w.get("root", "")
            stripped_token = "".join(c for c in token if c not in "ًٌٍَُِّْـٰٓ")
            stripped_token = stripped_token.replace("ٱ", "ا")

            # نُمَرِّر اللَّمَة + الجَذر معًا — الـ loader يَتَدَبَّر البَوادِئ + الجَذر
            c = maani_kb_loader.lookup_construction_for_verb(stripped_token, root=root)
            if c and c["construction_id"] not in seen_cids:
                seen_cids.add(c["construction_id"])
                match_info = c.get("_match_info", {})
                matched_lemma = match_info.get("matched_lemma", stripped_token)
                ext_type = match_info.get("extension_type", "verb_lemma")
                mod = maani_kb_loader.get_modality_for_verb(matched_lemma)
                src_refs = c.get("source_refs") or [{}]
                maani_hits.append({
                    "token": token,
                    "matched_lemma": matched_lemma,
                    "match_type": ext_type,
                    "extension_info": match_info,
                    "construction_id": c["construction_id"],
                    "construction_title": c.get("title", ""),
                    "modality": mod,
                    "warnings": c.get("warnings", []),
                    "source_ref": src_refs[0] if src_refs else {},
                })

        # ② مُطابَقَة بِبادِئَة الكَلِمَة (إِيَّاكَ، إِيَّاهُم، إِيَّانا، …)
        for w in word_analyses:
            token = w.get("word", "")
            c = maani_kb_loader.lookup_construction_for_word(token)
            if c and c["construction_id"] not in seen_cids:
                seen_cids.add(c["construction_id"])
                match_info = c.get("_match_info", {})
                src_refs = c.get("source_refs") or [{}]
                maani_hits.append({
                    "token": token,
                    "matched_lemma": match_info.get("matched_prefix", ""),
                    "match_type": "pronoun_suffix",
                    "extension_info": match_info,
                    "construction_id": c["construction_id"],
                    "construction_title": c.get("title", ""),
                    "modality": None,
                    "warnings": c.get("warnings", []),
                    "source_ref": src_refs[0] if src_refs else {},
                })

        # ③ مُطابَقَة بِنَمَط التَّرتيب (تَقديم لِلِاختِصاص، إلخ)
        order_matches = maani_kb_loader.lookup_order_pattern_constructions(word_analyses)
        for om in order_matches:
            c = om["construction"]
            if c["construction_id"] in seen_cids:
                continue
            seen_cids.add(c["construction_id"])
            src_refs = c.get("source_refs") or [{}]
            maani_hits.append({
                "token": om["matched_token"],
                "matched_lemma": om["matched_marker"],
                "match_type": "order_pattern",
                "construction_id": c["construction_id"],
                "construction_title": c.get("title", ""),
                "modality": (c.get("semantic_output") or {}).get("modality"),
                "warnings": c.get("warnings", []),
                "source_ref": src_refs[0] if src_refs else {},
            })

        result["maani_kb"] = {
            "contract": "MaaniKBLoader:v1",
            "hits": maani_hits,
        }
    except Exception as _e:
        result["maani_kb"] = {"contract": "MaaniKBLoader:v1", "hits": [], "error": str(_e)}

    # ④⑤⑥ Full mode: i3rab كامِل + segmentation + ProofObject details
    if full:
        clean_verse = _strip_pause_marks(verse)
        full_tokens = []
        # i3rab تَحليل
        if i3rab_engine is not None:
            try:
                sent = i3rab_engine.analyze_sentence(clean_verse)
                for t in sent.tokens:
                    seg_info = None
                    if segmenter_fn is not None:
                        try:
                            seg = segmenter_fn(t.token, normalize_input=True)
                            seg_info = {
                                "prefixes": list(seg.prefixes),
                                "stem": seg.stem,
                                "suffixes": list(seg.suffixes),
                            }
                        except Exception:
                            seg_info = None
                    full_tokens.append({
                        "position": t.position,
                        "token": t.token,
                        "word_class": t.word_class,
                        "word_class_source": t.word_class_source,
                        "wordclass_kind": t.wordclass_kind,
                        "verb_aspect": t.verb_aspect,
                        "root": t.root,
                        "wazn": t.wazn,
                        "closed_class_kind": t.closed_class_kind,
                        "operator_i3rab": t.operator_i3rab,
                        "case_id": t.case_id,
                        "case_source": t.case_source,
                        "case_kind": t.case_kind,
                        "mark_id": t.mark_id,
                        "mark_source": t.mark_source,
                        "tanwin": t.tanwin,
                        "role_id": t.role_id,
                        "role_phrase": t.role_phrase,
                        "role_source": t.role_source,
                        "role_kind": t.role_kind,
                        "alternatives": {
                            "wordclass": list(t.wordclass_alternatives),
                            "case": list(t.case_alternatives),
                            "role": list(t.role_alternatives),
                        },
                        "blockers": {
                            "wordclass": list(t.wordclass_blockers),
                            "case": list(t.case_blockers),
                            "role": list(t.role_blockers),
                        },
                        "segmentation": seg_info,
                    })
                result["i3rab"] = {
                    "n_tokens": len(full_tokens),
                    "tokens": full_tokens,
                }
            except Exception as e:
                result["i3rab_error"] = str(e)

        # ⑦ ProofObject details لِكُلّ كَلِمَة في tokens
        proof_details = []
        for w in word_analyses:
            proof_details.append({
                "word": w["word"],
                "kind": w["kind"],
                "contract": w["contract"],
                "source_of_claim": w["source_of_claim"],
                "blockers": w.get("blockers", []),
            })
        result["proof_details"] = proof_details

    return result


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


def format_arabic(result: dict, show_maani: bool = False) -> str:
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

    # ─── ④ i3rab كامِل (full mode) ───
    i3rab = result.get("i3rab")
    if i3rab:
        out.append("")
        out.append(_line())
        out.append(f"  ④ تَحليل الإِعراب الكامِل (i3rab) — {i3rab.get('n_tokens', 0)} رمز")
        out.append(_line())
        out.append(
            f"  {'#':>2}  {'الكَلِمَة':<18} {'النَّوع':<14} "
            f"{'الحالة':<10} {'العَلامة':<10} {'الدَّور':<22}"
        )
        out.append(_line("·"))
        case_names = {1: "مَرفوع", 2: "مَنصوب", 3: "مَجرور", 4: "مَجزوم", 5: "مَبني"}
        for t in i3rab.get("tokens", []):
            wc = t.get("word_class", "?")
            case = case_names.get(t.get("case_id"), "—") if t.get("case_id") else "—"
            mark = "—"
            mark_id = t.get("mark_id")
            if mark_id:
                from analyze_verse import _MARK_AR_LOOKUP  # fallback to local
                mark = _MARK_AR_LOOKUP.get(mark_id, "—")
            role = t.get("role_phrase", "") or "—"
            out.append(
                f"  {t.get('position', 0)+1:>2}  {t.get('token',''):<18} "
                f"{wc:<14} {case:<10} {mark:<10} {role:<22}"
            )
        # Segmentation sub-section
        out.append("")
        out.append(f"  ▸ التَّقطيع الصَّرفيّ (segmentation)")
        out.append(_line("·"))
        for t in i3rab.get("tokens", []):
            seg = t.get("segmentation")
            if not seg:
                continue
            pre = "+".join(seg.get("prefixes", [])) or "—"
            stem = seg.get("stem", "—")
            suf = "+".join(seg.get("suffixes", [])) or "—"
            out.append(f"     {t.get('token',''):<18}  {pre:<10} | {stem:<14} | {suf}")
        # Alternatives + Blockers (only those with content)
        alts_or_blockers = [
            t for t in i3rab.get("tokens", [])
            if any(t.get("alternatives", {}).values()) or any(t.get("blockers", {}).values())
        ]
        if alts_or_blockers:
            out.append("")
            out.append(f"  ▸ بَدائل + عوائِق ProofObject")
            out.append(_line("·"))
            for t in alts_or_blockers:
                alts = t.get("alternatives", {})
                blks = t.get("blockers", {})
                line_alts = []
                for k, v in alts.items():
                    if v:
                        line_alts.append(f"{k}={v}")
                line_blks = []
                for k, v in blks.items():
                    if v:
                        line_blks.append(f"{k}={v}")
                if line_alts or line_blks:
                    detail = " · ".join(line_alts + line_blks)
                    out.append(f"     {t.get('token',''):<18}  {detail}")

    # ─── ⑤ ProofObject details (full mode) ───
    proofs = result.get("proof_details")
    if proofs:
        out.append("")
        out.append(_line())
        out.append(f"  ⑤ تَفاصيل ProofObject لِكُلّ كَلِمَة")
        out.append(_line())
        for p in proofs:
            out.append(
                f"     {p['word']:<18}  kind={p['kind']:<11} "
                f"contract={p['contract']}"
            )
            out.append(f"        src: {p['source_of_claim']}")
            if p.get("blockers"):
                out.append(f"        عوائِق: {p['blockers']}")

    # ─── ⑥ M3 — Speech Frames (تَتَبُّع القائِل/المُخاطَب) ───
    m3 = result.get("m3_speech", {})
    if m3 and m3.get("frames"):
        out.append("")
        out.append(_line())
        out.append(f"  ⑥ تَتَبُّع الخِطاب (M3: SpeechFrames) — {m3.get('n_frames', 0)} إِطار")
        out.append(_line())
        for f in m3.get("frames", []):
            sp = f.get("speaker")
            ad = f.get("addressee")
            sp_text = sp.get("text", "—") if sp else "—"
            sp_src = sp.get("source_of_claim", "") if sp else ""
            ad_text = ad.get("text", "—") if ad else "—"
            ad_src = ad.get("source_of_claim", "") if ad else ""
            out.append("")
            out.append(f"  ◆ إِطار {f.get('frame_id','?')} [{f.get('speech_type', '?')}]  ثِقَة={f.get('confidence', '?')}")
            out.append(f"     • القائِل:   «{sp_text}»  ({sp_src})")
            out.append(f"     • المُخاطَب: «{ad_text}»  ({ad_src})")
            if f.get("introduced_by"):
                out.append(f"     • فَتَحَه:    «{f['introduced_by']}»")
            if f.get("utterance"):
                out.append(f"     • المَقول:  «{f['utterance']}»")
            ev = f.get("evidence", [])
            if ev:
                ev_str = " · ".join(f"«{e['token']}»→{e['role']}" for e in ev)
                out.append(f"     • الأَدِلَّة:  {ev_str}")
            if f.get("parent_frame_id"):
                out.append(f"     • الأَب:    {f['parent_frame_id']}")
        # الكِيانات المَوسومَة
        ents = m3.get("entities", {}).get("entities", {})
        if ents:
            out.append("")
            out.append(f"  ▸ الكِيانات المَفتوحَة في الخِطاب ({len(ents)})")
            out.append(_line("·"))
            for canon, e in ents.items():
                flags = []
                if e.get("is_speaker_candidate"):
                    flags.append("قائِل")
                if e.get("is_addressee_candidate"):
                    flags.append("مُخاطَب")
                fl = f" [{'/'.join(flags)}]" if flags else ""
                out.append(f"     • {e.get('surface', canon):<14}  (×{e.get('mentions', 1)}){fl}")

    # ─── ⑦ M3.G — الجِنس والعَدَد + تَفكيك أَسماء الإِشارَة ───
    gn = result.get("m3_gender_number", {})
    if gn:
        tokens_gn = gn.get("tokens", [])
        # نَعرِض فَقَط الكَلِمات الَّتي لَها جِنس مَعروف (لَيس default منخفض)
        interesting = [
            t for t in tokens_gn
            if t.get("gender") and (t.get("gender_conf", 0) > 0.4 or t.get("decomposition"))
        ]
        if interesting:
            out.append("")
            out.append(_line())
            out.append(f"  ⑦ طَبَقَة الجِنس والعَدَد (M3.G) — {len(interesting)} كَلِمَة مَكشوفَة")
            out.append(_line())
            out.append(f"  {'الكَلِمَة':<18} {'جِنس':<6} {'عَدَد':<8} {'مَصدَر':<22}  ثِقَة")
            out.append(_line("·"))
            for t in interesting:
                w = t["word"]
                g = t.get("gender", "?")
                n = t.get("number", "?")
                src = t.get("gender_source", "?")
                conf = t.get("gender_conf", 0.0)
                out.append(f"  {w:<18} {g:<6} {n:<8} {src:<22}  {conf:.2f}")

        # تَفكيك أَسماء الإِشارَة المُرَكَّبَة (ذلكم، تلكم، ...)
        decomps = [t for t in tokens_gn if t.get("decomposition")]
        if decomps:
            out.append("")
            out.append(f"  ▸ تَفكيك أَسماء الإِشارَة المُرَكَّبَة ({len(decomps)})")
            out.append(_line("·"))
            for t in decomps:
                d = t["decomposition"]
                ref = d.get("referent_part", {})
                add = d.get("addressee_part") or {}
                out.append(
                    f"     ⤇ «{t['word']}» = "
                    f"المُشار إِليه «{ref.get('form', '')}» ({ref.get('gender', '')}.{ref.get('number', '')}) "
                    f"+ المُخاطَب «{add.get('form', '—')}» "
                    f"({add.get('gender', '')}.{add.get('number', '')})"
                )
                if d.get("warning"):
                    out.append(f"        ⚠ {d['warning']}")

    # ─── ⑧ M3.N — العَدَد والمَعدود ───
    nc = result.get("m3_number_counted", {})
    if nc and nc.get("phrases"):
        out.append("")
        out.append(_line())
        out.append(f"  ⑧ طَبَقَة العَدَد والمَعدود (M3.N) — {nc.get('n_phrases', 0)} تَركيب")
        out.append(_line())
        for p in nc.get("phrases", []):
            out.append("")
            out.append(f"  ⊞ «{p.get('span','')}»  قيمَة={p.get('numeric_value', 0)}  "
                       f"ثِقَة={p.get('confidence', 0)}")
            for s in p.get("structure", []):
                out.append(f"     • {s.get('surface',''):<14} value={s.get('value','?')}  "
                           f"class={s.get('number_class','')}  gender_form={s.get('gender_form','')}")
            counted = p.get("counted")
            if counted:
                out.append(f"     ▶ المَعدود: «{counted.get('surface','')}»  "
                           f"مُفرَدُه={counted.get('singular','')} ({counted.get('singular_gender','')})  "
                           f"شَكلًا={counted.get('surface_number','')}  "
                           f"دَلالَةً={p.get('semantic_entity',{}).get('semantic_number','')}")
                out.append(f"        مَصدَر المُفرَد: {counted.get('source','')}")
            check = p.get("agreement_check", {})
            status_ar = {"valid": "صَحيح ✓", "mismatch": "خَطَأ مُطابَقَة ✗",
                         "no_check": "لَم يُفحَص", "no_gender_relation": "لا عَلاقَة جِنس مُباشَرَة",
                         "hierarchical": "تَرَكُّب هَرَميّ"}.get(check.get("status",""), check.get("status",""))
            out.append(f"     ⚖ المُطابَقَة: {status_ar}")
            for ev in check.get("evidence", []):
                out.append(f"        {ev}")

    # ─── ⑨ Maani KB — Semantic Grammar Authority (مَعاني النَّحو) ───
    # مَخفيَّة افتراضيًّا — تُعرَض فَقَط بِـ --maani
    mk = result.get("maani_kb", {})
    if show_maani and mk and mk.get("hits"):
        out.append("")
        out.append(_line())
        out.append(f"  ⑨ طَبَقَة المَرجِعيَّة النَّحويَّة-الدَّلاليَّة (Maani KB) — {len(mk['hits'])} مُطابَقَة")
        out.append(_line())
        for hit in mk.get("hits", []):
            out.append("")
            out.append(f"  ◇ «{hit.get('token','')}» → {hit.get('construction_id','')}")
            out.append(f"     • النَّوع:     {hit.get('construction_title','')}")
            mod = hit.get("modality")
            if mod:
                out.append(f"     • Modality:   {mod}")
            warn = hit.get("warnings", [])
            for w in warn[:2]:
                out.append(f"     ⚠ {w}")
            src = hit.get("source_ref", {})
            if src:
                out.append(f"     • المَصدَر:    «مَعاني النَّحو» ج{src.get('part','?')} ص{src.get('page_start','?')}")

    out.append("")
    out.append(_line("═"))
    out.append("  انتَهى التَّحلِيل.")
    out.append(_line("═"))
    return "\n".join(out)


# Mark names (from i3rab_engine/types.py)
_MARK_AR_LOOKUP = {
    1: "ضمة", 2: "ألف", 3: "واو", 4: "فتحة", 5: "ياء",
    6: "كسرة", 7: "ياء", 8: "سكون", 9: "حذف نون",
    10: "كسرة", 11: "فتحة ممنوع", 12: "فتحة ممنوع",
    13: "نون", 14: "حذف نون",
}


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
    ap.add_argument(
        "--full",
        action="store_true",
        help="وَضع كامِل: i3rab + segmentation + ProofObject details.",
    )
    ap.add_argument(
        "--maani",
        action="store_true",
        help="إِظهار طَبَقَة «مَعاني النَّحو» (مَخفيَّة افتراضيًّا).",
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

    result = analyze_verse(verse, source=source, full=args.full)

    if args.json:
        # JSON دائِمًا يَحوي كُلّ شَيء (المُسَتَهلِك يُقَرِّر)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_arabic(result, show_maani=args.maani))


if __name__ == "__main__":
    main()
