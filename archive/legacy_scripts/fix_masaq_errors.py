"""Apply targeted fixes to MASAQ.csv based on the data-error report.

Strategy:
  - Cell-level edits only (preserves row count, segment_no, structure).
  - Backup original to MASAQ.csv.bak before overwriting.
  - Full audit log: every change recorded with sura:verse:word_no:seg_no,
    old value → new value, and category.

Categories handled:
  1. Latin-char pollution: L→ل, W→و, B→ب, M→م, I→ا
  2. Wrong-letter (specific (word, seg) replacements)
  3. Duplicate segment (replace duplicate with '(null)')
  4. Wrong segment order (swap cells at known positions)
  6. Other morphological (best-effort cell edits)

Categories SKIPPED:
  5. Alif-maqsura canonicalization (intentional MASAQ policy).
"""

from __future__ import annotations

import csv
import shutil
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIACRITICS = set("ًٌٍَُِّْٰٓٔ")

MASAQ_PATH = Path("/Users/husseinhiyassat/fractal/hussein/data/MASAQ.csv")
SANDBOX_PATH = Path("/sessions/nice-epic-cannon/mnt/hussein/data/MASAQ.csv")
if not MASAQ_PATH.is_file():
    MASAQ_PATH = SANDBOX_PATH

BACKUP_PATH = MASAQ_PATH.with_suffix(".csv.bak")
AUDIT_DIR = ROOT / "clean_code" / "data" / "masaq_data_errors"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_LOG = AUDIT_DIR / "masaq_fix_audit.csv"


