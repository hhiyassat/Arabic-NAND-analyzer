"""arabic_analyzer.events — event gate + adapter (observe-only في Step E)."""
from .event_gate import (
    GateVerdict, EnforcementMode,
    can_emit_event, explain_event_gate,
    reset_audit as reset_event_audit,
    get_audit as get_event_audit,
)
from .event_adapter import (
    StandardEvent, event_to_legacy, event_from_legacy,
)

__all__ = [
    "GateVerdict", "EnforcementMode",
    "can_emit_event", "explain_event_gate",
    "reset_event_audit", "get_event_audit",
    "StandardEvent", "event_to_legacy", "event_from_legacy",
]
