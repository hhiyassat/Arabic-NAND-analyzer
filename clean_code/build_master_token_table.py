#!/usr/bin/env python3
"""build_master_token_table.py — يَدمج MASAQ + MEEMAR في جَدول مَرجِعيّ مُوَحَّد.

الإِخراج: data/master_token_table.csv
عَمود واحِد لِكُلّ كَلِمَة فَريدَة في القُرآن (بِالتَّشكيل):
  surface,plain,word_class,lemma,root,aspect,case,role,source,confidence

مَنطِق الـword_class — مَن MASAQ Morph_Tag (Stem segment فَقَط):
  PV / IV / CV / PV_PASS / IV_PASS  →  FIIL
  NOUN_PROP / NOUN_PROP_FOREIGN     →  JAMID (proper noun)
  NOUN_* / ADJ_* / GERUND / NOUN_NUM →  ISM_MUARAB
  REL_PRON / DEM_PRON / PRON / INTERR_PRON → ISM_MABNI
  PREP / CONJ / NEG_PART / ANNUL_PART / ... → HARF

source = "MASAQ:row_id" — كُلّ تَصنيف يَحمِل مَصدَره (MC).
"""
import csv
import sys
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
MASAQ = HERE.parent / "data" / "MASAQ.csv"
MEEMAR = HERE.parent / "data" / "MEEMAR.csv"
OUT = HERE / "data" / "master_token_table.csv"

# ─────────────────────────────────────────────────────────────
# MASAQ → word_class mapping
# ─────────────────────────────────────────────────────────────

VERB_TAGS = {"PV", "IV", "CV", "PV_PASS", "IV_PASS"}
PROPER_TAGS = {"NOUN_PROP", "NOUN_PROP_FOREIGN"}
NOUN_DECLN_TAGS = {
    "NOUN_CONCRETE", "NOUN_ABSTRACT", "NOUN_ACTIVE_PART",
    "NOUN_PASSIVE_PART", "GERUND", "NOUN_NUM", "NOUN_QUASI",
    "NOUN_INSTRUMENT", "NOUN_DIMINUTIVE", "NOUN_TIME_SPACE",
    "ADJ_QUALIT", "ADJ_COMP", "ADJ_INTENS", "ADJ_QUALIT_DEFECT",
    "ADJ_QUASI",
}
MABNI_TAGS = {
    "REL_PRON", "DEM_PRON", "PRON", "INTERR_PRON",
    "VOC_PART_PRON", "CONDIT_PRON",
}
HARF_TAGS = {
    "PREP", "CONJ", "NEG_PART", "ANNUL_PART", "INF_ANNUL_PART",
    "SUBJUNC_PART", "CONDITION_PART", "EXCEPT_PART", "JUSSIVE_PART",
    "CERT_PART", "VOC_PART", "INTERROG_PART", "EMPHATIC_PART",
    "FOC_PART", "RESULT_PART", "FUT_PART", "RESTRICTION_PART",
    "ANSWER_PART", "EXPLAN_PART", "INCEPT_PART", "RETRACT_PART",
    "AVERT_PART", "ADV",  # ظَرف
}
# أَسماء وَظيفيَّة تُصَنَّف ISM_MUARAB مَع وَسم خاصّ
FUNCTIONAL_NOUN_TAGS = {
    "EXCEPT_NOUN",  # غَيْر، سِوى
    "EQUAT_NOUN",   # مِثل
    "TIME_ADV",     # ظُروف زَمان
    "LOC_ADV",      # ظُروف مَكان
}


def masaq_tag_to_word_class(tag: str) -> str:
    """يُحَوِّل MASAQ Morph_Tag إلى word_class مَشروعنا."""
    if not tag:
        return "UNKNOWN"
    t = tag.strip().upper()
    if t in VERB_TAGS:
        return "FIIL"
    if t in PROPER_TAGS:
        return "JAMID"
    if t in MABNI_TAGS:
        return "ISM_MAWSOOL" if t == "REL_PRON" else "ISM_MABNI"
    if t in NOUN_DECLN_TAGS:
        return "ISM_MUARAB"
    if t in FUNCTIONAL_NOUN_TAGS:
        return "ISM_MUARAB"  # ظُروف وَ أَسماء وَظيفيَّة → ISM
    if t in HARF_TAGS:
        return "HARF"
    return "UNKNOWN"


def aspect_of(tag: str) -> str:
    """إِسناد aspect (PV/IV/CV) لِلأَفعال."""
    t = (tag or "").strip().upper()
    if t in ("PV", "PV_PASS"):
        return "PV"
    if t in ("IV", "IV_PASS"):
        return "IV"
    if t == "CV":
        return "CV"
    return ""


# ─────────────────────────────────────────────────────────────
# Load MEEMAR — index by (sura, verse, word)
# ─────────────────────────────────────────────────────────────

