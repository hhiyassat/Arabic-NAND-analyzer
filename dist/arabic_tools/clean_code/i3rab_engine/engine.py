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


class I3rabEngine:
    """Top-level orchestrator."""

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

        tokens = [t for t in (text or "").split() if t]
        sent = SentenceI3rab(text=text)

        # Layer 1: classify each token + segment for L1 of the coordinate
        for i, tok in enumerate(tokens):
            ti = TokenI3rab(token=tok, position=i)
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
