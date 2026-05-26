"""Engine — orchestrator for the three layers + IntegrityContract seal.

Orchestration per 14_Minimal_Complete_Theory:
  Layer 1 → WordClass + segmentation
  Layer 2 → Case + Mark
  Layer 3 → Role
  → claims[] + trace[] built from layer outputs
  → integrity_seal.seal(claims, trace) → proof_trace_hash

CONSTITUTIONAL RULE (enforced via integrity_seal assertions):
  - claims explain (each has a named contract source)
  - hash seals (lives in integrity{} only, never a claim source)

This replaces the archived old_nand approach (see archive/old_nand/).
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CC = _HERE.parent
sys.path.insert(0, str(_CC))


# ─────────────────────────────────────────────────────────────
# Phase 4 contextual-resolver flag check
# ─────────────────────────────────────────────────────────────
# Mirrors arabic_analyzer.contextual_resolver.integration.is_enabled.
# Imported lazily (per call) so flag changes mid-process — which the
# A0 probe does — are honoured without process restart.

_PHASE4_KEYS = (
    "phase4_selected_function",
    "phase4_reason",
    "phase4_context_features",
    "phase4_masaq_compatible_class",
    "phase4_original_candidates",
)


def _phase4_flag_enabled() -> bool:
    try:
        from arabic_analyzer.contextual_resolver.integration import is_enabled
        return bool(is_enabled())
    except Exception:  # noqa: BLE001
        return False


def _extract_phase4_metadata(r1: dict) -> dict:
    """Pull phase4_* keys out of a Layer-1 result dict, plus derived
    certainty/source/unresolved flags. Returns {} if no phase4 keys present.

    Derived keys:
      phase4_source              — "ContextualAmbiguityResolver" when r1.source
                                   shows the resolver promoted the decision.
      phase4_certainty           — "Certificate" if the resolver promoted,
                                   "Hypothesis" if it only attached metadata
                                   without promotion. Absent for unresolved.
      phase4_unresolved_ambiguous — True iff phase4_selected_function reports
                                   the unresolved sentinel.
    """
    meta: dict = {}
    for k in _PHASE4_KEYS:
        if k in r1:
            meta[k] = r1[k]
    if not meta:
        return meta
    sf = meta.get("phase4_selected_function")
    if sf == "unresolved_ambiguous":
        meta["phase4_unresolved_ambiguous"] = True
    if r1.get("source") == "ContextualAmbiguityResolver":
        meta["phase4_source"] = "ContextualAmbiguityResolver"
        meta["phase4_certainty"] = "Certificate"
    elif sf and sf != "unresolved_ambiguous":
        meta["phase4_certainty"] = "Hypothesis"
    return meta


class I3rabEngine:
    """Top-level orchestrator."""

    # Quranic recitation + pause marks — STRIPPED before tokenization.
    # Source: data/contracts/lists/quran_recitation_marks.csv (loaded lazily).
    _RECITATION_MARKS_CACHE: str | None = None

    @classmethod
    def _load_recitation_marks(cls) -> str:
        """Cache string of recitation/pause Unicode chars to strip."""
        if cls._RECITATION_MARKS_CACHE is not None:
            return cls._RECITATION_MARKS_CACHE
        import csv as _csv
        from pathlib import Path as _Path
        p = _Path(__file__).resolve().parent.parent / "data" / "contracts" / "lists" / "quran_recitation_marks.csv"
        marks = []
        if p.exists():
            with open(p, encoding="utf-8") as f:
                for row in _csv.DictReader(f):
                    m = (row.get("mark") or "").strip()
                    if m:
                        marks.append(m)
        cls._RECITATION_MARKS_CACHE = "".join(marks)
        return cls._RECITATION_MARKS_CACHE

    @classmethod
    def _strip_recitation_marks(cls, text: str) -> str:
        """Remove Quran pause/recitation marks from text BEFORE tokenization.

        These marks (ۚ ۖ ۗ ۘ ۙ ۚ ۛ ۜ ۥ ۦ ...) are tajweed annotations,
        NOT words. They must never reach i3rab classification.
        """
        if not text:
            return text
        marks = cls._load_recitation_marks()
        if not marks:
            return text
        # Replace each mark with a space (so adjacent words don't fuse)
        out = text
        for m in marks:
            out = out.replace(m, " ")
        # Collapse multiple spaces
        return " ".join(out.split())

    def __init__(self) -> None:
        from .layer1 import WordClassClassifier
        from .layer2 import CaseMarkClassifier
        from .layer3 import RoleClassifier
        # Local segmenter for L1 of the fractal coordinate
        from segmenter import segment as _segment  # type: ignore
        self._layer1 = WordClassClassifier()
        self._layer2 = CaseMarkClassifier()
        self._layer3 = RoleClassifier()
        self._segment = _segment

    def analyze_sentence(self, text: str):
        from .types import SentenceI3rab, TokenI3rab

        # L0 normalisation guard: strip Quran recitation/pause marks BEFORE
        # tokenization. These marks (ۚ ۖ ۗ ...) are tajweed annotations,
        # not words. Source: data/contracts/lists/quran_recitation_marks.csv.
        cleaned_text = self._strip_recitation_marks(text or "")
        tokens = [t for t in cleaned_text.split() if t]
        sent = SentenceI3rab(text=text)  # keep original for display

        # Layer 1: classify each token + segment for L1 of the coordinate
        # Phase 4 hook: when ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER is ON
        # AND Layer 1 exposes classify_with_context, route through the context
        # variant so the contextual resolver can attach phase4_* metadata.
        # Flag OFF (default): identical behavior to before — classify_with_context
        # is itself a no-op wrapper around classify when the flag is OFF, but we
        # gate at the call site too so the call counters stay clean for the
        # A0 probe.
        use_phase4_hook = (
            _phase4_flag_enabled()
            and hasattr(self._layer1, "classify_with_context")
        )
        for i, tok in enumerate(tokens):
            ti = TokenI3rab(token=tok, position=i)
            if use_phase4_hook:
                r1 = self._layer1.classify_with_context(
                    tok,
                    prev_tokens=tokens[:i],
                    next_tokens=tokens[i + 1:],
                )
            else:
                r1 = self._layer1.classify(tok)
            ti.word_class = r1["word_class"]
            ti.word_class_source = r1["source"]
            ti.closed_class_kind = r1["closed_class_kind"]
            ti.verb_aspect = r1["verb_aspect"]
            ti.root = r1["root"]
            ti.wazn = r1["wazn"]
            ti.operator_i3rab = r1["operator_i3rab"]
            # Proof-theoretic metadata for wordclass
            ti.wordclass_kind = r1.get("proof_kind", "")
            ti.wordclass_contract = r1.get("proof_contract", "")
            ti.wordclass_blockers = list(r1.get("proof_blockers", []))
            ti.wordclass_alternatives = list(r1.get("proof_alternatives", []))
            # Phase 4 metadata — empty dict if no phase4_* keys in r1, so
            # flag-OFF paths leave ti.phase4 as the default empty dict.
            ti.phase4 = _extract_phase4_metadata(r1)
            # Segmentation for L1 of the fractal coordinate
            try:
                seg = self._segment(tok, normalize_input=True)
                ti.prefixes = list(seg.prefixes)
                ti.stem = seg.stem
                ti.suffixes = list(seg.suffixes)
            except Exception:
                ti.prefixes = []
                ti.stem = tok
                ti.suffixes = []
            sent.tokens.append(ti)

        # Layer 2: assign case+mark given Layer 1 + neighbors
        self._layer2.classify_sentence(sent)

        # Layer 3: assign role given Layer 1 + Layer 2 + neighbors
        self._layer3.classify_sentence(sent)

        # === Build claims[] + trace[] per token, then seal with integrity ===
        from integrity_seal import (  # type: ignore
            seal,
            assert_hash_not_source_of_claim,
            assert_integrity_section_separate,
        )
        from dataclasses import asdict

        for ti in sent.tokens:
            # claims: named conclusions, each with a contract source
            claims = []
            if ti.word_class:
                claims.append({
                    "id": "word_class",
                    "value": ti.word_class,
                    "source": ti.wordclass_contract or ti.word_class_source,
                })
            if ti.root:
                claims.append({
                    "id": "root",
                    "value": ti.root,
                    "source": "root_pipeline:wazn_aligner",
                })
            if ti.wazn:
                claims.append({
                    "id": "wazn",
                    "value": ti.wazn,
                    "source": "root_pipeline:wazn_aligner",
                })
            if ti.case_id is not None:
                claims.append({
                    "id": "case",
                    "value": ti.case_id,
                    "source": ti.case_contract or "case_by_final_diacritic",
                })
            if ti.mark_id is not None:
                claims.append({
                    "id": "mark",
                    "value": ti.mark_id,
                    "source": ti.case_contract or "mark_by_case",
                })
            if ti.tanwin:
                claims.append({
                    "id": "tanwin",
                    "value": ti.tanwin,
                    "source": "case_by_final_diacritic:tanwin_marker",
                })
            if ti.role_phrase:
                claims.append({
                    "id": "role",
                    "value": ti.role_phrase,
                    "source": ti.role_contract or "role_positional",
                })

            # trace: which contracts ran, in order
            trace = [
                {
                    "contract": "Layer1:WordClassClassifier",
                    "result": ti.wordclass_kind or "PASS",
                },
                {
                    "contract": "Layer2:CaseMarkClassifier",
                    "result": ti.case_kind or "PASS",
                },
                {
                    "contract": "Layer3:RoleClassifier",
                    "result": ti.role_kind or "PASS",
                },
            ]

            # residuals/blockers — what didn't close
            residuals = []
            if ti.wordclass_blockers:
                residuals.extend(
                    [{"layer": "wordclass", "blocker": b}
                     for b in ti.wordclass_blockers]
                )
            if ti.case_blockers:
                residuals.extend(
                    [{"layer": "case", "blocker": b}
                     for b in ti.case_blockers]
                )
            if ti.role_blockers:
                residuals.extend(
                    [{"layer": "role", "blocker": b}
                     for b in ti.role_blockers]
                )

            # Seal — the ONLY place a hash exists
            sealed = seal(claims, trace)

            ti.claims = claims
            ti.trace = trace
            ti.residuals = residuals
            ti.integrity = asdict(sealed)

            # Constitutional check — assertions must pass on every token
            record = {
                "claims": claims,
                "trace": trace,
                "integrity": ti.integrity,
            }
            assert_hash_not_source_of_claim(record)
            assert_integrity_section_separate(record)

        return sent
