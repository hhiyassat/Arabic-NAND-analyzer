"""relation_schema.py — جَلسة 14: Relation / EntityNode / RelationGraph.

طَبَقَة العَلاقات (Phase C — Layer 3 الدَّستوريَّة) فَوق i3rab.

كُلّ شَيء قابِل لِلتَّحَقُّق:
  • EntityNode: تَمثيل كَلِمَة بِسِماتها الصَّرفيَّة (root، wazn، status).
  • Relation: قَوس مُوَجَّه بَين EntityNode و EntityNode (أَو حَدَث).
  • RelationGraph: مَجموعَة nodes + edges + ProofObject لِكُلّ edge.

كُلّ Relation تَحمِل:
  - source_of_claim (أَيّ role في i3rab + أَيّ قاعِدَة في relation_types.csv)
  - kind (Certificate | Hypothesis | Zero) — مَوروثَة مِن i3rab
  - contract (RelationExtractor:vN)
  - alternatives — في حال غُموض

Constitutional commitments:
  1. Source-of-Claim ✓
  2. Confidence kind ✓
  3. Alternatives ✓
  4. Reversible — مُؤَجَّل لِـ M2.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))


CONTRACT_NAME = "RelationSchema:v1"


# ============================================================================
# EntityNode — تَمثيل كَلِمَة كَ كِيان قابِل لِلرَّبط
# ============================================================================

@dataclass
class EntityNode:
    """عُقدَة كِيان في الـ RelationGraph.

    الحَقل الأَساسيّ: `entity_id` — مُعَرِّف داخِل الـ graph (str).
    قَد يَكون token موقعيّ (token_3) أَو مَفهوميّ (entity_aalam_zayd) أَو
    مُحَلّ لِضَمير (resolved_entity_5).
    """

    entity_id: str = ""
    surface: str = ""        # السَّطح كَما ظَهَر في النَّصّ
    surface_plain: str = ""  # بِلا تَشكيل
    position: int = -1       # 0-based في الجُملة (أَو -1 إن كانَ مُحَلًّى)

    # سِمات صَرفيَّة (مِن RootPipeline)
    root: str = "—"
    wazn: str = "—"
    status: str = ""         # open_class | closed_class | jamid | singular_term | no_match

    # سِمات إِعرابيَّة (مِن i3rab)
    word_class: str = ""     # HARF / ISM_MUARAB / FIIL / ...
    role_phrase: str = ""    # مِن Layer 3
    case_name: str = ""      # مَرفوع / مَنصوب / مَجرور / ...

    # علم خاصّ: لَفظ مُنفَرِد (اللَّه) — لا يُصَنَّف
    is_singular_term: bool = False
    is_divine_name: bool = False

    # مَصدَر المَعلومات
    source_of_claim: str = ""
    contract: str = "EntityNode:v1"

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "surface": self.surface,
            "surface_plain": self.surface_plain,
            "position": self.position,
            "root": self.root,
            "wazn": self.wazn,
            "status": self.status,
            "word_class": self.word_class,
            "role_phrase": self.role_phrase,
            "case_name": self.case_name,
            "is_singular_term": self.is_singular_term,
            "is_divine_name": self.is_divine_name,
            "source_of_claim": self.source_of_claim,
            "contract": self.contract,
        }


# ============================================================================
# Relation — قَوس مُوَجَّه بَين عُقدَتَين
# ============================================================================

@dataclass
class Relation:
    """عَلاقَة بَين كِيانَين.

    أَنماط (مِن relation_types.csv):
      - subj_pred       (agent_of, patient_of, patient2_of)
      - topic_comment   (topic_of, comment_of, inna_topic_of, ...)
      - possession      (possessor_of)
      - attribute       (attribute_of)
      - coordination    (coordinate_of)
      - apposition      (substitute_of)
      - vocative        (vocative_of)
      - prep_phrase     (harf_jarr_of) — يَحتَوي حَرف الجَرّ
      - clause_anchor   (verb_in_clause / topic_anchor)
      - locative/temporal/manner/cause/goal/source — مِن حَرف الجَرّ
        (سَتُضاف في جَلسة 16 من harf_jarr_relations.csv)
    """

    name: str = ""             # e.g. "agent_of"
    kind_type: str = ""        # e.g. "subj_pred"
    source_id: str = ""        # entity_id لِلطَّرَف الأَوَّل
    target_id: str = ""        # entity_id لِلطَّرَف الثَّاني (أَو "—")
    operator: Optional[str] = None  # لِـ harf_jarr_of: السَّطح "في"، إلخ

    # ProofObject-like
    kind: str = "Hypothesis"   # Certificate | Hypothesis | Zero
    source_of_claim: str = ""  # e.g. "role_فاعل + role_FIIL + relation_types:agent_of"
    contract: str = "Relation:v1"
    alternatives: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind_type": self.kind_type,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "operator": self.operator,
            "kind": self.kind,
            "source_of_claim": self.source_of_claim,
            "contract": self.contract,
            "alternatives": list(self.alternatives),
        }


# ============================================================================
# RelationGraph — حاوي العُقَد والقَوسات
# ============================================================================

@dataclass
class RelationGraph:
    """شَبَكَة كِيانات + علاقات لِجُملة (أَو نَصّ مُجَمَّع).

    nodes — قاموس entity_id → EntityNode
    relations — قائِمَة Relation
    source_text — النَّصّ الأَصليّ (لِلتَّتَبُّع)
    """

    nodes: dict = field(default_factory=dict)
    relations: list = field(default_factory=list)
    source_text: str = ""
    contract: str = CONTRACT_NAME

    def add_node(self, node: EntityNode) -> None:
        if not node.entity_id:
            raise ValueError("EntityNode بِلا entity_id")
        self.nodes[node.entity_id] = node

    def add_relation(self, rel: Relation) -> None:
        if rel.source_id not in self.nodes and rel.source_id != "—":
            raise ValueError(f"Relation.source_id '{rel.source_id}' غَير مَوجود في الـ graph")
        if rel.target_id not in self.nodes and rel.target_id != "—":
            raise ValueError(f"Relation.target_id '{rel.target_id}' غَير مَوجود في الـ graph")
        self.relations.append(rel)

    def neighbors_of(self, entity_id: str) -> list[Relation]:
        return [r for r in self.relations if r.source_id == entity_id or r.target_id == entity_id]

    def to_dict(self) -> dict:
        return {
            "contract": self.contract,
            "source_text": self.source_text,
            "n_nodes": len(self.nodes),
            "n_relations": len(self.relations),
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "relations": [r.to_dict() for r in self.relations],
        }


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    # بِناء graph يَدَوِيّ لِـ «كَتَبَ الوَلَدُ كِتَابًا»
    g = RelationGraph(source_text="كَتَبَ الوَلَدُ كِتَابًا")

    # 3 nodes
    n_verb = EntityNode(
        entity_id="t0",
        surface="كَتَبَ",
        position=0,
        root="كتب",
        wazn="فَعَل",
        status="open_class",
        word_class="FIIL",
        role_phrase="فعل ماضٍ",
        source_of_claim="manual_test",
    )
    n_subj = EntityNode(
        entity_id="t1",
        surface="الْوَلَدُ",
        position=1,
        root="ولد",
        wazn="فَعَل",
        status="open_class",
        word_class="ISM_MUARAB",
        role_phrase="فاعل",
        case_name="مَرْفُوع",
        source_of_claim="manual_test",
    )
    n_obj = EntityNode(
        entity_id="t2",
        surface="كِتَابًا",
        position=2,
        root="كتب",
        wazn="فِعَال",
        status="open_class",
        word_class="ISM_MUARAB",
        role_phrase="مفعول به",
        case_name="مَنْصُوب",
        source_of_claim="manual_test",
    )
    g.add_node(n_verb)
    g.add_node(n_subj)
    g.add_node(n_obj)

    # 2 relations
    g.add_relation(Relation(
        name="agent_of",
        kind_type="subj_pred",
        source_id="t1",
        target_id="t0",
        kind="Hypothesis",
        source_of_claim="role:فاعل + verb:كتب + relation_types:agent_of",
    ))
    g.add_relation(Relation(
        name="patient_of",
        kind_type="subj_pred",
        source_id="t2",
        target_id="t0",
        kind="Hypothesis",
        source_of_claim="role:مفعول_به + verb:كتب + relation_types:patient_of",
    ))

    import json
    print(json.dumps(g.to_dict(), ensure_ascii=False, indent=2))
    print()
    print(f"✓ {len(g.nodes)} nodes, {len(g.relations)} relations")
    assert len(g.nodes) == 3
    assert len(g.relations) == 2
    # neighbors_of(t0) should return both relations (kataba is the verb)
    nbr = g.neighbors_of("t0")
    assert len(nbr) == 2
    print(f"✓ verb t0 has {len(nbr)} incident relations")
