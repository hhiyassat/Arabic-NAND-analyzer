"""clause_segmenter.py — M1.A: Multi-clause segmenter (rule-based, honest).

CONSTITUTIONAL CORRECTION (2026-05-22):
Pause marks (ۖ ۚ ۛ ۗ ۙ ۘ ۜ) were previously used as INPUT to this segmenter.
That was a self-fulfilling architecture: we then measured the segmenter
against the same pause marks. The "Recall 99.9% / Precision 100%" claim
that resulted was zero-value.

Pause marks are now treated correctly:
  • STRIPPED from input before segmentation (noise, not signal).
  • Used ONLY as ground truth in `scripts/eval_segmenter_honest.py`.

Per 14_Minimal_Complete_Theory: every rule lives in a data file. This
module loads boundary + connective + conditional rules from CSV and
applies them to produce a list of Clause objects with ProofObject-like
metadata (source_of_claim, kind, alternatives).

Inputs:  raw Arabic text
Outputs: list[Clause]

Rule-based signals only:
  1. Arabic/Latin punctuation                         (Certificate)
  2. Connective particles at word start (و/ف/ثُمَّ/بَل/لَكِنَّ/أَو/أَم)  (Hypothesis)
  3. Conditional particles at word start (إذا/إن/لو/...) (Hypothesis)
  4. End-of-text                                       (Certificate)

Constitutional commitments (per §12 Project Scope Declaration):
  1. Source-of-Claim — every clause carries the rule that produced it
  2. Confidence      — kind = Certificate/Hypothesis (no scalar yet)
  3. Alternatives    — preserved when multiple boundary rules disagree
  4. Reversible      — not enforced at this layer (M2 gap)
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows
from wazn_data import DIACRITICS


CONTRACT_NAME = "ClauseSegmenter:v2"

# Quranic pause marks (علامات الوقف) — ground truth only, NEVER input.
# Stripped from any text before segmentation.
PAUSE_MARKS = {
    "ۖ",  # ۖ صلى
    "ۗ",  # ۗ قلى
    "ۘ",  # ۘ لازم
    "ۙ",  # ۙ ممنوع
    "ۚ",  # ۚ جواز
    "ۛ",  # ۛ معانقة
    "ۜ",  # ۜ مجوّز
}

# RECITATION_MARKS now live in data/contracts/lists/quran_recitation_marks.csv
# (loaded via SingularTermDetector). Kept here for back-compat imports only.


def _strip_pause_marks(s: str) -> str:
    """Remove all Quranic pause marks AND recitation marks from text.
    Pause marks are evaluation ground truth, not segmentation input.
    Recitation marks load from `data/contracts/lists/quran_recitation_marks.csv`.
    """
    if not s:
        return s
    # نَزع pause marks مُباشَرَة
    s = "".join(ch for ch in s if ch not in PAUSE_MARKS)
    # نَزع recitation marks عَبر detector (data-driven)
    try:
        from singular_term_detector import get_singular_term_detector
        s = get_singular_term_detector().strip_recitation_marks(s)
    except Exception:
        pass  # fallback لِبيئات بِلا الـ contract
    return s


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


# ============================================================================
# Schema
# ============================================================================

@dataclass
class Clause:
    """A single clausal unit with provenance."""
    text: str
    start_idx: int
    end_idx: int
    type: str = "main"
    connective: Optional[str] = None
    parent_clause_id: Optional[int] = None
    kind: str = "Hypothesis"  # Certificate | Hypothesis | Zero
    source_of_claim: str = ""
    contract: str = CONTRACT_NAME
    alternatives: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
            "type": self.type,
            "connective": self.connective,
            "parent_clause_id": self.parent_clause_id,
            "kind": self.kind,
            "source_of_claim": self.source_of_claim,
            "contract": self.contract,
            "alternatives": self.alternatives,
        }


# ============================================================================
# Engine
# ============================================================================

class ClauseSegmenter:
    """Segment Arabic text into clauses per data-driven rules.

    Pause marks (if present) are stripped before any analysis.
    """

    def __init__(self) -> None:
        self._boundary_rules = _load_rows("clause_boundary_rules.csv")
        self._boundary_rules.sort(key=lambda r: int(r.get("priority", "99")))
        self._relation_rules: list = []
        try:
            self._relation_rules = _load_rows("clause_relation_rules.csv")
            self._relation_rules.sort(key=lambda r: int(r.get("priority", "99")))
        except Exception:
            self._relation_rules = []

    def segment(self, text: str) -> list[Clause]:
        if not text or not text.strip():
            return []

        # CONSTITUTIONAL: strip pause marks before doing anything.
        # They are ground truth, not signal.
        text = _strip_pause_marks(text)

        # Phase 1: collect boundary positions from all rule families.
        boundary_positions = self._collect_boundary_positions(text)

        # Phase 2: split text at boundary positions → spans.
        spans = self._split_at_boundaries(text, boundary_positions)

        # Phase 3: assign connective + conditional type per span.
        clauses = self._build_clauses(spans, text)

        return clauses

    # ------------------------------------------------------------------
    # Phase 1 — boundary detection (rule-based, no pause marks)
    # ------------------------------------------------------------------

    def _collect_boundary_positions(self, text: str) -> list[tuple[int, str, str]]:
        """Return list of (position, rule_name, confidence_kind).

        Position is character offset where a NEW clause begins.
        """
        boundaries: list[tuple[int, str, str]] = []
        boundaries.append((0, "start_of_text", "Certificate"))

        # ── 1a. Punctuation boundaries ──
        for rule in self._boundary_rules:
            kind = rule.get("kind", "")
            marker = rule.get("marker", "")
            name = rule.get("name", "")
            action = rule.get("action", "")
            if kind == "punctuation":
                pos = 0
                while True:
                    found = text.find(marker, pos)
                    if found < 0:
                        break
                    boundary_at = found + len(marker)
                    conf = "Certificate" if action == "split_after" else "Hypothesis"
                    boundaries.append((boundary_at, name, conf))
                    pos = found + 1
            elif kind == "whitespace":
                actual_marker = marker.replace("\\n", "\n")
                pos = 0
                while True:
                    found = text.find(actual_marker, pos)
                    if found < 0:
                        break
                    boundary_at = found + len(actual_marker)
                    boundaries.append((boundary_at, name, "Certificate"))
                    pos = found + 1

        # ── 1b. Connective/conditional particles at word start ──
        #
        # A clause boundary is proposed BEFORE a word-initial connective
        # particle (و / ف / ثُمَّ / بَل / لَكِنَّ / أَو / أَم) or conditional
        # marker (إذا / إن / لو / ...), provided:
        #   • there is non-empty preceding content (boundary != 0)
        #   • the connective is not part of a single-letter word
        #     for clitics like و / ف, this means the word must have
        #     length >= 2 (و alone isn't a clause-starting و).
        for rule in self._relation_rules:
            kind = rule.get("kind", "")
            marker_raw = rule.get("marker", "")
            name = rule.get("name", "")
            if kind not in ("connective", "conditional"):
                continue
            marker = _strip_diac(marker_raw)
            if not marker:
                continue
            for word_start in self._iter_word_starts(text):
                # Word at this position
                word_end = self._word_end(text, word_start)
                if word_end <= word_start:
                    continue
                word_plain = _strip_diac(text[word_start:word_end])
                if len(marker) == 1:
                    # Single-letter clitic (و, ف): require word_plain starts
                    # with the clitic AND there's at least one more letter
                    # AND the previous char (if any) is a word separator.
                    if not word_plain.startswith(marker):
                        continue
                    if len(word_plain) < 2:
                        continue
                else:
                    # Multi-letter particle: require exact match on the
                    # full word (so "إن" matches but "إنّما" does not).
                    if word_plain != marker:
                        continue
                # Don't propose boundary at position 0 (no preceding clause)
                if word_start == 0:
                    continue
                boundaries.append((word_start, name, "Hypothesis"))

        # ── 1c. End of text ──
        boundaries.append((len(text), "end_of_text", "Certificate"))

        # Deduplicate by position; keep highest-confidence first occurrence
        # (Certificate beats Hypothesis at same position).
        by_pos: dict[int, tuple[str, str]] = {}
        confidence_rank = {"Certificate": 0, "Hypothesis": 1, "Zero": 2}
        for pos, name, conf in boundaries:
            if pos in by_pos:
                existing_name, existing_conf = by_pos[pos]
                if confidence_rank[conf] < confidence_rank[existing_conf]:
                    by_pos[pos] = (name, conf)
                elif confidence_rank[conf] == confidence_rank[existing_conf]:
                    by_pos[pos] = (existing_name + " + " + name, conf)
            else:
                by_pos[pos] = (name, conf)

        return sorted([(p, n, c) for p, (n, c) in by_pos.items()])

    @staticmethod
    def _iter_word_starts(text: str):
        """Yield positions where a new word begins (after whitespace or at idx 0)."""
        if not text:
            return
        if not text[0].isspace():
            yield 0
        for i in range(1, len(text)):
            if text[i].isspace():
                continue
            if text[i - 1].isspace():
                yield i

    @staticmethod
    def _word_end(text: str, start: int) -> int:
        i = start
        while i < len(text) and not text[i].isspace():
            i += 1
        return i

    def _split_at_boundaries(
        self,
        text: str,
        boundaries: list[tuple[int, str, str]],
    ) -> list[tuple[str, int, int, str, str]]:
        """Return list of (chunk, start_idx, end_idx, src_rule, conf)."""
        spans: list[tuple[str, int, int, str, str]] = []
        # boundaries already sorted; first is (0, start_of_text, ...),
        # last is (len(text), end_of_text, ...).
        for i in range(len(boundaries) - 1):
            start_pos, src_start, _ = boundaries[i]
            end_pos, src_end, conf_end = boundaries[i + 1]
            chunk = text[start_pos:end_pos].strip()
            if not chunk:
                continue
            # The source of THIS clause's RIGHT boundary is more informative
            # than its left, since the right boundary is what closes it.
            spans.append((chunk, start_pos, end_pos, src_end, conf_end))
        return spans

    # ------------------------------------------------------------------
    # Phase 3 — connective / conditional typing
    # ------------------------------------------------------------------

    def _build_clauses(self, spans: list, text: str) -> list[Clause]:
        clauses: list[Clause] = []
        for (chunk, start, end, src, kind) in spans:
            conn, ctype, conn_src = self._detect_connective(chunk)
            cond_type, cond_src = self._detect_conditional(chunk)
            ctype_final = cond_type or ctype or "main"
            sources = [src]
            if conn_src:
                sources.append(conn_src)
            if cond_src:
                sources.append(cond_src)
            clauses.append(Clause(
                text=chunk,
                start_idx=start,
                end_idx=end,
                type=ctype_final,
                connective=conn,
                kind=kind,
                source_of_claim=" + ".join(sources),
            ))
        return clauses

    def _first_word_plain(self, chunk: str) -> str:
        chunk_stripped = chunk.lstrip()
        if not chunk_stripped:
            return ""
        sp = re.split(r"\s+", chunk_stripped, maxsplit=1)
        first = sp[0] if sp else ""
        first = first.rstrip(".،,؛:؟?!")
        return _strip_diac(first)

    def _detect_connective(self, chunk: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        if not self._relation_rules:
            return None, None, None
        first_plain = self._first_word_plain(chunk)
        if not first_plain:
            return None, None, None
        for rule in self._relation_rules:
            if rule.get("kind") != "connective":
                continue
            marker = _strip_diac(rule.get("marker", ""))
            if not marker:
                continue
            if len(marker) == 1:
                if first_plain.startswith(marker) and len(first_plain) > 1:
                    return rule.get("marker"), rule.get("creates_clause_type", "coordinate"), rule.get("name", "")
            else:
                if first_plain == marker:
                    return rule.get("marker"), rule.get("creates_clause_type", "coordinate"), rule.get("name", "")
        return None, None, None

    def _detect_conditional(self, chunk: str) -> tuple[Optional[str], Optional[str]]:
        if not self._relation_rules:
            return None, None
        first_plain = self._first_word_plain(chunk)
        if not first_plain:
            return None, None
        for rule in self._relation_rules:
            if rule.get("kind") != "conditional":
                continue
            marker = _strip_diac(rule.get("marker", ""))
            if not marker:
                continue
            if first_plain == marker:
                return rule.get("creates_clause_type", "conditional_protasis"), rule.get("name", "")
        return None, None

    def source(self) -> str:
        return CONTRACT_NAME


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    seg = ClauseSegmenter()
    print(f"contract: {seg.source()}")
    print(f"boundary rules: {len(seg._boundary_rules)}")
    print(f"relation rules: {len(seg._relation_rules)}")
    print()

    tests = [
        "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ. مَالِكِ يَوْمِ الدِّينِ.",
        "قَالَ مُوسَى: ائْتُونِي",
        "أَأَنْتَ قُلْتَ هَذَا؟ نَعَمْ",
        "إِنَّ مَعَ الْعُسْرِ يُسْرًا",
        "ءَامَنَ ٱلرَّسُولُ بِمَا أُنزِلَ إِلَيْهِ وَٱلْمُؤْمِنُونَ كُلٌّ ءَامَنَ بِٱللَّهِ",
    ]
    for text in tests:
        clauses = seg.segment(text)
        print(f"input: {text}")
        for i, c in enumerate(clauses):
            print(f"  [{i}] type={c.type} conn={c.connective} kind={c.kind}")
            print(f"      text={c.text!r}")
            print(f"      src={c.source_of_claim}")
        print()
