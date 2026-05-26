"""text_graph_assembler.py — جَلسة 20: تَجميع RelationGraph لِنَصّ كامِل.

يَأخُذ نَصًّا مُتَعَدِّد الجُمَل، يُجري:

  1. ClauseSegmenter             → list[Clause]
  2. I3rabEngine.analyze_sentence(clause.text) لِكُلّ جُملة → SentenceI3rab
  3. RelationExtractor.extract(sent) لِكُلّ جُملة → RelationGraph
  4. InterClauseExtractor.extract(clauses) → list[InterClauseRelation]
  5. PronounCliticResolver.resolve لِكُلّ جُملة → ضَمائر مَع referent
  6. دَمج كُلّ ذلِك في graph واحِد بِـ:
       - entity_id فَريد عَلى مُستَوى النَّصّ (c{clause}_t{token})
       - inter-clause relations كَ edges خاصَّة (clause_id → clause_id)
       - pronoun resolution edges (clitic_host → referent)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from clause_segmenter import ClauseSegmenter
from i3rab_engine.engine import I3rabEngine
from relation_extractor import RelationExtractor
from inter_clause_extractor import InterClauseExtractor
from pronoun_clitic_resolver import PronounCliticResolver
from anaphora_resolver_v2 import AnaphoraResolverV2
from speech_frame_extractor import SpeechFrameExtractor
from relation_schema import EntityNode, Relation, RelationGraph


CONTRACT_NAME = "TextGraphAssembler:v1"


@dataclass
class TextGraph:
    """graph على مُستَوى النَّصّ بأَكمَلِه."""
    source_text: str = ""
    clauses_text: list = field(default_factory=list)
    nodes: dict = field(default_factory=dict)         # entity_id → EntityNode
    intra_relations: list = field(default_factory=list)  # list[Relation]
    inter_clause_relations: list = field(default_factory=list)  # list[InterClauseRelation]
    pronoun_references: list = field(default_factory=list)  # list[CliticReference]
    contract: str = CONTRACT_NAME

    def to_dict(self) -> dict:
        return {
            "contract": self.contract,
            "source_text": self.source_text,
            "n_clauses": len(self.clauses_text),
            "clauses_text": self.clauses_text,
            "n_nodes": len(self.nodes),
            "n_intra_relations": len(self.intra_relations),
            "n_inter_clause_relations": len(self.inter_clause_relations),
            "n_pronoun_references": len(self.pronoun_references),
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "intra_relations": [r.to_dict() for r in self.intra_relations],
            "inter_clause_relations": [r.to_dict() for r in self.inter_clause_relations],
            "pronoun_references": [r.to_dict() for r in self.pronoun_references],
        }


class TextGraphAssembler:

    def __init__(self) -> None:
        self._segmenter = ClauseSegmenter()
        self._engine = I3rabEngine()
        self._rel_extractor = RelationExtractor()
        self._inter_extractor = InterClauseExtractor()
        self._pronoun_resolver = PronounCliticResolver()  # v1 legacy
        self._anaphora_v2 = AnaphoraResolverV2()           # v2 — يَستَخدِم SpeechFrames
        self._speech_extractor = SpeechFrameExtractor()

    def assemble(self, text: str) -> TextGraph:
        tg = TextGraph(source_text=text)
        # 1. تَقسيم الجُمَل
        clauses = self._segmenter.segment(text)
        tg.clauses_text = [c.text for c in clauses]

        # تَتَبُّع الأَسماء عَبر الجُمَل — لِحَلّ ضَمائر تَشير إلى مَرجِع
        # في جُملة سابِقَة (جَلسة 23 fix).
        cross_clause_nouns: list[tuple[str, str]] = []

        # SpeechFrames عَلى مُستَوى الآية كامِلَة (لِيَنتَقِل المُخاطَب)
        # نُحَلِّل الآية كامِلَةً بِالـ i3rab engine لِنُمَرِّر word_class لِلـ extractor
        verse_sent = self._engine.analyze_sentence(text)
        full_text_speech = self._speech_extractor.extract(
            text, i3rab_tokens=verse_sent.tokens,
        )
        verse_frames = full_text_speech["frames"]
        verse_tracker = full_text_speech["tracker"]

        # 2-3-5. لِكُلّ جُملة: i3rab + relations + ضَمائر (v2: SpeechFrames-aware)
        for ci, clause in enumerate(clauses):
            sent = self._engine.analyze_sentence(clause.text)
            sub_graph = self._rel_extractor.extract(sent)
            # v2: استَخدِم SpeechFrames المَبنِيَّة على مُستَوى الآية كامِلَة
            # حَتّى يَستَفيد المُخاطَب مِن نِداء سابِق («يا أَيُّها الَّذين آمنوا...» في 2:282)
            v2_refs = self._anaphora_v2.resolve(
                sent.tokens,
                frames=verse_frames,
                tracker=verse_tracker,
            )
            # legacy للمُقارَنَة (سَيُحذَف في إِصدار لاحِق)
            pronoun_refs = self._pronoun_resolver.resolve(sent.tokens)
            # نَستَخدِم v2 كَ الأَساس
            pronoun_refs = v2_refs

            # نَقل nodes مَع تَعديل entity_id إِلى مَفهوم نَصّ-مُستَوى
            id_map: dict[str, str] = {}  # clause-local → text-global
            for local_id, node in sub_graph.nodes.items():
                global_id = f"c{ci}_{local_id}"
                id_map[local_id] = global_id
                new_node = EntityNode(
                    entity_id=global_id,
                    surface=node.surface,
                    surface_plain=node.surface_plain,
                    position=node.position,
                    root=node.root,
                    wazn=node.wazn,
                    status=node.status,
                    word_class=node.word_class,
                    role_phrase=node.role_phrase,
                    case_name=node.case_name,
                    is_singular_term=node.is_singular_term,
                    is_divine_name=node.is_divine_name,
                    source_of_claim=f"clause[{ci}]:{node.source_of_claim}",
                )
                tg.nodes[global_id] = new_node

            for rel in sub_graph.relations:
                new_rel = Relation(
                    name=rel.name,
                    kind_type=rel.kind_type,
                    source_id=id_map.get(rel.source_id, rel.source_id),
                    target_id=id_map.get(rel.target_id, rel.target_id) if rel.target_id != "—" else "—",
                    operator=rel.operator,
                    kind=rel.kind,
                    source_of_claim=f"clause[{ci}]:{rel.source_of_claim}",
                    contract=rel.contract,
                    alternatives=list(rel.alternatives),
                )
                tg.intra_relations.append(new_rel)

            # ضَمائر v2 — تَحويل الفَهارِس لِـ global ids
            # v2 يَستَخدِم: host_position, referent_text (مِن frame/entity)
            for pref in pronoun_refs:
                # adapter لِـ v2 ResolvedReference
                if hasattr(pref, "host_position"):
                    host_global = f"c{ci}_t{pref.host_position}"
                    # v2: referent يَأتي مِن frame_addressee/frame_speaker/entity_match
                    # نُسَجِّل بِالنَّصّ والـ source بِدون global_id (لا يَلزَم)
                    pref.host_token_idx = host_global  # type: ignore[attr-defined]
                    pref.host_surface = pref.host_token  # type: ignore[attr-defined]
                    pref.referent_surface = pref.referent_text  # type: ignore[attr-defined]
                    pref.referent_token_idx = pref.referent_text  # type: ignore[attr-defined]
                else:
                    # legacy v1 path (CliticReference)
                    host_global = f"c{ci}_t{pref.host_token_idx}"
                    referent_global = None
                    if pref.referent_token_idx is not None:
                        referent_global = f"c{ci}_t{pref.referent_token_idx}"
                    else:
                        if cross_clause_nouns:
                            cand_id, cand_surface = cross_clause_nouns[-1]
                            referent_global = cand_id
                            pref.referent_surface = cand_surface
                            pref.source_of_claim += " | cross_clause_fallback:last_prior_noun"
                    pref.host_token_idx = host_global  # type: ignore[assignment]
                    pref.referent_token_idx = referent_global  # type: ignore[assignment]
                tg.pronoun_references.append(pref)

            # تَحديث قائِمَة الأَسماء العابِرَة لِلجُمَل
            for local_id, node in sub_graph.nodes.items():
                if node.word_class in ("ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM", "JALALAH"):
                    cross_clause_nouns.append((id_map[local_id], node.surface))

        # 4. inter-clause relations
        tg.inter_clause_relations = self._inter_extractor.extract(clauses)
        return tg


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    asm = TextGraphAssembler()

    text = "كَتَبَ الْوَلَدُ كِتَابًا. وَقَرَأَهُ أَخُوهُ"
    tg = asm.assemble(text)
    print(f"النَّصّ: {text}")
    print(f"الجُمَل: {len(tg.clauses_text)}")
    for i, c in enumerate(tg.clauses_text):
        print(f"  [{i}] {c}")
    print(f"العُقَد: {len(tg.nodes)}")
    print(f"عَلاقات داخِل الجُمَل: {len(tg.intra_relations)}")
    for r in tg.intra_relations:
        print(f"  • {r.name}: {r.source_id} → {r.target_id}")
    print(f"عَلاقات بَين الجُمَل: {len(tg.inter_clause_relations)}")
    for r in tg.inter_clause_relations:
        print(f"  ◆ {r.name}: clause[{r.source_clause_idx}] ← clause[{r.target_clause_idx}] via «{r.trigger}»")
    print(f"إِحالات الضَّمائر: {len(tg.pronoun_references)}")
    for pref in tg.pronoun_references:
        print(f"  ⤺ «{pref.clitic}» في {pref.host_surface} → {pref.referent_surface}")
