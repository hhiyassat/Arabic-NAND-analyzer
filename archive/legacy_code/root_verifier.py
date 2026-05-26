"""root_verifier.py — Verify extracted roots against reference databases.

PHILOSOPHY:
  This module DOES NOT extract roots. It only verifies whether a root that
  was produced by root_extractor.py (pure rules) is also attested in known
  reference databases. The references are:
    1. mishkat_word_root.csv         — Quranic word-root corpus
    2. audited_roots.csv             — manually audited (لسان العرب citations)
    3. unified_wazn_database.csv     — wazn/root canonical table

  Verification does NOT change the extracted root. It only annotates it.

CONSTITUTIONAL ROLE:
  - References are consulted as evidence, not as authority
  - A root that fails all references is still kept (with flag)
  - Source-of-Claim: each verification flag has the reference name

API:
  verifier = RootVerifier()
  result = verifier.verify(root)
    Returns VerificationResult with bool flags + counts.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ============================================================================
# Constants
# ============================================================================

DIACRITICS = set("ًٌٍَُِّْٰٓٔ")
HAMZA_VARIANTS = {"أ", "إ", "ؤ", "ئ", "آ", "ٱ"}


def strip_diacritics(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def normalize_root_for_match(root: str) -> str:
    """Strip diacritics + collapse hamza variants to ء for lookup.
    The reference databases store roots in canonical form (e.g. ءكل not أكل).
    """
    if not root:
        return ""
    out = strip_diacritics(root)
    out = "".join("ء" if c in HAMZA_VARIANTS else c for c in out)
    return out


# ============================================================================
# Data structure
# ============================================================================

@dataclass
class VerificationResult:
    root: str                         # the input (as-given)
    root_normalized: str              # after diacritic strip + hamza collapse
    in_mishkat: bool                  # found in Quranic mishkat corpus
    in_audited: bool                  # found in salehan audited_roots
    in_canonical: bool                # found in unified canonical wazn table
    quran_count: int = 0              # frequency in mishkat (Quran)
    audited_verified: bool = False    # audited_roots has تم تدقيقه=1
    reference_sources: list[str] = None  # which DBs found it

    @property
    def is_verified(self) -> bool:
        """True if found in at least one reference."""
        return self.in_mishkat or self.in_audited or self.in_canonical

    @property
    def verification_strength(self) -> str:
        """A label describing how strongly verified."""
        n = sum([self.in_mishkat, self.in_audited, self.in_canonical])
        if n == 0:
            return "unverified"
        if n == 1:
            return "single_reference"
        if n == 2:
            return "double_reference"
        return "triple_reference"


# ============================================================================
# Verifier
# ============================================================================

class RootVerifier:
    """Loads reference databases once and verifies roots against them."""

    def __init__(self, base_path: Optional[Path] = None):
        # Try multiple roots so this works on host AND sandbox
        if base_path is None:
            for candidate in (
                Path("/Users/husseinhiyassat/fractal/hussein"),
                Path("/sessions/nice-epic-cannon/mnt/hussein"),
            ):
                if candidate.is_dir():
                    base_path = candidate
                    break
        self.base_path = base_path

        # Reference set: mishkat (Quran-attested roots + their counts)
        self.mishkat_roots: dict[str, int] = {}    # root → total count
        # Reference set: audited (root → is_audited_true)
        self.audited_roots: dict[str, bool] = {}
        # Reference set: canonical wazn table (just root attestations)
        self.canonical_roots: set[str] = set()

        self._load_mishkat()
        self._load_audited()
        self._load_canonical()

    def _load_mishkat(self):
        """Load mishkat_word_root.csv (root, word, count)."""
        if self.base_path is None:
            return
        path = self.base_path / "clean_code/data/mishkat_word_root.csv"
        if not path.is_file():
            return
        with path.open(encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                root = normalize_root_for_match(row["root"])
                if not root:
                    continue
                try:
                    count = int(row.get("count", 0))
                except (ValueError, TypeError):
                    count = 0
                self.mishkat_roots[root] = self.mishkat_roots.get(root, 0) + count

    def _load_audited(self):
        """Load salehan audited_roots.csv. Each row has 'الجذر' column."""
        if self.base_path is None:
            return
        candidates = [
            self.base_path / "data/audited_roots.csv",
            Path("/sessions/nice-epic-cannon/mnt/salehan/Salehan19-6-67/data/audited_roots.csv"),
            Path("/Users/husseinhiyassat/fractal/salehan/Salehan19-6-67/data/audited_roots.csv"),
        ]
        for path in candidates:
            if path.is_file():
                with path.open(encoding="utf-8") as f:
                    r = csv.DictReader(f)
                    for row in r:
                        # Schema: id, الفعل الماضي, الجذر, ...
                        root_raw = row.get("الجذر") or row.get("root") or ""
                        root = normalize_root_for_match(root_raw)
                        if not root:
                            continue
                        audited = str(row.get("تم تدقيقه", "")).strip() == "1" or \
                                  str(row.get("تم إعادة تدقيقه", "")).strip() == "1"
                        # Keep True if ANY occurrence is audited
                        self.audited_roots[root] = self.audited_roots.get(root, False) or audited
                break

    def _load_canonical(self):
        """Load unified_wazn_database.csv to extract attested roots."""
        if self.base_path is None:
            return
        path = self.base_path / "clean_code/data/unified_wazn_database.csv"
        if not path.is_file():
            return
        with path.open(encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                # The examples field contains "(curated)+ROOT" snippets
                examples = row.get("examples", "")
                for tok in examples.split(" | "):
                    tok = tok.strip()
                    if "+" in tok:
                        root_candidate = tok.split("+")[-1].strip()
                        norm = normalize_root_for_match(root_candidate)
                        if 2 <= len(norm) <= 5:
                            self.canonical_roots.add(norm)

    def verify(self, root: str) -> VerificationResult:
        """Verify a single root against all references."""
        norm = normalize_root_for_match(root)
        in_mishkat = norm in self.mishkat_roots
        in_audited = norm in self.audited_roots
        in_canonical = norm in self.canonical_roots
        sources = []
        if in_mishkat:
            sources.append(f"mishkat:count={self.mishkat_roots[norm]}")
        if in_audited:
            audited_flag = "audited" if self.audited_roots[norm] else "listed"
            sources.append(f"salehan:{audited_flag}")
        if in_canonical:
            sources.append("canonical")
        return VerificationResult(
            root=root,
            root_normalized=norm,
            in_mishkat=in_mishkat,
            in_audited=in_audited,
            in_canonical=in_canonical,
            quran_count=self.mishkat_roots.get(norm, 0),
            audited_verified=self.audited_roots.get(norm, False),
            reference_sources=sources,
        )

    def stats(self) -> dict:
        return {
            "mishkat_roots": len(self.mishkat_roots),
            "audited_roots": len(self.audited_roots),
            "canonical_roots": len(self.canonical_roots),
        }


# ============================================================================
# Self-test
# ============================================================================

def _self_test():
    print("=== root_verifier self-test ===\n")
    v = RootVerifier()
    print(f"Reference DB sizes: {v.stats()}\n")

    test_roots = [
        ("كتب", "well-known root, should be in all"),
        ("ذهب", "common Quranic root"),
        ("علم", "very common"),
        ("xyz", "nonsense — should NOT verify"),
        ("سمو", "اسم's root — should verify"),
    ]
    for root, note in test_roots:
        r = v.verify(root)
        print(f"  verify({root!r}) — {note}")
        print(f"    in_mishkat={r.in_mishkat} (count={r.quran_count}) "
              f"in_audited={r.in_audited} in_canonical={r.in_canonical}")
        print(f"    strength={r.verification_strength}  sources={r.reference_sources}")
        print()


if __name__ == "__main__":
    _self_test()
