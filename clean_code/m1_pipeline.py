"""m1_pipeline.py — M1: Language Layer pipeline.

Composes the four M1 detectors:
  A) ClauseSegmenter      — split text into clauses
  B) SpeechActDetector    — classify each clause's act type + embedding
  C) NegationDetector     — find negations + scope per clause
  D) ModalDetector        — find modal markers per clause

Output: M1Result with per-clause structured analysis. All sub-results
carry ProofObject-like provenance (kind, source_of_claim, alternatives).

Per 14_Minimal_Complete_Theory: this pipeline contains NO inline rules —
it only orchestrates the four detectors, each of which loads its rules
from data/contracts/rules/*.csv.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from clause_segmenter import ClauseSegmenter, Clause
from speech_act_detector import SpeechActDetector, SpeechAct
from negation_detector import NegationDetector, Negation
from modal_detector import ModalDetector, Modal


CONTRACT_NAME = "M1Pipeline:v1"


@dataclass
class ClauseAnalysis:
    """Full M1 analysis for a single clause."""
    clause: Clause
    speech_act: SpeechAct
    embedding: Optional[dict] = None  # speech-act verb rule if this clause embeds another
    negations: list = field(default_factory=list)  # list[Negation]
    modals: list = field(default_factory=list)     # list[Modal]
    contract: str = CONTRACT_NAME

    def to_dict(self) -> dict:
        return {
            "clause": self.clause.to_dict(),
            "speech_act": self.speech_act.to_dict(),
            "embedding": self.embedding,
            "negations": [n.to_dict() for n in self.negations],
            "modals": [m.to_dict() for m in self.modals],
            "contract": self.contract,
        }


@dataclass
class M1Result:
    """Top-level M1 result for a text input."""
    input_text: str
    clause_analyses: list = field(default_factory=list)  # list[ClauseAnalysis]
    contract: str = CONTRACT_NAME

    def to_dict(self) -> dict:
        return {
            "input_text": self.input_text,
            "n_clauses": len(self.clause_analyses),
            "clauses": [ca.to_dict() for ca in self.clause_analyses],
            "contract": self.contract,
        }


class M1Pipeline:
    """Orchestrator for the four M1 detectors."""

    def __init__(self) -> None:
        self._segmenter = ClauseSegmenter()
        self._speech_act = SpeechActDetector()
        self._negation = NegationDetector()
        self._modal = ModalDetector()

    def analyze(self, text: str) -> M1Result:
        clauses = self._segmenter.segment(text)
        analyses: list[ClauseAnalysis] = []
        for clause in clauses:
            sa = self._speech_act.detect(clause.text)
            embedding = self._speech_act.detect_embedding(clause.text)
            negs = self._negation.detect(clause.text)
            mods = self._modal.detect(clause.text)
            analyses.append(ClauseAnalysis(
                clause=clause,
                speech_act=sa,
                embedding=embedding,
                negations=negs,
                modals=mods,
            ))
        return M1Result(input_text=text, clause_analyses=analyses)

    def source(self) -> str:
        return CONTRACT_NAME


# ============================================================================
# Pretty-printer for human inspection
# ============================================================================

def format_m1_result(r: M1Result, verbose: bool = False) -> str:
    out = []
    out.append(f"=== M1 analysis ({r.contract}) ===")
    out.append(f"input:    {r.input_text!r}")
    out.append(f"clauses:  {len(r.clause_analyses)}")
    for i, ca in enumerate(r.clause_analyses):
        c = ca.clause
        out.append(f"")
        out.append(f"[{i}] {c.text!r}")
        out.append(f"     type={c.type}  conn={c.connective}  kind={c.kind}  src={c.source_of_claim}")
        sa = ca.speech_act
        out.append(f"     speech_act = {sa.act_type} ({sa.kind})  src={sa.source_of_claim}")
        if ca.embedding:
            out.append(f"     embedding: {ca.embedding.get('verb_kind')} → {ca.embedding.get('creates_embedded')}  rule={ca.embedding.get('name')}")
        for n in ca.negations:
            out.append(f"     negation @ {n.marker_position}: {n.marker}  eff={n.polarity_effect}  ({n.kind})")
        for m in ca.modals:
            out.append(f"     modal @ {m.marker_position}: {m.marker}  type={m.modal_type}  str={m.strength}  ({m.kind})")
        if verbose:
            for alt in sa.alternatives:
                out.append(f"     [alt speech_act] {alt}")
    return "\n".join(out)


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    pipe = M1Pipeline()
    print(f"contract: {pipe.source()}")
    print()

    samples = [
        "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ",
        "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
        "هَلْ أَتَاكَ حَدِيثُ الْغَاشِيَةِ",
        "يَا أَيُّهَا النَّاسُ اعْبُدُوا رَبَّكُمْ",
        "لَا تَأْكُلُوا الرِّبَا",
        "قَدْ أَفْلَحَ الْمُؤْمِنُونَ",
        "قَالَ مُوسَى: ادْعُونِي أَسْتَجِبْ لَكُمْ",
        "إِنْ جَاءَكُمْ فَاسِقٌ بِنَبَإٍ فَتَبَيَّنُوا",
        "لَيْسَ كَمِثْلِهِ شَيْءٌ. وَهُوَ السَّمِيعُ الْبَصِيرُ",
    ]
    for s in samples:
        result = pipe.analyze(s)
        print(format_m1_result(result))
        print()
