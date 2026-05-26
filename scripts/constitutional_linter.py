#!/usr/bin/env python3
"""constitutional_linter.py — حارس Minimum Complete.

يَفحص clean_code/ ويُحَذِّر من المُخالفات الشَّائعة:

1. **inline string sets** — `{"x", "y", "z"}` بلا comment يُحيل لعقد
2. **inline translation dicts** — قواميس فيها قيم عربيّة (يجب أن تكون CSV)
3. **inline lexical lists** — `if word == "..."` بلا contract
4. **hash as source-of-claim** — أيّ كلمة تَحتوي "sha256" أو "hash" في
   source field يُمَرَّر كادّعاء

يَطبع تقريرًا (لا يُغيّر شيئًا) ويَعود بـ exit code:
  0 — لا مُخالفات
  1 — مُخالفات وُجدت

استعمال:
  python3 scripts/constitutional_linter.py
  python3 scripts/constitutional_linter.py --strict   (يُغيّر warnings إلى errors)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN_CODE = ROOT / "clean_code"

# ============================================================================
# Detection rules
# ============================================================================

# Set literals with Arabic strings — likely inline override
RE_INLINE_ARABIC_SET = re.compile(
    r'\{[^}]*"[؀-ۿ][^"]*"[^}]*\}',
    re.MULTILINE,
)

# Dict literals with Arabic values
RE_INLINE_ARABIC_DICT = re.compile(
    r'^\s*_AR_[A-Z_]+\s*=\s*\{',
    re.MULTILINE,
)

# Hash as source pattern
RE_HASH_AS_SOURCE = re.compile(
    r'(source|contract)["\s]*[=:]["\s]*[\'"]?\s*(sha256|hash|fingerprint)',
    re.IGNORECASE,
)

# Hardcoded Arabic word equality checks
RE_INLINE_WORD_CHECK = re.compile(
    r'\bword\s*(==|!=|in)\s*[\'"](?:[؀-ۿ]|\\u06)[^\'\"]+[\'"]',
)


# Files that are ALLOWED to contain inline data (the data files themselves
# don't apply, and explicit fallbacks marked as such are OK).
EXEMPT_FILES = {
    "i3rab_engine/types.py",        # MARK_IDS dict is the canonical mark table
    "contracts_loader.py",          # the loader itself
    "old_nand_coordinate.py",       # archived experiment
    "wazn_data.py",                 # canonical data loaders + necessary tags
}

# Substrings that mark a line as exempt from a specific check
EXEMPT_LINE_MARKERS = (
    "# canonical",           # explicitly canonical data
    "# constitutional",      # constitutional necessity
    "# linter:skip",         # explicit skip
    "EXEMPT_",               # this file's own constants
)


# ============================================================================
# Violation report
# ============================================================================

class Violation:
    def __init__(self, file: Path, line: int, rule: str, snippet: str):
        self.file = file
        self.line = line
        self.rule = rule
        self.snippet = snippet[:80]

    def __str__(self) -> str:
        rel = self.file.relative_to(ROOT)
        return f"  {rel}:{self.line}  [{self.rule}]  {self.snippet}"


def scan_file(path: Path) -> list[Violation]:
    rel = path.relative_to(CLEAN_CODE).as_posix() if str(path).startswith(str(CLEAN_CODE)) else path.name
    if rel in EXEMPT_FILES:
        return []
    if path.name.startswith("test_") or path.name.startswith("_"):
        return []

    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    lines = text.splitlines()
    violations: list[Violation] = []

    for i, line in enumerate(lines, start=1):
        # Skip exempt lines
        if any(m in line for m in EXEMPT_LINE_MARKERS):
            continue

        # Rule 1: inline Arabic string set
        if RE_INLINE_ARABIC_SET.search(line):
            violations.append(Violation(
                path, i, "inline_arabic_set", line.strip()
            ))
            continue

        # Rule 2: inline translation dict
        if RE_INLINE_ARABIC_DICT.search(line):
            violations.append(Violation(
                path, i, "inline_translation_dict",
                line.strip()
            ))
            continue

        # Rule 3: hash as source-of-claim
        if RE_HASH_AS_SOURCE.search(line):
            violations.append(Violation(
                path, i, "hash_as_source_of_claim",
                line.strip()
            ))
            continue

        # Rule 4: inline word equality
        if RE_INLINE_WORD_CHECK.search(line):
            violations.append(Violation(
                path, i, "inline_word_check",
                line.strip()
            ))
            continue

    return violations


def scan_tree() -> list[Violation]:
    out: list[Violation] = []
    for path in CLEAN_CODE.rglob("*.py"):
        # Skip __pycache__
        if "__pycache__" in path.parts:
            continue
        # Skip archive
        if "archive" in path.parts or "old_nand" in path.parts:
            continue
        out.extend(scan_file(path))
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--strict", action="store_true",
                   help="non-zero exit even on warnings")
    args = p.parse_args()

    violations = scan_tree()

    if not violations:
        print("✓ لا مُخالفات للحد الأدنى المكتمل.")
        return 0

    # Group by rule
    by_rule: dict[str, list[Violation]] = {}
    for v in violations:
        by_rule.setdefault(v.rule, []).append(v)

    print(f"وُجِدت {len(violations)} مُخالفة في {len({v.file for v in violations})} ملف:")
    print()
    for rule, vs in sorted(by_rule.items()):
        print(f"─── [{rule}]  {len(vs)} مُخالفة ───")
        for v in vs[:10]:
            print(v)
        if len(vs) > 10:
            print(f"  ... و{len(vs) - 10} أخرى")
        print()

    print("لِلحصول على Minimum Complete، انقل المُخالفات إلى:")
    print("  - قوائم الحروف/الكلمات → clean_code/data/contracts/")
    print("  - قواميس الترجمة         → clean_code/data/contracts/translations/")
    print("  - قواعد لسانيّة         → clean_code/data/contracts/rules/")
    print("  - استثني الـ canonical    → ضع '# canonical' في السطر")

    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
