"""relation_adapter.py — يَلُفّ relation_schema القَديم.

Step E (observe): تَحويل records بِين legacy وَ standard schema.
لا تَغيير في output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StandardRelation:
    """تَنسيق مُوَحَّد لِلـrelation (مُتَوافِق مَع relation_schema القَديم)."""
    name: str                    # agent_of / patient_of / harf_jarr_of / …
    source_id: str               # tID مَثَل "t3"
    target_id: str
    kind_type: str = ""          # subj_pred / kana_comment / …
    role_kind: str = "Hypothesis"  # Certificate / Hypothesis / Zero
    source_of_claim: str = ""
    position_evidence: str = ""
    metadata: dict = field(default_factory=dict)


def relation_to_legacy(rel: StandardRelation) -> dict:
    """تَحويل StandardRelation إلى dict تَنسيق Layer 3."""
    return {
        "name": rel.name,
        "source_id": rel.source_id,
        "target_id": rel.target_id,
        "kind_type": rel.kind_type,
        "role_kind": rel.role_kind,
        "source_of_claim": rel.source_of_claim,
        "position_evidence": rel.position_evidence,
        **rel.metadata,
    }


def relation_from_legacy(d: dict | Any) -> StandardRelation:
    """يُنشِئ StandardRelation مِن dict أَو object القَديم."""
    if hasattr(d, "name"):  # dataclass object مِن relation_schema
        return StandardRelation(
            name=getattr(d, "name", ""),
            source_id=getattr(d, "source_id", ""),
            target_id=getattr(d, "target_id", ""),
            kind_type=getattr(d, "kind_type", ""),
            role_kind=getattr(d, "role_kind", "Hypothesis"),
            source_of_claim=getattr(d, "source_of_claim", ""),
            position_evidence=getattr(d, "position_evidence", ""),
        )
    return StandardRelation(
        name=d.get("name", ""),
        source_id=d.get("source_id", ""),
        target_id=d.get("target_id", ""),
        kind_type=d.get("kind_type", ""),
        role_kind=d.get("role_kind", "Hypothesis"),
        source_of_claim=d.get("source_of_claim", ""),
        position_evidence=d.get("position_evidence", ""),
        metadata={k: v for k, v in d.items()
                 if k not in ("name","source_id","target_id","kind_type",
                              "role_kind","source_of_claim","position_evidence")},
    )


__all__ = ["StandardRelation", "relation_to_legacy", "relation_from_legacy"]
