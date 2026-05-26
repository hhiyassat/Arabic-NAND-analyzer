#!/usr/bin/env python3
"""regression_scan.py — قياس انحِدار مُختَصَر بِالتَّنسيق الجَدوَليّ.

يَفحَص آية وَ يُصدِر تَقريرًا مَوحَدًا يُتيح المُقارَنَة قَبل/بَعد:

  WordClass distribution
  Implicit Subjects breakdown (created/certified/hypothesis)
  Events breakdown (total/certificate/hypothesis/with-agent/with-patient)
  Relations breakdown (total/by kind/by type)
  MeaningGraph (nodes/edges/coverage/entropy/contradictions)
  Top suspicious claims

CLI:
  python3 regression_scan.py --verse 2:282
  python3 regression_scan.py "نَصّ مُشَكَّل"
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
QURAN_PATH = _HERE.parent / "data" / "quran-uthmani-with-pause-mark.txt"


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


def is_verb_target(graph_or_tokens, target_id: str) -> bool:
    """Check if target token is classified as FIIL."""
    if not target_id.startswith("t"):
        return False
    try:
        idx = int(target_id[1:])
        if 0 <= idx < len(graph_or_tokens):
            return graph_or_tokens[idx].word_class == "FIIL"
    except (ValueError, IndexError):
        pass
    return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("text", nargs="?", help="نَصّ مُباشَر")
    p.add_argument("--verse", help="آية مَن القُرآن")
    args = p.parse_args()

    if args.verse:
        text = load_verse(args.verse)
        if text is None:
            print(f"⚠ لَم نَجِد {args.verse}")
            sys.exit(1)
        ref = args.verse
    elif args.text:
        text = args.text
        ref = "<custom>"
    else:
        p.print_help()
        sys.exit(1)

    print()
    print(f"=== Regression Scan: {ref} ===")
    print()

    # Run all layers
    from i3rab_engine.engine import I3rabEngine
    from relation_extractor import RelationExtractor
    from event_extractor import EventExtractor
    from resolution_engine import ResolutionEngine
    from meaning_assembler import MeaningAssembler

    sent = I3rabEngine().analyze_sentence(text)
    rg = RelationExtractor().extract(sent)
    eg = EventExtractor().extract(sent, rg)
    res = ResolutionEngine().resolve(sent, eg)
    graph = MeaningAssembler().assemble(text)

    # ── WordClass distribution ──
    print("WordClass:")
    wc_counter = Counter()
    for t in sent.tokens:
        wc_counter[t.word_class] += 1
    for k in ("FIIL", "ISM_MUARAB", "ISM_MABNI", "ISM_MAWSOOL", "ISM_ISHARA",
              "JAMID", "AALAM", "SINGULAR_TERM", "HARF", "UNKNOWN"):
        n = wc_counter.get(k, 0)
        if n > 0 or k in ("FIIL", "ISM_MUARAB", "HARF", "UNKNOWN"):
            print(f"  {k:18s}: {n}")
    print(f"  {'TOTAL':18s}: {sum(wc_counter.values())}")
    print()

    # ── Implicit Subjects ──
    implicit_nodes = [n for n in rg.nodes.values()
                       if str(n.entity_id).startswith("implicit_")]
    implicit_certified = sum(1 for r in rg.relations
                             if r.source_id.startswith("implicit_")
                             and r.kind == "Certificate")
    implicit_hypothesis = sum(1 for r in rg.relations
                              if r.source_id.startswith("implicit_")
                              and r.kind == "Hypothesis")
    # how many ambiguous تَ verbs got NO implicit subject (suppressed)
    suppressed = 0
    for i, t in enumerate(sent.tokens):
        if t.word_class != "FIIL":
            continue
        surface = (t.token or "").strip()
        # check if it has agent_of (explicit or implicit)
        has_agent = any(r.target_id == f"t{i}" and r.name == "agent_of"
                        for r in rg.relations)
        # ambiguous تَ pattern
        if surface.startswith("تَ") and not has_agent:
            suppressed += 1

    print("Implicit Subjects:")
    print(f"  {'created':18s}: {len(implicit_nodes)}")
    print(f"  {'certified':18s}: {implicit_certified}")
    print(f"  {'hypothesis':18s}: {implicit_hypothesis}")
    print(f"  {'suppressed (تَ amb.)':18s}: {suppressed}")
    print()

    # ── Events ──
    n_events = len(eg.events)
    n_event_cert = sum(1 for e in eg.events if e.kind == "Certificate")
    n_event_hyp = sum(1 for e in eg.events if e.kind == "Hypothesis")
    n_event_zero = sum(1 for e in eg.events if e.kind == "Zero")
    n_event_agent = sum(1 for e in eg.events if e.agent)
    n_event_patient = sum(1 for e in eg.events if e.patient)

    print("Events:")
    print(f"  {'total':18s}: {n_events}")
    print(f"  {'certificate':18s}: {n_event_cert}")
    print(f"  {'hypothesis':18s}: {n_event_hyp}")
    print(f"  {'zero':18s}: {n_event_zero}")
    print(f"  {'with agent':18s}: {n_event_agent}")
    print(f"  {'with patient':18s}: {n_event_patient}")
    print(f"  {'no agent':18s}: {n_events - n_event_agent}")
    print(f"  {'no patient':18s}: {n_events - n_event_patient}")
    print()

    # ── AgentAgreementContract audit ──
    try:
        from agent_agreement_contract import get_audit
        audit = get_audit()
        print("AgentAgreementContract:")
        print(f"  {'candidates_seen':18s}: {audit['candidates_seen']}")
        print(f"  {'passed':18s}: {audit['passed']}")
        print(f"  {'certificate':18s}: {audit['certificate']}")
        print(f"  {'hypothesis':18s}: {audit['hypothesis']}")
        print(f"  {'zero (rejected)':18s}: {audit['zero']}")
        print(f"  {'suppressed':18s}: {audit['suppressed']}")
        print(f"  {'blockers_count':18s}: {audit['blockers_count']}")
        if audit.get("zero_reasons"):
            print(f"  top zero reasons:")
            for reason, count in sorted(
                audit["zero_reasons"].items(), key=lambda x: -x[1]
            )[:3]:
                print(f"    - {reason}: {count}")
        print()
    except ImportError:
        pass

    # ── PatientAgreementContract audit ──
    try:
        from patient_agreement_contract import get_audit as get_p_audit
        p_audit = get_p_audit()
        print("PatientAgreementContract:")
        print(f"  {'candidates_seen':18s}: {p_audit['candidates_seen']}")
        print(f"  {'passed':18s}: {p_audit['passed']}")
        print(f"  {'certificate':18s}: {p_audit['certificate']}")
        print(f"  {'hypothesis':18s}: {p_audit['hypothesis']}")
        print(f"  {'zero (rejected)':18s}: {p_audit['zero']}")
        print(f"  {'suppressed':18s}: {p_audit['suppressed']}")
        print(f"  {'blockers_count':18s}: {p_audit['blockers_count']}")
        if p_audit.get("zero_reasons"):
            print(f"  top zero reasons:")
            for reason, count in sorted(
                p_audit["zero_reasons"].items(), key=lambda x: -x[1]
            )[:3]:
                print(f"    - {reason}: {count}")
        print()
    except ImportError:
        pass

    # ── Relations ──
    rel_total = len(rg.relations)
    rel_cert = sum(1 for r in rg.relations if r.kind == "Certificate")
    rel_hyp = sum(1 for r in rg.relations if r.kind == "Hypothesis")
    rel_zero = sum(1 for r in rg.relations if r.kind == "Zero")
    rel_by_name = Counter(r.name for r in rg.relations)

    print("Relations:")
    print(f"  {'total':18s}: {rel_total}")
    print(f"  {'certificate':18s}: {rel_cert}")
    print(f"  {'hypothesis':18s}: {rel_hyp}")
    print(f"  {'zero':18s}: {rel_zero}")
    for name in ("agent_of", "patient_of", "patient2_of", "attribute_of",
                 "possessor_of", "harf_jarr_of", "verb_in_clause",
                 "in_location", "on_surface", "vocative_of"):
        if name in rel_by_name:
            print(f"  {name:18s}: {rel_by_name[name]}")
    print()

    # ── MeaningGraph ──
    s = graph.stats()
    print("MeaningGraph:")
    print(f"  {'nodes':18s}: {s['nodes']} ({s['certificate_nodes']}C + {s['hypothesis_nodes']}H)")
    print(f"  {'edges':18s}: {s['edges']} ({s['certificate_edges']}C + {s['hypothesis_edges']}H)")
    print(f"  {'coverage':18s}: {s['coverage_pct']}%")
    print(f"  {'entropy':18s}: {s['entropy']}")
    print(f"  {'contradictions':18s}: {s.get('contradictions', 0)}")
    print(f"  {'consistent':18s}: {'YES' if s.get('is_consistent') else 'NO'}")
    print()

    # ── Top remaining suspicious claims ──
    print("Top remaining suspicious claims:")
    suspicious = []

    # 1. Implicit agent on non-FIIL target (should be 0 after fix)
    for r in rg.relations:
        if r.name == "agent_of" and r.source_id.startswith("implicit_"):
            if not is_verb_target(sent.tokens, r.target_id):
                src_node = rg.nodes.get(r.source_id)
                tgt_tok = sent.tokens[int(r.target_id[1:])].token if r.target_id.startswith("t") else "?"
                suspicious.append(
                    f"IMPLICIT_ON_NON_VERB: {src_node.surface if src_node else '?'} → {tgt_tok}"
                )

    # 2. agent_of where source word ends with tanwin (improbable)
    for r in rg.relations:
        if r.name != "agent_of":
            continue
        if not r.source_id.startswith("t"):
            continue
        try:
            src_tok = sent.tokens[int(r.source_id[1:])].token
        except (ValueError, IndexError):
            continue
        if any(c in src_tok for c in ("ٌ", "ٍ", "ً")):
            tgt_tok = sent.tokens[int(r.target_id[1:])].token if r.target_id.startswith("t") else "?"
            # tanwin doesn't make agent impossible (مرفوع ٌ) — but mark suspicious
            # only if tanwin is fatḥa (ً, manṣub — wouldn't be agent)
            if "ً" in src_tok:
                suspicious.append(
                    f"NASB_AS_AGENT: {src_tok} → {tgt_tok}"
                )

    # 3. Event with agent or patient pointing to a non-noun
    for e in eg.events:
        if e.agent and any(c in e.agent for c in ("بِ", "لِ", "كِ")):
            suspicious.append(f"PREP_AS_AGENT in Event[{e.type}]: agent={e.agent}")

    # 4. Relations where target is not a FIIL but relation is agent/patient
    for r in rg.relations:
        if r.name in ("agent_of", "patient_of", "patient2_of"):
            if not is_verb_target(sent.tokens, r.target_id):
                if r.target_id.startswith("t"):
                    try:
                        tgt_tok = sent.tokens[int(r.target_id[1:])].token
                        src_tok = sent.tokens[int(r.source_id[1:])].token if r.source_id.startswith("t") else "implicit"
                        suspicious.append(
                            f"{r.name.upper()}_TO_NON_VERB: {src_tok} → {tgt_tok}"
                        )
                    except (ValueError, IndexError):
                        pass

    # dedupe
    seen, dedupe = set(), []
    for s_item in suspicious:
        if s_item not in seen:
            seen.add(s_item)
            dedupe.append(s_item)

    if not dedupe:
        print("  ✓ no top-tier suspicious claims detected")
    else:
        for i, s_item in enumerate(dedupe[:15], 1):
            print(f"  {i}. {s_item}")
        if len(dedupe) > 15:
            print(f"  ... (+{len(dedupe) - 15} more)")
    print()


if __name__ == "__main__":
    main()
