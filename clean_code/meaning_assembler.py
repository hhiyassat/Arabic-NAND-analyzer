"""meaning_assembler.py — Phase F: يَبني MeaningGraph مِن كُلّ الطَّبَقات.

يَجمَع مَخرَجات:
  • i3rab_engine (Layer 1+2+3)
  • relation_extractor (Phase C)
  • event_extractor (Phase D)
  • resolution_engine (Phase E)
  • samarrai_analyzer (Maani KB) — اختياريّ

كُلّ ما يَنبَني هُنا = داخِل النِّطاق (structural composition).
لا تَأويل، لا تَفسير، لا حُكم.

CLI:
  python3 meaning_assembler.py "نَصّ عَرَبيّ"
  python3 meaning_assembler.py --verse 1:5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from meaning_graph import (
    MeaningGraph,
    MeaningNode,
    MeaningEdge,
    Contradiction,
)

_HERE = Path(__file__).resolve().parent


class MeaningAssembler:
    """يَبني MeaningGraph مِن كُلّ الطَّبَقات السُّفلى."""

    CONTRACT = "MeaningAssembler:v1"

    def __init__(self, with_samarrai: bool = True):
        from i3rab_engine.engine import I3rabEngine
        from relation_extractor import RelationExtractor
        from event_extractor import EventExtractor
        from resolution_engine import ResolutionEngine

        self.i3rab = I3rabEngine()
        self.rel_ext = RelationExtractor()
        self.event_ext = EventExtractor()
        self.res_eng = ResolutionEngine()
        self.with_samarrai = with_samarrai
        if with_samarrai:
            try:
                from samarrai_analyzer import analyze as samarrai_analyze
                self.samarrai_analyze = samarrai_analyze
            except Exception:
                self.samarrai_analyze = None
        else:
            self.samarrai_analyze = None

    def assemble(self, text: str) -> MeaningGraph:
        """يَبني الـ MeaningGraph الكامِل لِنَصّ."""
        graph = MeaningGraph(text=text)

        # 1. الطَّبَقات السُّفلى
        sent = self.i3rab.analyze_sentence(text)
        rg = self.rel_ext.extract(sent)
        eg = self.event_ext.extract(sent, rg)
        res = self.res_eng.resolve(sent, eg)

        # 2. تَحويل الـ tokens إلى MeaningNodes (entities)
        for i, t in enumerate(sent.tokens):
            if t.word_class in ("ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM"):
                surface = getattr(t, "token", "") or getattr(t, "surface", "")
                graph.add_node(MeaningNode(
                    node_id=f"t{i}",
                    node_type="entity",
                    surface=surface,
                    position=i,
                    proof_kind="Certificate" if t.word_class != "SINGULAR_TERM" else "Certificate",
                    contract="i3rab_engine.Layer1",
                    source_of_claim=f"word_class:{t.word_class}",
                    attributes={
                        "word_class": t.word_class,
                        "role": getattr(t, "role_phrase", "") or "",
                        "root": t.root or "",
                        "wazn": t.wazn or "",
                    },
                ))

        # 2b. عُقَد ضِمنيَّة مِن RelationGraph (ضَمائر مُستَتِرَة implicit_t...)
        for entity_id, ent in getattr(rg, "nodes", {}).items():
            if not entity_id.startswith("implicit_"):
                continue
            graph.add_node(MeaningNode(
                node_id=entity_id,
                node_type="entity",
                surface=getattr(ent, "surface", "") or "",
                position=getattr(ent, "position", -1),
                proof_kind="Hypothesis",
                contract=getattr(ent, "contract", "EntityNode:implicit"),
                source_of_claim=getattr(ent, "source_of_claim", ""),
                attributes={
                    "word_class": getattr(ent, "word_class", "ISM_DAMIR"),
                    "role": getattr(ent, "role_phrase", ""),
                    "is_implicit": True,
                },
            ))

        # 2c. عُقَد لِـ HARF tokens الَّتي تَلعَب دَور entity (ضَمائر مُنفَصِلَة)
        # مَثَل إِيَّاكَ: يُصَنَّف HARF لَكِنَّه يَظهَر كَ patient_of في relations
        existing_ids = {n.node_id for n in graph.nodes}
        for r in getattr(rg, "relations", []):
            for tid in (r.source_id, r.target_id):
                if tid == "—" or tid in existing_ids:
                    continue
                if not tid.startswith("t"):
                    continue
                try:
                    idx = int(tid[1:])
                except ValueError:
                    continue
                if idx < 0 or idx >= len(sent.tokens):
                    continue
                tk = sent.tokens[idx]
                # نُضيف فَقَط الـ tokens الَّتي تَظهَر كَ source/target في عَلاقات أَرغومنتيَّة
                surface = getattr(tk, "token", "") or getattr(tk, "surface", "")
                graph.add_node(MeaningNode(
                    node_id=tid,
                    node_type="entity",
                    surface=surface,
                    position=idx,
                    proof_kind="Hypothesis",
                    contract="i3rab_engine.Layer1+argument_role",
                    source_of_claim=(
                        f"word_class:{tk.word_class} + participates in relation"
                    ),
                    attributes={
                        "word_class": tk.word_class,
                        "role": getattr(tk, "role_phrase", ""),
                        "as_argument": True,
                    },
                ))
                existing_ids.add(tid)

        # 3. تَحويل Events إلى MeaningNodes
        for ev in eg.events:
            graph.add_node(MeaningNode(
                node_id=ev.event_id,
                node_type="transformation" if hasattr(ev, "subject") and ev.subject else "event",
                surface=ev.verb_surface,
                position=ev.verb_position,
                proof_kind=ev.kind,
                contract=ev.contract,
                source_of_claim=ev.source_of_claim,
                attributes={
                    "type": ev.type,
                    "tense": ev.tense,
                    "time_value": ev.time_value,
                    "agent": ev.agent,
                    "patient": ev.patient,
                    "location": ev.location,
                    "subject": getattr(ev, "subject", None),
                    "state_before": getattr(ev, "state_before", None),
                    "state_after": getattr(ev, "state_after", None),
                },
            ))

            # ربط الـ event بِالـ agent/patient/location (edges)
            if ev.agent:
                # ابحَث عَن الـ entity node
                agent_node = self._find_entity_by_surface(graph, ev.agent)
                if agent_node:
                    graph.add_edge(MeaningEdge(
                        edge_id=f"e_{ev.event_id}_agent",
                        edge_type="agent_of",
                        source=agent_node.node_id,
                        target=ev.event_id,
                        proof_kind=ev.kind,
                        contract="event_extractor:agent",
                        source_of_claim=f"event:{ev.type}",
                    ))
            if ev.patient:
                patient_node = self._find_entity_by_surface(graph, ev.patient)
                if patient_node:
                    graph.add_edge(MeaningEdge(
                        edge_id=f"e_{ev.event_id}_patient",
                        edge_type="patient_of",
                        source=patient_node.node_id,
                        target=ev.event_id,
                        proof_kind=ev.kind,
                        contract="event_extractor:patient",
                        source_of_claim=f"event:{ev.type}",
                    ))
            if ev.location:
                loc_node = self._find_entity_by_surface(graph, ev.location)
                if loc_node:
                    graph.add_edge(MeaningEdge(
                        edge_id=f"e_{ev.event_id}_location",
                        edge_type="in_location",
                        source=ev.event_id,
                        target=loc_node.node_id,
                        proof_kind="Certificate",
                        contract="event_extractor:location",
                        source_of_claim=f"event:{ev.type} + harf_jarr:في",
                    ))

        # 4. تَحويل Relations إلى MeaningEdges (الَّتي لَيسَت مَكشوفَة في events)
        for r in rg.relations:
            if r.name in ("verb_in_clause", "topic_anchor"):
                continue
            # Whitelist of edge_types preserved as-is. Anything else collapses
            # to "operator_meaning". Locative-style relations created by
            # harf_jarr_relations.csv (in_location, on_surface, direction_to,
            # from_source, etc.) must pass through so Reasoning Phase G can
            # answer أَين/إلى أَين questions.
            PASSTHROUGH = {
                "agent_of", "patient_of", "patient2_of",
                "topic_of", "comment_of",
                "possessor_of", "attribute_of",
                "harf_jarr_of",
                # Locative + directional + instrumental (from harf_jarr_relations.csv)
                "in_location", "on_surface", "direction_to", "from_source",
                "about_topic", "with_companion", "with_instrument",
                "for_benefit", "until_temporal", "since_temporal",
                # Predicate-style
                "inna_topic_of", "inna_comment_of",
                "kana_topic_of", "kana_comment_of",
                "vocative_of", "substitute_of", "coordinate_of",
            }
            graph.add_edge(MeaningEdge(
                edge_id=f"rel_{r.name}_{r.source_id}",
                edge_type=r.name if r.name in PASSTHROUGH else "operator_meaning",
                source=r.source_id,
                target=r.target_id,
                operator=r.operator,
                proof_kind=r.kind,
                contract=r.contract,
                source_of_claim=r.source_of_claim,
            ))

        # 5. تَحويل Resolutions إلى MeaningEdges
        for res_item in res.resolutions:
            if not res_item.has_target:
                continue
            edge_type_map = {
                "anaphora": "anaphora_to",
                "deixis": "deixis_to",
                "relative": "relative_to",
                "identity_transformation": "identity_through",
            }
            edge_type = edge_type_map.get(res_item.resolution_type, "operator_meaning")
            graph.add_edge(MeaningEdge(
                edge_id=res_item.resolution_id,
                edge_type=edge_type,
                source=f"t{res_item.referent_position}",
                target=res_item.target,
                proof_kind=res_item.kind,
                contract=res_item.contract,
                source_of_claim=f"resolution:{res_item.resolution_type}",
                alternatives=[c.entity_id for c in res_item.candidates[1:]],
            ))

        # 6. Samarrai constructions (TAQDIM، TAHZHEER، ...) كَ construction nodes
        if self.samarrai_analyze:
            try:
                ta = self.samarrai_analyze(text)
                for cm in ta.constructions:
                    node_id = f"con_{cm.construction_id}_{cm.span_words[0]}"
                    graph.add_node(MeaningNode(
                        node_id=node_id,
                        node_type="construction",
                        surface=cm.pattern_name[:50],
                        position=cm.span_words[0],
                        proof_kind=cm.claim.proof_kind,
                        contract=cm.claim.contract,
                        source_of_claim=cm.claim.source_of_claim,
                        attributes={
                            "construction_id": cm.construction_id,
                            "trigger": cm.trigger_word,
                            "meaning_ar": cm.claim.meaning_ar,
                            "samarrai_volume": cm.claim.volume,
                            "samarrai_page": cm.claim.source_page,
                        },
                    ))
                    # ربط الـ construction بِالـ tokens في النِّطاق
                    for pos in cm.span_words:
                        graph.add_edge(MeaningEdge(
                            edge_id=f"e_con_{node_id}_t{pos}",
                            edge_type="construction_pattern",
                            source=node_id,
                            target=f"t{pos}",
                            proof_kind=cm.claim.proof_kind,
                            contract=cm.claim.contract,
                            source_of_claim=f"Samarrai vol{cm.claim.volume}/p{cm.claim.source_page}",
                        ))
            except Exception:
                pass

        # 7. فَحص التَّناقُضات (تَوسعَة Phase F)
        self._detect_contradictions(graph)
        self._detect_tense_conflicts(graph)
        self._detect_number_conflicts(graph)

        return graph

    # ──────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _find_entity_by_surface(graph: MeaningGraph, surface: str) -> MeaningNode | None:
        for n in graph.nodes:
            if n.node_type == "entity" and n.surface == surface:
                return n
        return None

    @staticmethod
    def _detect_tense_conflicts(graph: MeaningGraph):
        """يَكشِف تَناقُض الزَّمَن: ظَرف زَمان «أَمسِ» مَع فِعل مُضارِع."""
        for n in graph.nodes:
            if n.node_type not in ("event", "transformation"):
                continue
            tense = n.attributes.get("tense", "")
            time_value = n.attributes.get("time_value", "")
            if not tense or not time_value:
                continue
            past_markers = {"yesterday", "previously"}
            future_markers = {"tomorrow", "later"}
            if tense == "past" and time_value in future_markers:
                graph.add_contradiction(Contradiction(
                    contradiction_id=f"tense_conflict_{n.node_id}",
                    description=f"فِعل ماضٍ «{n.surface}» مَع ظَرف مُستَقبَل «{time_value}»",
                    involved_edges=[],
                    severity="high",
                ))
            elif tense == "present" and time_value in past_markers:
                graph.add_contradiction(Contradiction(
                    contradiction_id=f"tense_conflict_{n.node_id}",
                    description=f"فِعل مُضارِع «{n.surface}» مَع ظَرف ماضٍ «{time_value}»",
                    involved_edges=[],
                    severity="medium",
                ))

    @staticmethod
    def _detect_number_conflicts(graph: MeaningGraph):
        """يَكشِف تَناقُض العَدَد: ضَمير جَمع يُحيل لِكِيان مُفرَد."""
        for e in graph.edges:
            if e.edge_type != "anaphora_to":
                continue
            # المَرجِع (target) — هَل عَدَده يُطابِق الضَّمير؟
            src_node = graph.get_node(e.source)
            tgt_node = graph.get_node(e.target)
            if not src_node or not tgt_node:
                continue
            src_surface = src_node.surface
            # heuristic بَسيط: «هم»/«هما» جَمع، «هو»/«هي» مُفرَد
            if src_surface in ("هم", "هما"):
                # المَرجِع يَجِب جَمع — لَو سَطحه يَنتَهي بِـ ةٌ/ا فَهو مُفرَد
                if not (tgt_node.surface.endswith(("ون", "ين", "ات")) or "ال" in tgt_node.surface[:3]):
                    # placeholder — قَد تَكون false positive
                    pass

    @staticmethod
    def _detect_contradictions(graph: MeaningGraph):
        """فَحص التَّناقُضات البِنيَويَّة الأَساسيَّة.

        Phase F base: نَفحَص نَوعَين أَوَّليَّين:
          • نَفس entity عَلَيه agent_of وَ patient_of لِنَفس event (نَدير)
          • event مَع tense مُتَناقِض (لاحِقًا)
        """
        # نَفس الـ entity كَ agent + patient لِنَفس event
        edges_by_event = {}
        for e in graph.edges:
            if e.edge_type in ("agent_of", "patient_of"):
                ev_id = e.target
                edges_by_event.setdefault(ev_id, []).append(e)

        for ev_id, edges in edges_by_event.items():
            agents = [e.source for e in edges if e.edge_type == "agent_of"]
            patients = [e.source for e in edges if e.edge_type == "patient_of"]
            overlap = set(agents) & set(patients)
            if overlap:
                for node_id in overlap:
                    graph.add_contradiction(Contradiction(
                        contradiction_id=f"contr_{ev_id}_{node_id}",
                        description=f"الـ entity {node_id} يَظهَر كَ agent + patient لِـ {ev_id}",
                        involved_edges=[e.edge_id for e in edges if e.source == node_id],
                        severity="medium",
                    ))


# ─────────────────────────────────────────────────────────────────
# CLI + عَرض
# ─────────────────────────────────────────────────────────────────

def format_graph(graph: MeaningGraph, verbose: bool = False) -> str:
    out = []
    out.append("=" * 60)
    out.append(f"MeaningGraph: «{graph.text}»")
    out.append("=" * 60)

    s = graph.stats()
    out.append(f"\nالإِحصاءات:")
    out.append(f"  العُقَد: {s['nodes']} (Certificates={s['certificate_nodes']}، Hypotheses={s['hypothesis_nodes']})")
    out.append(f"  الرَّوابِط: {s['edges']} (Certificates={s['certificate_edges']}، Hypotheses={s['hypothesis_edges']})")
    out.append(f"  التَّغطيَة: {s['coverage_pct']}%")
    out.append(f"  الـ entropy: {s['entropy']} (0 = لا غُموض)")
    out.append(f"  التَّناقُضات: {s['contradictions']}")
    out.append(f"  مُتَّسِق: {'نَعَم ✓' if s['is_consistent'] else 'لا ✗'}")

    out.append(f"\nالعُقَد:")
    for n in graph.nodes:
        out.append(f"  {n}")
        if verbose and n.attributes:
            for k, v in n.attributes.items():
                if v:
                    out.append(f"      {k}: {v}")

    out.append(f"\nالرَّوابِط:")
    for e in graph.edges:
        out.append(f"  {e}")

    if graph.contradictions:
        out.append(f"\nالتَّناقُضات:")
        for c in graph.contradictions:
            out.append(f"  ✗ [{c.severity}] {c.description}")

    return "\n".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("text", nargs="?")
    p.add_argument("--verse", help="آيَة قُرآنيَّة (سُورة:آية)")
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()

    if args.verse:
        # تَحميل الآيَة
        verses_path = _HERE.parent / "data" / "quran-uthmani-with-pause-mark.txt"
        text = None
        if verses_path.exists():
            surah, ayah = args.verse.split(":")
            with open(verses_path, encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("|")
                    if len(parts) >= 3 and parts[0] == str(int(surah)) and parts[1] == str(int(ayah)):
                        text = parts[2]
                        break
        if not text:
            print(f"⚠ لَم نَجِد الآيَة {args.verse}")
            sys.exit(1)
    elif args.text:
        text = args.text
    else:
        p.print_help()
        sys.exit(1)

    ma = MeaningAssembler()
    graph = ma.assemble(text)
    print(format_graph(graph, verbose=args.verbose))


if __name__ == "__main__":
    main()
