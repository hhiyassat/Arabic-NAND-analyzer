"""fractal_coordinate.py — إحداثيّة fractal recursive لكل token.

Per 14_Minimal_Complete_Theory.md + user proposal: every token after
full analysis carries a contextual fingerprint composed of 6 levels.
The same surface word in different contexts gets a different coordinate.

نموذج البنية:

  L0 — الحامل (Carrier):          السطح + المُجرَّد
  L1 — البنية الداخلية (Internal): البادئات + الجذع + اللواحق
  L2 — الهوية الصرفية (Morphology): فئة + جذر + وزن + (verb_aspect/closed_class_kind)
  L3 — الهوية النحوية (Syntax):     حالة + علامة + دور
  L4 — الجوار (Neighbors):         فئة ما قبل/ما بعد + حروف حاكمة
  L5 — العقد المُصدِر (Contract):   wordclass/case/role contracts + blockers

نمط البنية يتكرّر عند كل مستوى (head + modifiers + role-in-parent) — وهذا
معنى "fractal" البنيوي.

التوقيع له شكلان:
  - coord_path: نصّ مقروء بـ 6 مستويات (للفحص اليدوي والتفسير)
  - coord_hash: hash مدمج 24 hex chars = 96-bit (للفهرسة والمقارنة)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


def _hash6(s: str) -> str:
    """6-char hex digest. 6 hex = 24 bits — كافٍ للحدّ من collisions
    داخل المستوى الواحد، صغير بما يكفي للقراءة."""
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:6]


@dataclass
class FractalCoordinate:
    """Recursive 6-level coordinate for a fully analyzed token."""
    # Raw per-level strings (human-readable)
    L0_carrier: str = ""
    L1_internal: str = ""
    L2_morphology: str = ""
    L3_syntax: str = ""
    L4_neighbors: str = ""
    L5_contracts: str = ""

    # Per-level 6-hex hashes
    L0_hash: str = ""
    L1_hash: str = ""
    L2_hash: str = ""
    L3_hash: str = ""
    L4_hash: str = ""
    L5_hash: str = ""

    @property
    def path(self) -> str:
        """Readable path with all 6 levels, dot-separated."""
        return (
            f"L0[{self.L0_carrier}]"
            f"·L1[{self.L1_internal}]"
            f"·L2[{self.L2_morphology}]"
            f"·L3[{self.L3_syntax}]"
            f"·L4[{self.L4_neighbors}]"
            f"·L5[{self.L5_contracts}]"
        )

    @property
    def hash(self) -> str:
        """Concatenated 96-bit hash (24 hex chars)."""
        return (
            self.L0_hash + self.L1_hash + self.L2_hash
            + self.L3_hash + self.L4_hash + self.L5_hash
        )

    @property
    def hash_dotted(self) -> str:
        """Dotted hash for readability: a1f3.7c2e.0091.3f06.d4b1.8211"""
        return (
            f"{self.L0_hash}.{self.L1_hash}.{self.L2_hash}"
            f".{self.L3_hash}.{self.L4_hash}.{self.L5_hash}"
        )

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "hash": self.hash,
            "hash_dotted": self.hash_dotted,
            "levels": {
                "L0_carrier": self.L0_carrier,
                "L1_internal": self.L1_internal,
                "L2_morphology": self.L2_morphology,
                "L3_syntax": self.L3_syntax,
                "L4_neighbors": self.L4_neighbors,
                "L5_contracts": self.L5_contracts,
            },
            "hashes": {
                "L0": self.L0_hash, "L1": self.L1_hash, "L2": self.L2_hash,
                "L3": self.L3_hash, "L4": self.L4_hash, "L5": self.L5_hash,
            },
        }


def _strip_diac(s: str) -> str:
    from wazn_data import DIACRITICS  # type: ignore
    return "".join(c for c in (s or "") if c not in DIACRITICS)


def _neighbor_signature(neighbor) -> str:
    """Compact signature for a previous/next token (or 'START'/'END')."""
    if neighbor is None:
        return "BOUNDARY"
    wc = neighbor.word_class or "?"
    kind = neighbor.closed_class_kind
    surf = neighbor.token
    if wc == "HARF" and kind:
        return f"{wc}[{kind}:{surf}]"
    return f"{wc}[{surf}]"


def compute_coordinate(token, *, prev=None, next_tok=None) -> FractalCoordinate:
    """Compute the 6-level fractal coordinate for a TokenI3rab.

    ``token`` must be a TokenI3rab already populated by Layers 1/2/3.
    ``prev`` and ``next_tok`` are the adjacent TokenI3rab (or None at
    sentence boundaries).
    """
    # === L0 — Carrier ===
    plain = _strip_diac(token.token)
    L0 = f"{token.token}|{plain}"

    # === L1 — Internal structure ===
    # Note: prefixes/stem/suffixes live elsewhere (in segmentation).
    # If TokenI3rab carries them, use them; else derive lightly.
    prefixes = getattr(token, "prefixes", None) or ""
    if isinstance(prefixes, list):
        prefixes = "+".join(prefixes) if prefixes else "∅"
    stem = getattr(token, "stem", "") or "?"
    suffixes = getattr(token, "suffixes", None) or ""
    if isinstance(suffixes, list):
        suffixes = "+".join(suffixes) if suffixes else "∅"
    if not prefixes:
        prefixes = "∅"
    if not suffixes:
        suffixes = "∅"
    L1 = f"{prefixes}|{stem}|{suffixes}"

    # === L2 — Morphology ===
    wc = token.word_class or "?"
    root = token.root or "∅"
    wazn = token.wazn or "∅"
    aspect = token.verb_aspect or ""
    cc_kind = token.closed_class_kind or ""
    L2_parts = [wc, root, wazn]
    if aspect:
        L2_parts.append(f"asp:{aspect}")
    if cc_kind:
        L2_parts.append(f"cc:{cc_kind}")
    L2 = "·".join(L2_parts)

    # === L3 — Syntax ===
    case = f"c{token.case_id}" if token.case_id else "c0"
    mark = f"m{token.mark_id}" if token.mark_id else "m0"
    role = token.role_phrase or "∅"
    L3 = f"{case}·{mark}·{role}"

    # === L4 — Neighbors ===
    prev_sig = _neighbor_signature(prev) if prev else "START"
    next_sig = _neighbor_signature(next_tok) if next_tok else "END"
    L4 = f"{prev_sig} → • → {next_sig}"

    # === L5 — Contracts ===
    wc_c = token.wordclass_contract or "∅"
    case_c = token.case_contract or "∅"
    role_c = token.role_contract or "∅"
    blockers_all = (
        list(token.wordclass_blockers)
        + list(token.case_blockers)
        + list(token.role_blockers)
    )
    blk = ",".join(blockers_all) if blockers_all else "∅"
    L5 = f"wc:{wc_c}·case:{case_c}·role:{role_c}·blk:{blk}"

    return FractalCoordinate(
        L0_carrier=L0,
        L1_internal=L1,
        L2_morphology=L2,
        L3_syntax=L3,
        L4_neighbors=L4,
        L5_contracts=L5,
        L0_hash=_hash6(L0),
        L1_hash=_hash6(L1),
        L2_hash=_hash6(L2),
        L3_hash=_hash6(L3),
        L4_hash=_hash6(L4),
        L5_hash=_hash6(L5),
    )


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    import sys
    from pathlib import Path
    _HERE = Path(__file__).resolve().parent
    sys.path.insert(0, str(_HERE))
    from i3rab_engine import I3rabEngine
    from i3rab_engine.types import TokenI3rab

    e = I3rabEngine()
    s = e.analyze_sentence("كَتَبَ الطَّالِبُ دَرْسًا فِي الْكِتَابِ")
    print("Sentence:", s.text)
    print()
    for i, t in enumerate(s.tokens):
        prev = s.tokens[i - 1] if i > 0 else None
        nxt = s.tokens[i + 1] if i + 1 < len(s.tokens) else None
        coord = compute_coordinate(t, prev=prev, next_tok=nxt)
        print(f"{t.token}:")
        print(f"  hash: {coord.hash_dotted}")
        print(f"  L2:   {coord.L2_morphology}")
        print(f"  L3:   {coord.L3_syntax}")
        print(f"  L4:   {coord.L4_neighbors}")
        print(f"  L5:   {coord.L5_contracts[:80]}...")
        print()
