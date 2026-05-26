"""fallback_classifier.py — wrapper حَول heuristic gates.

تَوصيَة المُستَخدِم 2026-05-26 (Step C):
  fallback لِلـtokens الَّتي لَم تُحسَم في registry.
  يَلُفّ legacy gates بِدون تَعديل:
    • master_token_lookup (MASAQ table)
    • non_verb_override_gate (tanwin، broken plural، proper nouns…)
    • verb_form_contract (Form I-X detection)
    • closed_function_word_gate
    • explicit_verbs_contract
"""
from __future__ import annotations

import sys
from pathlib import Path
_PARENT = Path(__file__).resolve().parent.parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from ..core import Decision


def classify_via_masaq(token: str) -> Decision | None:
    """master_token_lookup wrapper."""
    try:
        from master_token_lookup import lookup
    except ImportError:
        return None
    r = lookup(token)
    if not r or not r.get("word_class") or r["word_class"] == "UNKNOWN":
        return None
    return Decision(
        surface=token,
        word_class=r["word_class"],
        candidates=[r["word_class"]],
        certainty="Certificate",
        source=r.get("source", "MASAQ"),
        source_ids=[r.get("source", "MASAQ")],
        proof_kind="Certificate",
        priority=10,
        masaq_tag=r.get("masaq_tag", ""),
        role=r.get("role", ""),
        features={
            "root": r.get("root") or None,
            "wazn": r.get("wazn") or None,
            "tense": None, "voice": None, "person": None,
            "number": None, "gender": None,
            "case": r.get("case") or None,
        },
    )


def classify_via_heuristics(token: str) -> Decision:
    """يَستَدعي Layer 1 الكامِل وَ يَلُفّ الإِخراج.

    Layer 1 يَتَوَلَّى كُلّ السِّلسِلَة:
      Step -1: registry
      Step 0: master_token_lookup
      Step 1-N: heuristic gates (Tanwin، VerbForm، NonVerbOverride، …)

    هَذا الـwrapper يُحَوِّل dict القَديم إلى Decision.
    """
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    legacy = clf.classify(token)
    return Decision.from_legacy_dict(legacy, surface=token)


__all__ = ["classify_via_masaq", "classify_via_heuristics"]