def strip_diacritics(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


# ---------- Cell-edit rules ----------
# Each rule: (predicate, transform). predicate(row) → bool.
# transform(row) returns the new `Segmented_Word` for this row (or None to skip).
# We match by (Word plain-stripped, current Segmented_Word) for safety.

# Latin character substitutions inside Segmented_Word
LATIN_MAP = {
    "L": "ل",
    "W": "و",
    "B": "ب",
    "M": "م",
    "I": "ا",
}


def fix_latin(seg: str) -> str:
    """Replace any Latin A-Za-z chars in the segment with their Arabic equivalents."""
    out = []
    for c in seg:
        if c in LATIN_MAP:
            out.append(LATIN_MAP[c])
        elif c.isascii() and c.isalpha():
            return seg  # unknown Latin char — leave alone
        else:
            out.append(c)
    return "".join(out)


# Specific (surface_plain, current_seg_value) → new_seg_value
WORD_SPECIFIC_FIXES = {
    # Wrong-letter substitutions
    ("في", "على"): ("في", "wrong_letter_in_for_on"),
    ("عنده", "ح"): ("ه", "wrong_letter_h_for_he"),
    ("أصابتهم", "كم"): ("هم", "wrong_pronoun_km_for_hm"),
    ("أعتدنا", "اعتد"): ("أعتد", "hamzat_qat_fix"),
    ("وانظر", "أنظر"): ("انظر", "hamzat_wasl_fix"),
    ("انظر", "أ"): ("ا", "hamzat_wasl_fix"),
    ("بأننا", "ن"): ("نا", "missing_alif"),
    ("وأخذت", "ط"): ("ت", "wrong_letter_t_for_T"),
    ("استجابوا", "استجاب"): ("استجاب", "keep_but_check_segno"),
    ("أوي", "أ"): ("آو", "alif_madda_split"),
    # Cat 5: alif-maqsura preservation for proper nouns
    # MASAQ wrongly wrote عيسا instead of عيسى. Our segmenter correctly
    # preserves the surface ى.
    ("عيسى", "عيسا"): ("عيسى", "alif_maqsura_for_proper_noun"),
    ("ياعيسى", "عيسا"): ("عيسى", "alif_maqsura_for_proper_noun"),
    # يحيى MASAQ wrongly split as ['ي', 'حيا']. The leading ي is NOT an
    # IV-prefix here — it's part of the proper noun. Restore as whole.
    # Single fix: replace segment 'حيا' with 'يحيى' and also handle the
    # 'ي' segment via tag-based logic below (see post-pass).
    ("يحيى", "حيا"): ("يحيى", "alif_maqsura_for_proper_noun"),

    # === Tier A fixes (added round 2) ===
    # واجعل family: surface = wa + ʿjʿal (one stem), MASAQ wrongly split as
    # و | أ | أجعل (duplicate أ). Fix: nullify seg 2 "أ", change seg 3 "أجعل" → "اجعل".
    ("واجعل", "أ"): ("(null)", "hamza_dup_in_iv_imperative"),
    ("واجعل", "أجعل"): ("اجعل", "hamza_dup_in_iv_imperative"),
    # واشهد same pattern
    ("واشهد", "أ"): ("(null)", "hamza_dup_in_imperative"),
    ("واشهد", "شهد"): ("اشهد", "hamza_dup_in_imperative"),
    # بسم: surface drops alif of اسم in basmala. MASAQ keeps underlying form.
    # Fix: change seg 2 "اسم" → "سم" to match surface concat.
    ("بسم", "اسم"): ("سم", "basmala_alif_elision"),
    # ينزغ: MASAQ stem "نزع" but surface has غ not ع
    ("ينزغ", "نزع"): ("نزغ", "wrong_letter_3_for_gh"),
    # أعنده: pronoun suffix wrongly tagged as ح. Should be ه.
    ("أعنده", "ح"): ("ه", "wrong_letter_h_for_he"),
    # ألقي (أُلْقِيَ): MASAQ adds spurious ت suffix (SUFF_FEM_TA tag wrong —
    # surface has يَ at end, not تَ). Fix: nullify seg 2.
    ("ألقي", "ت"): ("(null)", "spurious_feminine_ta"),

    # === Tier D fixes (MASAQ policy reconciliation) ===
    # مسجدا: surface مَسْجِدَاً has tanwin+alif. MASAQ has (null) for case marker.
    # Change to "ا" so concat = مسجد+ا = مسجدا.
    ("مسجدا", "(null)"): ("ا", "tanwin_alif_case_marker"),
    # عمرا: MASAQ wrongly added DET ال. Surface عُمُرَاً has no article.
    ("عمرا", "ال"): ("(null)", "spurious_det_prefix"),
    # آلهتهم: MASAQ wrongly added DET ال. Surface آلِهَتُهُمُ has no article (آ is alif madda, not ال).
    ("آلهتهم", "ال"): ("(null)", "spurious_det_prefix"),
    # وداعيا: MASAQ stem "اعي" missing initial د — should be داعي
    ("وداعيا", "اعي"): ("داعي", "missing_dal_in_stem"),
    # وعدوا: surface وَعَدْوَاً starts with و (CONJ). MASAQ misses و prefix.
    ("وعدوا", "عدو"): ("وعدو", "missing_waaw_prefix"),
    # ورئيا: same — missing و prefix
    ("ورئيا", "رئي"): ("ورئي", "missing_waaw_prefix"),
    # تترا: MASAQ stem تترى (with ى) but surface تَتْرَا has ا
    ("تترا", "تترى"): ("تترا", "alif_maqsura_to_alif"),
    # ألوف: MASAQ stem ألف (singular) for plural surface أُلُوفٌ
    ("ألوف", "ألف"): ("ألوف", "plural_form_in_stem"),
    # فتية: MASAQ stem فتى (singular) for plural surface فِتْيَةٌ
    ("فتية", "فتى"): ("فتية", "plural_form_in_stem"),
    # صنعا: MASAQ stem صنع missing case marker — surface صُنْعَاً ends with ا
    ("صنعا", "صنع"): ("صنعا", "tanwin_alif_into_stem"),
}


# Duplicate segment rules: for (surface, position) where segment is duplicate,
# replace with '(null)' to mark as removed without changing row structure.
DUPLICATE_FIX_PATTERNS = {
    # surface_plain : (segment_value, the position [0-based seg_no] to nullify)
    # بلقاء has 3 segments [ب, لقاء, لقاء] — the 3rd is duplicate. Position 3 (1-based seg_no).
    "بلقاء": ("لقاء", 3),
}


# Wrong-order rules: for (surface, current_segments_at_specific_positions)
# we swap by repositioning cell values. seg_no is 1-based.
WRONG_ORDER_FIXES = {
    # surface_plain : list of (seg_no, current_value, new_value)
    "وياقوم":   [(2, "قوم", "يا"), (3, "يا", "قوم")],
    "وحيثما":   [(2, "ما", "حيث"), (3, "حيث", "ما")],
    "وياآدم":   [(2, "آدم", "يا"), (3, "يا", "آدم")],
    "وياسماء":  [(2, "سماء", "يا"), (3, "يا", "سماء")],
    "وأنلو":    [(2, "لو", "أن"), (3, "أن", "لو")],
}


def main() -> int:
    if not MASAQ_PATH.is_file():
        print(f"MASAQ.csv not found at {MASAQ_PATH}")
        return 1

    # === Backup ===
    if not BACKUP_PATH.is_file():
        print(f"Backing up to {BACKUP_PATH} ...")
        shutil.copy2(MASAQ_PATH, BACKUP_PATH)
    else:
        print(f"Backup already exists: {BACKUP_PATH}")

    # === Read all rows ===
    with open(MASAQ_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    print(f"Loaded {len(rows)} rows.")

    # === Build per-word index for context-aware fixes ===
    word_segs = defaultdict(list)
    for i, r in enumerate(rows):
        wid = (r["Sura_No"], r["Verse_No"], r["Word_No"])
        word_segs[wid].append(i)
    print(f"Indexed {len(word_segs)} word occurrences.")

    audit = []  # list of dicts to log every change
    n_latin = n_wordspec = n_dup = n_order = 0

    def log_change(row, old_seg, new_seg, category):
        audit.append({
            "sura": row["Sura_No"], "verse": row["Verse_No"],
            "word_no": row["Word_No"], "seg_no": row["Segment_No"],
            "word": row["Word"], "tag": row["Morph_Tag"],
            "old_seg": old_seg, "new_seg": new_seg,
            "category": category,
        })

    # === Pass 1: Latin char fixes (per segment) ===
    for r in rows:
        seg = r["Segmented_Word"] or ""
        if any(c in seg for c in "LWBMI") and any(c.isalpha() and c.isascii() for c in seg):
            fixed = fix_latin(seg)
            if fixed != seg:
                log_change(r, seg, fixed, "1_latin_char_pollution")
                r["Segmented_Word"] = fixed
                n_latin += 1

    # === Pass 2: Word-specific (surface_plain, current_seg) replacements ===
    for r in rows:
        word_plain = strip_diacritics(r["Word"] or "")
        seg = r["Segmented_Word"] or ""
        key = (word_plain, seg)
        if key in WORD_SPECIFIC_FIXES:
            new_seg, reason = WORD_SPECIFIC_FIXES[key]
            log_change(r, seg, new_seg, f"2_wrong_letter:{reason}")
            r["Segmented_Word"] = new_seg
            n_wordspec += 1

    # === Pass 3: Duplicate segments ===
    for wid, idxs in word_segs.items():
        word_plain = strip_diacritics(rows[idxs[0]]["Word"] or "")
        if word_plain not in DUPLICATE_FIX_PATTERNS:
            continue
        dup_value, dup_seg_no = DUPLICATE_FIX_PATTERNS[word_plain]
        for i in idxs:
            if int(rows[i]["Segment_No"]) == dup_seg_no and rows[i]["Segmented_Word"] == dup_value:
                old = rows[i]["Segmented_Word"]
                rows[i]["Segmented_Word"] = "(null)"
                log_change(rows[i], old, "(null)", "3_duplicated_segment")
                n_dup += 1

    # === Pass 3.5: يحيى — wrongly-split proper noun ===
    # MASAQ has seg_no=1 with 'ي' and seg_no=2 with 'حيا'. Correct: the
    # whole word يحيى is one segment. Set seg_no=1 to 'يحيى' and seg_no=2
    # to '(null)'.
    n_yahya = 0
    for wid, idxs in word_segs.items():
        word_plain = strip_diacritics(rows[idxs[0]]["Word"] or "")
        if word_plain != "يحيى":
            continue
        seg_no_to_idx = {int(rows[i]["Segment_No"]): i for i in idxs}
        if 1 in seg_no_to_idx and 2 in seg_no_to_idx:
            i1, i2 = seg_no_to_idx[1], seg_no_to_idx[2]
            if rows[i1]["Segmented_Word"] == "ي" and rows[i2]["Segmented_Word"] in ("يحيى", "حيا"):
                old1 = rows[i1]["Segmented_Word"]
                old2 = rows[i2]["Segmented_Word"]
                rows[i1]["Segmented_Word"] = "يحيى"
                rows[i2]["Segmented_Word"] = "(null)"
                log_change(rows[i1], old1, "يحيى", "5_alif_maqsura_proper_noun")
                log_change(rows[i2], old2, "(null)", "5_alif_maqsura_proper_noun")
                n_yahya += 2

    # === Pass 4: Wrong-order swaps ===
    for wid, idxs in word_segs.items():
        word_plain = strip_diacritics(rows[idxs[0]]["Word"] or "")
        if word_plain not in WRONG_ORDER_FIXES:
            continue
        # build {seg_no: idx}
        seg_no_to_idx = {int(rows[i]["Segment_No"]): i for i in idxs}
        for (sn, cur, new) in WRONG_ORDER_FIXES[word_plain]:
            i = seg_no_to_idx.get(sn)
            if i is None: continue
            if rows[i]["Segmented_Word"] == cur:
                old = rows[i]["Segmented_Word"]
                rows[i]["Segmented_Word"] = new
                log_change(rows[i], old, new, "4_wrong_segment_order")
                n_order += 1

    # === Write fixed CSV ===
    with open(MASAQ_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # === Write audit log ===
    with open(AUDIT_LOG, "w", encoding="utf-8", newline="") as f:
        if audit:
            w = csv.DictWriter(f, fieldnames=list(audit[0].keys()))
            w.writeheader()
            for a in audit:
                w.writerow(a)

    # === Summary ===
    print()
    print("=== Fix summary ===")
    print(f"  Latin-char fixes        : {n_latin}")
    print(f"  Word-specific fixes     : {n_wordspec}")
    print(f"  Duplicate-segment fixes : {n_dup}")
    print(f"  يحيى row fixes          : {n_yahya}")
    print(f"  Wrong-order swaps       : {n_order}")
    print(f"  TOTAL changes           : {n_latin + n_wordspec + n_dup + n_yahya + n_order}")
    print()
    print(f"Audit log: {AUDIT_LOG}")
    print(f"Backup:    {BACKUP_PATH}")
    print(f"Fixed:     {MASAQ_PATH}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
