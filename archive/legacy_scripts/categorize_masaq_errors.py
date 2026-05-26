"""Categorize MASAQ data errors found by find_masaq_data_errors.py.

Outputs a categorized report listing each genuine MASAQ tagging error
suitable for upstream bug-report submission.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ERR_DIR = ROOT / "clean_code" / "data" / "masaq_data_errors"
INPUT = ERR_DIR / "masaq_data_errors_by_pattern.csv"
OUTPUT = ERR_DIR / "masaq_errors_categorized.md"


def has_latin(s: str) -> bool:
    return bool(re.search(r"[A-Za-z]", s))


def categorize(surface: str, segments: str) -> str:
    """Return a category label for this error."""
    if has_latin(segments):
        return "1_latin_char_pollution"
    # ى/ا canonicalization (MASAQ writes alif maqsura as plain alif)
    if surface.endswith("ى") and segments.endswith("ا"):
        return "5_alif_maqsura_canonicalization"
    if "ى" in surface and segments.replace("ا", "ى") == surface:
        return "5_alif_maqsura_canonicalization"
    # Wrong consonant (different letter entirely, no morpho relationship)
    surface_letters = set(surface)
    seg_letters_combined = "".join(segments.split(" | "))
    seg_letter_set = set(seg_letters_combined)
    # Check if segments introduce letters NOT in surface (could be wrong)
    extra_in_segs = seg_letter_set - surface_letters - {" "}
    if extra_in_segs and not seg_letter_set <= surface_letters:
        # Letters in segments that aren't in surface — suspicious
        return "2_wrong_letter_substitution"
    # Duplicated segments
    seg_parts = segments.split(" | ")
    if len(seg_parts) != len(set(seg_parts)):
        return "3_duplicated_segment"
    # Wrong segment order
    surface_no_space = surface.replace(" ", "")
    if "".join(seg_parts) != surface_no_space:
        # Re-arrange segments and compare
        from itertools import permutations
        if len(seg_parts) <= 4:
            for perm in permutations(seg_parts):
                if "".join(perm) == surface_no_space:
                    return "4_wrong_segment_order"
    return "6_other_morphological_difference"


def main() -> int:
    if not INPUT.is_file():
        print(f"Run find_masaq_data_errors.py first — {INPUT} not found")
        return 1
    rows = []
    with open(INPUT, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)

    by_category = defaultdict(list)
    total = 0
    for row in rows:
        count = int(row["count"])
        cat = categorize(row["surface_word"], row["MASAQ_segments"])
        by_category[cat].append(row)
        total += count

    # Write categorized markdown report
    category_names = {
        "1_latin_char_pollution":
            "1. Latin-character pollution (encoding artifact)",
        "2_wrong_letter_substitution":
            "2. Wrong-letter substitution (consonant differs)",
        "3_duplicated_segment":
            "3. Duplicated segment",
        "4_wrong_segment_order":
            "4. Wrong segment order",
        "5_alif_maqsura_canonicalization":
            "5. Alif-maqsura canonicalization (ى → ا)",
        "6_other_morphological_difference":
            "6. Other morphological difference",
    }

    print(f"=== MASAQ data errors — categorized ===\n")
    print(f"Total error occurrences: {total} across {sum(len(v) for v in by_category.values())} distinct patterns")
    print()

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("# MASAQ.csv Data Quality Issues — Report for Upstream\n\n")
        f.write(f"Source file: `MASAQ.csv` (17,619 unique words; 77,411 occurrences)\n\n")
        f.write(f"**Methodology:** for each word occurrence in MASAQ, the script "
                "concatenates its `Segmented_Word` values, applies standard "
                "Arabic morphological transformations (diacritic strip, "
                "ى↔ي, ة↔ت, ٱ↔ا, hamza variants, alif madda decomposition, "
                "shadda gemination, nun-meem idgham, lam-alif elision), then "
                "compares to the surface `Word`. Mismatches after all these "
                "transformations are MASAQ tagging errors.\n\n")
        f.write(f"**Total issues found:** {total} word occurrences across "
                f"{sum(len(v) for v in by_category.values())} distinct patterns.\n\n")
        f.write("---\n\n")
        for cat_key in sorted(by_category.keys()):
            cat_label = category_names.get(cat_key, cat_key)
            cat_rows = by_category[cat_key]
            cat_total = sum(int(r["count"]) for r in cat_rows)
            print(f"\n--- {cat_label} ({cat_total} occurrences, {len(cat_rows)} patterns) ---")
            f.write(f"## {cat_label}\n\n")
            f.write(f"**{cat_total} occurrences across {len(cat_rows)} patterns.**\n\n")
            f.write("| Count | Surface (Word) | MASAQ Segmented_Word | Sample locations |\n")
            f.write("|---:|---|---|---|\n")
            for r in sorted(cat_rows, key=lambda x: -int(x["count"])):
                print(f"  {int(r['count']):>4}  {r['surface_word']:<25} → {r['MASAQ_segments']:<35}  [{r.get('sample_locations', '')[:60]}]")
                f.write(f"| {r['count']} | `{r['surface_word']}` | `{r['MASAQ_segments']}` | {r.get('sample_locations','')} |\n")
            f.write("\n")
        f.write("\n---\n\n")
        f.write("## Notes\n\n")
        f.write("- Category 1 (Latin pollution) is almost certainly a "
                "processing/encoding step that mis-substituted Arabic "
                "letters with their visually-similar Latin equivalents "
                "(L↔ل, W↔و, B↔ب, M↔م, I↔ا).\n")
        f.write("- Category 2 cases (e.g., فِي → على, عنده → عند+ح) are "
                "categorically wrong — the segments contain letters that "
                "cannot derive the surface form.\n")
        f.write("- Category 5 (ى → ا canonicalization) may be intentional "
                "MASAQ policy. Listed for review.\n")

    print(f"\n=== Output ===")
    print(f"  {OUTPUT}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
