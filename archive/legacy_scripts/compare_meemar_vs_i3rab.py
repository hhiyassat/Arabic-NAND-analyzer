"""Compare MEEMAR.csv with quran_i3rab_labels.jsonl on Al-Fatiha.

Maps the i3rab labels (MAJROOR, MUDAF, NACT, ...) to our schema and
produces a per-word comparison showing:
  - Case_Mood agreement (ours vs i3rab)
  - Suggested values for our currently-empty Tier 3 columns
  - Where i3rab can ENRICH our MEEMAR.csv

Output: compare_fatiha.md
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path("/Users/husseinhiyassat/fractal/hussein")
SANDBOX = Path("/sessions/nice-epic-cannon/mnt/hussein")
if not ROOT.is_dir():
    ROOT = SANDBOX

MEEMAR = ROOT / "data" / "MEEMAR.csv"
I3RAB_LABELS = Path("/sessions/nice-epic-cannon/mnt/new_arabic_analyzer/data/quran/quran_i3rab_labels.jsonl")
I3RAB_FULL = Path("/sessions/nice-epic-cannon/mnt/new_arabic_analyzer/data/quran/quran_i3rab.csv")
OUT_MD = ROOT / "MEEMAR_VS_I3RAB_FATIHA.md"

# i3rab label → our schema mappings
CASE_FROM_LABEL = {
    "MAJROOR": "GENITIVE / جر",
    "MARFOO": "NOMINATIVE / رفع",
    "MANSOOB": "ACCUSATIVE / نصب",
    "MAJZOOM": "JUSSIVE / جزم",
}

# Role labels → Arabic syntactic role
ROLE_FROM_LABEL = {
    "MUBTADA": "مبتدأ",
    "KHABAR": "خبر",
    "FAAIL": "فاعل",
    "NAIB_FAAIL": "نائب فاعل",
    "MAFOOL_BIH": "مفعول به",
    "MAFOOL": "مفعول",
    "MAFOOL_FIH": "مفعول فيه",
    "MAFOOL_LAH": "مفعول لأجله",
    "MAFOOL_MAAH": "مفعول معه",
    "MAFOOL_MUTLAQ": "مفعول مطلق",
    "NACT": "نعت",
    "BADAL": "بدل",
    "MAOTOOF": "معطوف",
    "TAWKEED": "توكيد",
    "HAL": "حال",
    "TAMYEEZ": "تمييز",
    "MUNADA": "منادى",
    "MUSTATHNA": "مستثنى",
    "ISM_INNA": "اسم إن",
    "KHABAR_INNA": "خبر إن",
    "ISM_KANA": "اسم كان",
    "KHABAR_KANA": "خبر كان",
}

# الإضافة labels
IDAFAH_FROM_LABEL = {
    "MUDAF": "مضاف",
    "MUDAF_ILAYH": "مضاف إليه",
}

# Word-class labels
WORD_CLASS_FROM_LABEL = {
    "HARF": "حرف",
    "FIIL": "فعل",
    "ISM": "اسم",
    "DAMEER": "ضمير",
}

# Particle/clitic subtypes
PARTICLE_SUBTYPE = {
    "HARF_JARR": "حرف جر",
    "HARF_ATF": "حرف عطف",
    "HARF_NIDA": "حرف نداء",
    "HARF_NAFI": "حرف نفي",
    "HARF_NASB": "حرف نصب",
    "HARF_JAZM": "حرف جزم",
    "HARF_TAWKEED": "حرف توكيد",
    "ISM_MAWSOOL": "اسم موصول",
    "ISM_ISHARA": "اسم إشارة",
    "ISM_SHART": "اسم شرط",
}


def parse_i3rab_labels(labels: list[str]) -> dict:
    """Convert i3rab label list into structured fields."""
    out = {
        "case_mood": None,
        "role": None,
        "idafah": None,
        "word_class": None,
        "particle_subtype": None,
        "is_mabni": "MABNI" in labels,
        "raw_labels": labels,
    }
    for lbl in labels:
        if lbl in CASE_FROM_LABEL:
            out["case_mood"] = CASE_FROM_LABEL[lbl]
        elif lbl in ROLE_FROM_LABEL:
            # MAFOOL_BIH and MAFOOL both appear together — prefer specific
            if out["role"] is None or "MAFOOL_BIH" in labels:
                out["role"] = ROLE_FROM_LABEL[lbl]
        elif lbl in IDAFAH_FROM_LABEL:
            if out["idafah"] is None:
                out["idafah"] = IDAFAH_FROM_LABEL[lbl]
            else:
                out["idafah"] = out["idafah"] + " | " + IDAFAH_FROM_LABEL[lbl]
        elif lbl in WORD_CLASS_FROM_LABEL:
            out["word_class"] = WORD_CLASS_FROM_LABEL[lbl]
        elif lbl in PARTICLE_SUBTYPE:
            out["particle_subtype"] = PARTICLE_SUBTYPE[lbl]
    if out["is_mabni"] and not out["case_mood"]:
        out["case_mood"] = "INVARIABLE / مبني"
    return out


def main() -> int:
    # Load i3rab labels for Fatiha
    i3rab = {}
    with open(I3RAB_LABELS, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["surah"] != 1:
                continue
            key = (r["ayah"], r["word"])
            i3rab[key] = parse_i3rab_labels(r["labels"])

    # Load i3rab full text
    i3rab_text = {}
    with open(I3RAB_FULL, encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        for row in r:
            if row["surah"] != "1":
                continue
            i3rab_text[(int(row["ayah"]), row["word"])] = row["i3rab"]

    # Load MEEMAR Fatiha — keep stem rows + group by (verse, word_no)
    meemar_by_word = defaultdict(list)
    with open(MEEMAR, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if row["Sura_No"] != "1":
                continue
            meemar_by_word[(int(row["Verse_No"]), int(row["Word_No"]))].append(row)

    # Build comparison
    lines = []
    lines.append("# MEEMAR vs i3rab — سورة الفاتحة")
    lines.append("")
    lines.append("**التاريخ:** 2026-05-19")
    lines.append("**المرجع:** quran_i3rab_labels.jsonl (Hussein's i3rab)")
    lines.append("**هدف:** التحقق من Case_Mood + استخراج Tier 3 (الوظيفة_النحوية، الإضافة)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## جدول المقارنة الكلمة-بكلمة")
    lines.append("")
    lines.append("| Word | Our Case_Mood | i3rab Case | ✓/✗ | i3rab Role | Our Wazn/Root |")
    lines.append("|---|---|---|---|---|---|")

    n_total = n_agree_case = n_disagree_case = 0
    n_role_provided = 0
    enrichment_suggestions = []

    for (ayah, word_no), rows in sorted(meemar_by_word.items()):
        # Word-level case_mood = last non-empty case among segments (this is
        # the segment that carries the case marker).
        word_surface = rows[0]["Word"]
        our_case = ""
        for r in reversed(rows):
            if r["Case_Mood / الحالة_الإعرابية"]:
                our_case = r["Case_Mood / الحالة_الإعرابية"]
                break
        stem_row = next((r for r in rows if r["Our_Root"]), rows[-1])
        our_root = stem_row["Our_Root"]
        our_wazn = stem_row["Our_Wazn"]

        # Match i3rab by full surface word
        i3rab_match = i3rab.get((ayah, word_surface))
        if not i3rab_match:
            lines.append(f"| {word_surface} | {our_case} | _no i3rab_ | — | — | {our_root}/{our_wazn} |")
            continue

        their_case = i3rab_match["case_mood"] or "—"
        their_role = i3rab_match["role"] or "—"
        their_idafah = i3rab_match["idafah"] or ""

        n_total += 1
        # Normalize for comparison: لفظ الجلالة في محل X ↔ standard case
        def _canon(c: str) -> str:
            if "لفظ الجلالة في محل جر" in c: return "GENITIVE / جر"
            if "لفظ الجلالة في محل رفع" in c: return "NOMINATIVE / رفع"
            if "لفظ الجلالة في محل نصب" in c: return "ACCUSATIVE / نصب"
            return c
        agree = (_canon(our_case) == _canon(their_case))
        if agree:
            n_agree_case += 1
            mark = "✓"
        else:
            n_disagree_case += 1
            mark = "✗"

        if their_role != "—":
            n_role_provided += 1

        if their_role != "—" or their_idafah:
            enrichment_suggestions.append({
                "ayah": ayah, "word_no": word_no, "word": word_surface,
                "role": their_role, "idafah": their_idafah,
            })

        lines.append(f"| {word_surface} | {our_case} | {their_case} | {mark} | "
                     f"{their_role} {('+' + their_idafah) if their_idafah else ''} | "
                     f"{our_root}/{our_wazn} |")

    lines.append("")
    lines.append(f"**Agreement على Case_Mood:** {n_agree_case}/{n_total} = "
                 f"**{100*n_agree_case/n_total:.1f}%**")
    lines.append("")
    lines.append(f"**Roles provided by i3rab:** {n_role_provided}/{n_total} = "
                 f"**{100*n_role_provided/n_total:.1f}%** "
                 f"(يملأ عمود `الوظيفة_النحوية` لنا)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## ما يمكن أن يُملأ في MEEMAR.csv من i3rab")
    lines.append("")
    lines.append("| Ayah | Word_No | Word | الوظيفة_النحوية | الإضافة |")
    lines.append("|---|---|---|---|---|")
    for s in enrichment_suggestions[:30]:
        lines.append(f"| {s['ayah']} | {s['word_no']} | {s['word']} | "
                     f"{s['role']} | {s['idafah']} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## النص الإعرابي الكامل (مرجع لكل كلمة)")
    lines.append("")
    for (ayah, word), text in sorted(i3rab_text.items()):
        lines.append(f"**{ayah}:{word}** — {text}")
        lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"=== Comparison summary ===")
    print(f"  Words compared: {n_total}")
    print(f"  Case_Mood agreement: {n_agree_case}/{n_total} ({100*n_agree_case/n_total:.1f}%)")
    print(f"  Roles available: {n_role_provided}/{n_total}")
    print(f"  Output: {OUT_MD}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
