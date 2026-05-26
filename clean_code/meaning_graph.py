"""meaning_graph.py — Phase F: شَبَكَة المَعنى المُوَحَّدَة.

Per `Distinction_Meaning_vs_Interpretation.md`:
  • Meaning = structural composition (entities + relations + events + resolutions)
  • Interpretation = خارِج النِّطاق

MC-COMPLIANT:
  • كُلّ Node + Edge بِـ ProofObject metadata
  • كُلّ alternative مَحفوظَة
  • Certificate / Hypothesis / Zero صَريحَة
  • Contradictions مَكشوفَة، لا مُخفاة
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal, Optional, Any

NodeType = Literal["entity", "event", "transformation", "construction"]
EdgeType = Literal[
    # مِن RelationGraph
    "agent_of", "patient_of", "patient2_of", "topic_of", "comment_of",
    "possessor_of", "attribute_of", "coordinate_of", "substitute_of",
    "vocative_of", "harf_jarr_of", "verb_in_clause", "topic_anchor",
    "in_location", "at_time", "with_instrument", "by_means_of",
    # مِن EventGraph
    "before_event", "after_event", "during_event",
    # مِن ResolutionGraph
    "anaphora_to", "deixis_to", "relative_to", "identity_through",
    # مِن السَّامَرّائيّ
    "operator_meaning", "construction_pattern",
]


@dataclass
class MeaningNode:
    """عُقدة في شَبَكَة المَعنى."""
    node_id: str
    node_type: NodeType
    surface: str             # النَّصّ السَّطحيّ
    position: int            # مَوضِع في النَّصّ
    # MC metadata
    proof_kind: str = "Certificate"  # Certificate | Hypothesis | Zero
    contract: str = ""
    source_of_claim: str = ""
    # خَصائِص إِضافيَّة (مَرنَة)
    attributes: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        sym = {"Certificate": "✓", "Hypothesis": "?", "Zero": "✗"}.get(self.proof_kind, "·")
        return f"{sym} {self.node_type}[{self.node_id}]: {self.surface}"


@dataclass
class MeaningEdge:
    """رابِطَة في الشَّبَكَة."""
    edge_id: str
    edge_type: EdgeType
    source: str              # node_id
    target: str              # node_id
    operator: Optional[str] = None  # لِـ harf_jarr مَثَلًا
    # MC metadata
    proof_kind: str = "Certificate"
    contract: str = ""
    source_of_claim: str = ""
    confidence: float = 1.0
    alternatives: list = field(default_factory=list)
    blockers: list = field(default_factory=list)

    def __str__(self) -> str:
        sym = {"Certificate": "✓", "Hypothesis": "?", "Zero": "✗"}.get(self.proof_kind, "·")
        op = f"[{self.operator}]" if self.operator else ""
        return f"{sym} {self.edge_type}{op}: {self.source} → {self.target}"


@dataclass
class Contradiction:
    """تَناقُض بِنيَويّ مَكشوف في الشَّبَكَة."""
    contradiction_id: str
    description: str
    involved_edges: list[str] = field(default_factory=list)
    severity: Literal["low", "medium", "high"] = "medium"


@dataclass
class MeaningGraph:
    """شَبَكَة المَعنى الكامِلَة لِنَصّ.

    MC-COMPLIANT: كُلّ node + edge بِـ ProofObject.
    """
    text: str
    nodes: list[MeaningNode] = field(default_factory=list)
    edges: list[MeaningEdge] = field(default_factory=list)
    contradictions: list[Contradiction] = field(default_factory=list)
    contract: str = "MeaningGraph:v1"

    def add_node(self, n: MeaningNode):
        self.nodes.append(n)

    def add_edge(self, e: MeaningEdge):
        self.edges.append(e)

    def add_contradiction(self, c: Contradiction):
        self.contradictions.append(c)

    # ──────────────────────────────────────────────────────────
    # المَقاييس
    # ──────────────────────────────────────────────────────────

    @property
    def total_nodes(self) -> int:
        return len(self.nodes)

    @property
    def total_edges(self) -> int:
        return len(self.edges)

    @property
    def certificate_nodes(self) -> int:
        return sum(1 for n in self.nodes if n.proof_kind == "Certificate")

    @property
    def hypothesis_nodes(self) -> int:
        return sum(1 for n in self.nodes if n.proof_kind == "Hypothesis")

    @property
    def certificate_edges(self) -> int:
        return sum(1 for e in self.edges if e.proof_kind == "Certificate")

    @property
    def hypothesis_edges(self) -> int:
        return sum(1 for e in self.edges if e.proof_kind == "Hypothesis")

    @property
    def coverage_pct(self) -> float:
        """نِسبَة الـ tokens المُغَطّاة بِـ node."""
        tokens = self.text.split()
        if not tokens:
            return 0.0
        covered_positions = {n.position for n in self.nodes}
        return len(covered_positions) / len(tokens) * 100

    @property
    def entropy(self) -> float:
        """مِقياس الغُموض الكُلّيّ في الشَّبَكَة (Shannon entropy على البَدائِل)."""
        if not self.edges:
            return 0.0
        # Edge مَع n alternatives → entropy = log2(n+1)
        total_entropy = 0.0
        for e in self.edges:
            n_alts = len(e.alternatives)
            if n_alts > 0:
                total_entropy += math.log2(n_alts + 1)
        return total_entropy

    @property
    def is_consistent(self) -> bool:
        return len(self.contradictions) == 0

    def stats(self) -> dict:
        return {
            "text": self.text,
            "nodes": self.total_nodes,
            "edges": self.total_edges,
            "certificate_nodes": self.certificate_nodes,
            "hypothesis_nodes": self.hypothesis_nodes,
            "certificate_edges": self.certificate_edges,
            "hypothesis_edges": self.hypothesis_edges,
            "coverage_pct": round(self.coverage_pct, 1),
            "entropy": round(self.entropy, 2),
            "contradictions": len(self.contradictions),
            "is_consistent": self.is_consistent,
        }

    # ──────────────────────────────────────────────────────────
    # الِاستِعلامات
    # ──────────────────────────────────────────────────────────

    def get_node(self, node_id: str) -> Optional[MeaningNode]:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        return None

    def edges_from(self, node_id: str) -> list[MeaningEdge]:
        return [e for e in self.edges if e.source == node_id]

    def edges_to(self, node_id: str) -> list[MeaningEdge]:
        return [e for e in self.edges if e.target == node_id]

    def neighbors(self, node_id: str) -> list[str]:
        out = set()
        for e in self.edges:
            if e.source == node_id:
                out.add(e.target)
            if e.target == node_id:
                out.add(e.source)
        return list(out)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "contract": self.contract,
            "stats": self.stats(),
            "nodes": [
                {
                    "id": n.node_id, "type": n.node_type, "surface": n.surface,
                    "position": n.position, "proof_kind": n.proof_kind,
                    "contract": n.contract, "source": n.source_of_claim,
                    "attributes": n.attributes,
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "id": e.edge_id, "type": e.edge_type, "source": e.source,
                    "target": e.target, "operator": e.operator,
                    "proof_kind": e.proof_kind, "contract": e.contract,
                    "source_of_claim": e.source_of_claim,
                    "confidence": e.confidence,
                    "alternatives": e.alternatives,
                    "blockers": e.blockers,
                }
                for e in self.edges
            ],
            "contradictions": [
                {
                    "id": c.contradiction_id,
                    "description": c.description,
                    "edges": c.involved_edges,
                    "severity": c.severity,
                }
                for c in self.contradictions
            ],
        }

    def __str__(self) -> str:
        s = self.stats()
        out = [f"MeaningGraph(text=«{self.text[:50]}...»)"]
        out.append(f"  nodes={s['nodes']} ({s['certificate_nodes']}C/{s['hypothesis_nodes']}H)")
        out.append(f"  edges={s['edges']} ({s['certificate_edges']}C/{s['hypothesis_edges']}H)")
        out.append(f"  coverage={s['coverage_pct']}% | entropy={s['entropy']} | consistent={s['is_consistent']}")
        return "\n".join(out)
