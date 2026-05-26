"""Find MASAQ tagging errors where the segmentation cannot produce the
surface word (i.e., the tagged segments don't morphologically combine
to form the actual Word). These are MASAQ-origin errors, not segmenter
errors — useful for reporting upstream.

Detection method:
  1. Read each row's Word (surface) and the row's Segmented_Word.
  2. Aggregate all segments per word occurrence.
  3. Concatenate segments (after handling "(null)" and known
     morphological transforms: ـة↔ـت, alif maqsura↔ya, shadda gemination,
     hamzat wasl elision, article assimilation).
  4. Compare normalized concatenation to normalized surface.
  5. Flag mismatches as MASAQ data errors.

Output: masaq_data_errors.csv listing every flagged word occurrence.
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_MASAQ_CANDIDATES = [
    Path("/Users/husseinhiyassat/fractal/hussein/data/MASAQ.csv"),
    Path("/Users/husseinhiyassat/fractal/new_arabic_analyzer/data/MASAQ.csv"),
    Path("/sessions/nice-epic-cannon/mnt/hussein/data/MASAQ.csv"),
    Path("/sessions/nice-epic-cannon/mnt/new_arabic_analyzer/data/MASAQ.csv"),
]
MASAQ_CSV = next((p for p in _MASAQ_CANDIDATES if p.is_file()), None)
OUT_DIR = ROOT / "clean_code" / "data" / "masaq_data_errors"

DIACRITICS = set("ًٌٍَُِّْٰٓٔ")
ARABIC_LETTERS = set("ابتثجحخدذرزسشصضطظعغفقكلمنهويءأإؤئآى")


def strip_diacritics(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def normalize_for_compare(s: str) -> str:
    """Normalize an Arabic string for permissive comparison.
    Handles standard morphological transformations so legitimate variation
    (shadda gemination, lam elision, idgham, taa↔ة) doesn't flag as error.
    """
    out = strip_diacritics(s)
    # Hollow-verb morphophonology: stem-final ى/ي drops before و/ا suffix.
    #   ترضى + ون → ترضون (not ترضىون)
    #   تخشى + و + ه → تخشوه
    #   نهي + ون → نهون
    # Apply BEFORE ى→ي. The ي variants apply only before specific suffix
    # patterns to avoid corrupting non-verb words like بيوت/يوسف.
    out = out.replace("ىو", "و")
    out = out.replace("ىا", "ا")
    out = out.replace("ى", "ي")           # alif maqsura → ya (remaining)
    # ي drops before و-suffix (و, ون, وا, وه): only safe before specific patterns.
    import re as _re
    out = _re.sub(r"يون(?=[^ا-ي]|$)", "ون", out)   # ـيون at end-cluster
    out = _re.sub(r"يوا(?=[^ا-ي]|$)", "وا", out)
    out = _re.sub(r"يوه(?=[^ا-ي]|$)", "وه", out)
    out = _re.sub(r"يو$", "و", out)
    out = out.replace("ة", "ت")            # taa marbuta → open ta
    out = out.replace("ٱ", "ا")            # alif wasla → bare alif
    out = out.replace("آ", "اا")          # alif madda → double alif
    for h in ("أ", "إ", "ؤ", "ئ"):
        out = out.replace(h, "ء")           # any hamza variant → ء
    return out


def collapse_doubles(s: str) -> str:
    """Collapse consecutive identical letters into one — handles shadda
    gemination (إنّا = إن + نا → surface 'إنا') and idgham assimilation.
    """
    if not s:
        return s
    out = [s[0]]
    for c in s[1:]:
        if c != out[-1]:
            out.append(c)
    return "".join(out)


def idgham_normalize(s: str) -> str:
    """Apply Arabic idgham assimilation patterns:
       نم → مم  (nun before meem → both meem)
       نل → لل
       نر → رر
       نو → وو
       ني → يي
    """
    rules = [("نم", "مم"), ("نل", "لل"), ("نر", "رر"),
             ("نو", "وو"), ("ني", "يي"), ("نن", "نن")]
    for src, dst in rules:
        s = s.replace(src, dst)
    return s


def aggressive_normalize(s: str) -> str:
    """Final aggressive normalization for surface-vs-segments comparison."""
    out = normalize_for_compare(s)
    # Alif elision: prep lam + article alif → surface drops the alif
    #   "لال" (segments) ↔ "لل" (surface)
    out = out.replace("لال", "لل")
    # Interrogative أ + article ال → آ (alif madda) in surface, but split as
    # أ | ال in MASAQ segments. Both represent same morphology — drop the
    # initial hamza-ء before alif so they normalize identically.
    if out.startswith("ءا"):
        out = "ا" + out[2:]
    # Apply idgham (نم → مم etc.) and collapse consecutive duplicates
    out = idgham_normalize(out)
    out = collapse_doubles(out)
    return out


def clean_seg(s: str) -> str:
    """Clean a single segment value from MASAQ."""
    if s in ("(null)", "None", "null", "", None):
        return ""
    return s


def concat_segments(segs: list[str]) -> str:
    """Concatenate all segments, dropping null markers."""
    return "".join(s for s in segs if clean_seg(s))


def main() -> int:
    if MASAQ_CSV is None or not MASAQ_CSV.is_file():
        print("MASAQ.csv not found")
        return 1
    print(f"Reading {MASAQ_CSV}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    word_segs = defaultdict(list)
    with open(MASAQ_CSV, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            wid = (row["Sura_No"], row["Verse_No"], row["Word_No"])
            word_segs[wid].append({
                "seg_no": int(row["Segment_No"]),
                "word": row["Word"],
                "seg": row["Segmented_Word"],
                "tag": row["Morph_Tag"],
            })

    errors = []
    by_pattern = Counter()
    examples_by_pattern = defaultdict(list)

    total_words = 0
    for wid, parts in word_segs.items():
        # IMPORTANT: do NOT sort by seg_no. MASAQ uses duplicate seg_no values
        # within a single Word_No for compound structures (e.g., يا + noun
        # vocative, where MASAQ writes two rows of seg_no=1 and two of
        # seg_no=2). Physical row order is the authoritative segment order.
        word = parts[0]["word"]
        if not word or not any(c in ARABIC_LETTERS for c in strip_diacritics(word)):
            continue
        total_words += 1
        segs = [p["seg"] for p in parts]
        tags = [p["tag"] for p in parts]

        # Concatenate segments
        seg_concat = concat_segments(segs)
        # Aggressively normalize both (handles shadda gemination, idgham,
        # ى↔ي, ة↔ت, alif madda, hamza variants)
        norm_surface = aggressive_normalize(word)
        norm_segs = aggressive_normalize(seg_concat)

        # If they STILL don't match after handling all standard morphology,
        # it's a real MASAQ data error.
        if norm_surface != norm_segs:
            # Pattern key: (surface_plain, segs_plain)
            surf_plain = strip_diacritics(word)
            segs_plain = " | ".join(strip_diacritics(s) for s in segs if clean_seg(s))
            pattern_key = (surf_plain, segs_plain)
            by_pattern[pattern_key] += 1
            if len(examples_by_pattern[pattern_key]) < 5:
                examples_by_pattern[pattern_key].append(
                    f"{wid[0]}:{wid[1]}:{wid[2]}"
                )
            errors.append({
                "sura": wid[0],
                "verse": wid[1],
                "word_no": wid[2],
                "word": word,
                "word_plain": surf_plain,
                "segments_raw": " | ".join(segs),
                "segments_plain": segs_plain,
                "tags": " | ".join(tags),
                "norm_surface": norm_surface,
                "norm_segs": norm_segs,
            })

    # Sort by pattern frequency
    sorted_patterns = by_pattern.most_common()

    # Write full error list
    full_path = OUT_DIR / "masaq_data_errors_full.csv"
    with open(full_path, "w", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "sura", "verse", "word_no", "word", "word_plain",
            "segments_raw", "segments_plain", "tags",
            "norm_surface", "norm_segs",
        ])
        w.writeheader()
        for e in errors:
            w.writerow(e)

    # Write pattern summary
    pattern_path = OUT_DIR / "masaq_data_errors_by_pattern.csv"
    with open(pattern_path, "w", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["count", "surface_word", "MASAQ_segments", "sample_locations"])
        for (surf, segs), count in sorted_patterns:
            samples = " ; ".join(examples_by_pattern[(surf, segs)][:5])
            w.writerow([count, surf, segs, samples])

    print(f"=== MASAQ data error detection ===")
    print(f"Total words checked:         {total_words}")
    print(f"Words with concat mismatch:  {len(errors)} ({100 * len(errors) / total_words:.2f}%)")
    print(f"Distinct mismatch patterns:  {len(by_pattern)}")
    print()
    print(f"=== Top 40 mismatch patterns ===")
    print(f"{'count':>6}  {'surface':<25} → MASAQ segments")
    print("  " + "-" * 70)
    for (surf, segs), count in sorted_patterns[:40]:
        print(f"  {count:>4}  {surf:<25} → {segs}")
    print()
    print(f"=== Output files ===")
    print(f"  Full list:    {full_path}")
    print(f"  By pattern:   {pattern_path}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
