"""arabic_analyzer.relations — relation gate + adapter (observe-only في Step E)."""
from .relation_gate import (
    GateVerdict, EnforcementMode,
    can_emit_relation, explain_relation_gate,
    reset_audit as reset_relation_audit,
    get_audit as get_relation_audit,
)
from .relation_adapter import (
    StandardRelation, relation_to_legacy, relation_from_legacy,
)

__all__ = [
    "GateVerdict", "EnforcementMode",
    "can_emit_relation", "explain_relation_gate",
    "reset_relation_audit", "get_relation_audit",
    "StandardRelation", "relation_to_legacy", "relation_from_legacy",
]