def load_meemar_index():
    """يَبني فَهرَس: (sura,verse,word) → {root, wazn, confidence} مِن Stem segment."""
    idx = {}
    if not MEEMAR.is_file():
        return idx
    with open(MEEMAR, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                key = (int(row["Sura_No"]), int(row["Verse_No"]), int(row["Word_No"]))
            except (KeyError, ValueError):
                continue
            morph_type = (row.get("Morph_Type / النوع_الموضعي") or "").strip()
            if not morph_type.startswith("Stem"):
                continue
            root = (row.get("Our_Root") or "").strip()
            wazn = (row.get("Our_Wazn") or "").strip()
            conf = (row.get("Our_Confidence") or "").strip()
            agreement = (row.get("Agreement_With_MASAQ") or "").strip()
            if key not in idx:
                idx[key] = {
                    "root": root, "wazn": wazn,
                    "confidence": conf, "agreement": agreement,
                }
    return idx


# ─────────────────────────────────────────────────────────────
# Process MASAQ — group by word, take Stem segment as canonical
# ─────────────────────────────────────────────────────────────

def build_table():
    print(f"[1/3] Loading MEEMAR index from {MEEMAR}…")
    meemar_idx = load_meemar_index()
    print(f"      MEEMAR indexed: {len(meemar_idx)} (sura,verse,word) entries")

    print(f"[2/3] Processing MASAQ from {MASAQ}…")
    # نَجمَع كُلّ صُفوف الكَلِمَة الواحِدَة (segments) ثُمَّ نَأخُذ Stem
    word_segments = defaultdict(list)
    with open(MASAQ, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                key = (int(row["Sura_No"]), int(row["Verse_No"]), int(row["Word_No"]))
            except (KeyError, ValueError):
                continue
            word_segments[key].append(row)

    print(f"      MASAQ words: {len(word_segments)}")

    # نَبني unique surface → entry
    # لَو نَفس الـsurface ظَهَر بِتَصنيفات مُختَلِفَة → نُسَجِّل كَ ambiguous
    surface_entries = {}  # surface → list of (entry, key)
    print(f"[3/3] Building master table…")
    for key, segs in word_segments.items():
        # ابحَث عَن Stem segment (الأَهَمّ — يَحمِل التَّصنيف الجَوهَريّ)
        stem = None
        for s in segs:
            if (s.get("Morph_Type") or "").strip() == "Stem":
                stem = s
                break
        if stem is None:
            # لَيس فيها Stem — قَد تَكون كُلّها prefix/suffix (نادِر)
            stem = segs[0]

        surface = (stem.get("Word") or "").strip()
        plain = (stem.get("Without_Diacritics") or "").strip()
        tag = (stem.get("Morph_Tag") or "").strip()
        morph_type = (stem.get("Morph_Type") or "").strip()
        wc = masaq_tag_to_word_class(tag)
        asp = aspect_of(tag)
        case = (stem.get("Case_Mood") or "").strip()
        role = (stem.get("Syntactic_Role") or "").strip()

        meem = meemar_idx.get(key, {})
        root = meem.get("root", "")
        wazn = meem.get("wazn", "")
        confidence = meem.get("confidence", "")
        agreement = meem.get("agreement", "Unknown")

        entry = {
            "surface": surface,
            "plain": plain,
            "word_class": wc,
            "masaq_tag": tag,
            "lemma": "",
            "root": root,
            "wazn": wazn,
            "aspect": asp,
            "case": case,
            "role": role,
            "source": f"MASAQ:{stem.get('ID','')}",
            "agreement_with_masaq": agreement,
            "confidence": "Certificate" if agreement == "Match" else
                          ("Hypothesis" if agreement in ("Partial","Disagree") else "Certificate"),
            "first_seen_at": f"{key[0]}:{key[1]}:{key[2]}",
        }
        if surface in surface_entries:
            # لَو نَفس التَّصنيف، لا حاجَة لِلتَّسجيل مَرَّة أُخرى
            existing = surface_entries[surface][0]
            if existing["word_class"] != wc:
                # ambiguous! نُسَجِّل أَوَّل ظُهور كَ canonical لَكِنّنا نُؤَشِّر
                existing["ambiguous"] = existing.get("ambiguous", "") + f";{wc}@{key}"
        else:
            surface_entries[surface] = [entry]

    print(f"      unique surfaces: {len(surface_entries)}")

    # كَتابَة CSV
    fields = ["surface","plain","word_class","masaq_tag","lemma","root","wazn",
              "aspect","case","role","source","agreement_with_masaq",
              "confidence","first_seen_at","ambiguous"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for surf, entries in sorted(surface_entries.items()):
            for entry in entries:
                row = {k: entry.get(k, "") for k in fields}
                w.writerow(row)

    print(f"\n✓ Wrote {OUT}")
    print(f"  unique surfaces: {len(surface_entries)}")

    # تَوزيع word_class
    dist = defaultdict(int)
    for entries in surface_entries.values():
        for e in entries:
            dist[e["word_class"]] += 1
    print(f"\n  word_class distribution:")
    for k, v in sorted(dist.items(), key=lambda kv: -kv[1]):
        print(f"    {k:<15s} {v}")


if __name__ == "__main__":
    build_table()
