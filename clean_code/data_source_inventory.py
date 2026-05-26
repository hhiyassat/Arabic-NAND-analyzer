#!/usr/bin/env python3
"""data_source_inventory.py — مَسح new_arabic_analyzer/data بِلا تَغيير runtime.

الهَدَف (Phase 1 مِن خُطَّة المُستَخدِم 2026-05-26):
  • مَسح كُلّ ملَفّ JSON/CSV في new_arabic_analyzer/data
  • تَصنيف كُلّ مَلَفّ: source_type, entry_count, keys, target_classes,
    closed_class?, requires_context?, notes
  • إِنتاج data_source_inventory.csv
  • لا يَلمَس أَيّ كود قائِم. لا تَغيير في Layer 1.

التَّصنيف:
  closed_class    — قائِمَة مُغلَقَة (ضَمائر، حُروف جَرّ، أَدوات شَرط…)
  rule            — قاعِدَة نَحويَّة (كان وأَخواتها، أَفعال ناصِبَة…)
  pattern         — وَزن صَرفيّ (فاعِل، مَفعول، أَفعَل تَفضيل…)
  lexicon         — مَعجَم كَلِمات (جُذور، أَفعال، أَسماء)
  examples        — جُمَل مِثاليَّة (test corpus)
  benchmark       — بَيانات قِياس (MASAQ، MEEMAR…)
  unknown         — يَحتاج فَحص يَدَويّ
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path("/sessions/nice-epic-cannon/mnt/new_arabic_analyzer/data")
OUT = Path(__file__).resolve().parent / "data_source_inventory.csv"


# ─────────────────────────────────────────────────────────────
# تَخمين الـsource_type مِن اسم الـfolder + بِنيَة الـcontent
# ─────────────────────────────────────────────────────────────

# Hint: اسم المُجَلَّد يَدُلّ
FOLDER_HINTS = {
    "01_phonology": "rule",
    "02_mabniyat": "closed_class",
    "03_juthur_mushtaqat": "pattern",
    "04_nahw": "rule",
    "awzan": "pattern",
    "quran": "examples",
    "connectives_api": "closed_class",
    "masaq_engine": "benchmark",
}

# Hint: اسم المَلَفّ يَدُلّ بِشَكل أَدَقّ
FILENAME_HINTS = {
    "MASAQ.csv": ("benchmark", "Arabic Quran morphological gold standard"),
    "masaq_ayahs.csv": ("benchmark", "MASAQ ayah list"),
    "mishkat_word_root.csv": ("lexicon", "16k Arabic word→root pairs"),
    "test_corpus.csv": ("examples", "test sentences"),
    "data_bank.csv": ("lexicon", "general data bank"),
    "horof_muaqatah.csv": ("closed_class", "الحُروف المُقَطَّعَة"),
    "awzan_cleaned_with_example.csv": ("pattern", "500 أَوزان مَع أَمثِلَة"),
    "awzan_cleaned_with_example_unique_pairs.csv": ("pattern", "أَوزان فَريدَة"),
    "awzan_cleaned_unique.txt": ("pattern", "قائِمَة أَوزان"),
    "awzan_merged_final100.csv": ("pattern", "100 وَزن مَوحَّد"),
    "operators_catalog_split.csv": ("closed_class", "العَوامِل المِئَة"),
    "operators_catalog_split_vocalized.csv": ("closed_class", "العَوامِل بِالتَّشكيل"),
    "operators_catalog_gate_entries.json": ("closed_class", "العَوامِل كَ gates"),
    "operators_particles.json": ("closed_class", "particle operators"),
}

# تَصنيف word_class الَّذي يَستَهدِفه كُلّ ملَفّ
TARGET_CLASS_HINTS = {
    "demonstrative_pronouns": ["ISM_MABNI"],
    "pronouns_classification": ["ISM_MABNI"],
    "hidden_pronouns": ["ISM_MABNI"],
    "relative_pronouns": ["ISM_MAWSOOL"],
    "interrogative_letters_tools": ["ISM_MABNI", "HARF"],
    "interrogative_tools_categories": ["ISM_MABNI"],
    "conditional_letters_tools": ["HARF", "ISM_MABNI"],
    "coordinating_conjunctions": ["HARF"],
    "copulative_particle": ["HARF"],
    "vocative_particles": ["HARF"],
    "jazm_tools": ["HARF"],
    "present_naseb_tools": ["HARF"],
    "verb_building_rules": ["FIIL"],
    "imperative_verb_building": ["FIIL"],
    "past_tense_conjugation_rules": ["FIIL"],
    "present_tense_building_cases": ["FIIL"],
    "verb_name": ["FIIL", "ISM_MUARAB"],
    "built_in_adverbs": ["ISM_MABNI"],
    "kinaya_names": ["JAMID"],
    "compound_numbers": ["ISM_MUARAB"],
    "compound_number_details": ["ISM_MUARAB"],
    "preposition_meanings": ["HARF"],
    "building_regulations": ["meta"],
    "estimated_parsing_indeclinables": ["ISM_MABNI"],
    "functional_indeclinable_substitutes": ["ISM_MABNI"],
    "grammatical_construction_cases": ["meta"],
    "indeclinable_discourse_roles": ["meta"],
    "letters_answers": ["HARF"],
    "types_of_i3rab": ["meta"],
    # 03_juthur_mushtaqat
    "triliteral_active_participles": ["ISM_MUARAB"],
    "passive_participles_triliteral": ["ISM_MUARAB"],
    "non_passive_participles": ["ISM_MUARAB"],
    "descriptive_adjective_forms": ["ISM_MUARAB"],
    "quad_verb_analysis": ["FIIL"],
    "shadda_positions": ["meta"],
    "shadda_types": ["meta"],
    "shadda_weight_rules": ["meta"],
    "marra_sources": ["ISM_MUARAB"],
    "marra_conditions": ["meta"],
    "tamyeez_guides": ["ISM_MUARAB"],
    # 04_nahw
    "accusative_verbs": ["FIIL"],
    "kana_sisters": ["FIIL"],
    "verb_classifications": ["FIIL"],
    "verb_subject_rules": ["meta"],
    "verbs_five_forms": ["FIIL"],
    "sound_verb_types": ["FIIL"],
    "maf3ool_types": ["meta"],
    "comparative_nouns": ["ISM_MUARAB"],
    "comparative_noun_rules": ["meta"],
    "comparative_exceptions": ["ISM_MUARAB"],
    "al_ism_almaqsur": ["ISM_MUARAB"],
    "extended_nouns": ["ISM_MUARAB"],
    "noun_classification": ["meta"],
    "noun_extension_rules": ["meta"],
    "nominative_cases": ["meta"],
    "exception_definitions": ["meta"],
    "exception_ahkam_illa": ["HARF"],
    "exception_ahkam_ghayr_siwa": ["ISM_MUARAB"],
    "exception_ahkam_khala_ada_hasha": ["FIIL", "HARF"],
    "ta_fael": ["meta"],
}

# هَل الـtoken يَحتاج تَحليل سياقيّ لِلحَسم؟
REQUIRES_CONTEXT_HINTS = {
    "interrogative_letters_tools": True,   # مَن/ما/أَيّ
    "conditional_letters_tools": True,     # إِن/إِذا/مَن/ما
    "relative_pronouns": True,             # مَن/ما/الَّذي
    "exception_ahkam_illa": True,          # إِلَّا
    "comparative_nouns": True,             # أَفْعَل (تَفضيل vs فِعل)
}


def _classify_file(path: Path) -> dict:
    """يُصَنِّف ملَفًّا واحِدًا."""
    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path.name
    rel_str = str(rel)
    fname = path.name
    stem = path.stem
    folder = path.parent.name
    ext = path.suffix.lower()

    # filename hint
    if fname in FILENAME_HINTS:
        stype, notes = FILENAME_HINTS[fname]
    else:
        stype = FOLDER_HINTS.get(folder, "unknown")
        notes = ""

    # count entries
    entry_count = 0
    keys = []
    sample = None
    try:
        if ext == ".json":
            with path.open(encoding="utf-8") as f:
                content = json.load(f)
            data = content.get("data", content) if isinstance(content, dict) else content
            if isinstance(data, list):
                entry_count = len(data)
                if data and isinstance(data[0], dict):
                    keys = list(data[0].keys())
                    sample = data[0]
            elif isinstance(data, dict):
                entry_count = len(data)
                keys = list(data.keys())[:5]
        elif ext in (".csv", ".tsv"):
            with path.open(encoding="utf-8") as f:
                r = csv.reader(f)
                headers = next(r, [])
                keys = headers
                entry_count = sum(1 for _ in r)
        elif ext == ".txt":
            with path.open(encoding="utf-8") as f:
                lines = [l for l in f.read().splitlines() if l.strip()]
            entry_count = len(lines)
    except Exception as e:
        notes = f"PARSE_ERROR: {e}"

    target_classes = TARGET_CLASS_HINTS.get(stem, [])
    requires_context = REQUIRES_CONTEXT_HINTS.get(stem, False)
    is_closed = stype in ("closed_class",)

    return {
        "source_path": rel_str,
        "source_type": stype,
        "entry_count": entry_count,
        "keys": "|".join(keys[:8]),
        "target_classes": "|".join(target_classes),
        "closed_class": "yes" if is_closed else "no",
        "requires_context": "yes" if requires_context else "no",
        "notes": notes,
    }


def main():
    if not ROOT.is_dir():
        print(f"ERROR: {ROOT} not found")
        return
    rows = []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".json", ".csv", ".tsv", ".txt"):
            continue
        rows.append(_classify_file(p))

    # Write CSV
    fields = ["source_path","source_type","entry_count","keys",
              "target_classes","closed_class","requires_context","notes"]
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Wrote {OUT}  ({len(rows)} entries)")
    print()
    # Summary
    from collections import Counter
    stypes = Counter(r["source_type"] for r in rows)
    print("By source_type:")
    for s, n in stypes.most_common():
        print(f"  {s:<18s} {n}")
    print()
    closed = [r for r in rows if r["closed_class"] == "yes"]
    print(f"Closed-class sources: {len(closed)}")
    for r in closed:
        print(f"  {r['source_path']:<70s} [{r['entry_count']} entries] → {r['target_classes']}")
    print()
    ctx = [r for r in rows if r["requires_context"] == "yes"]
    print(f"Requires-context sources: {len(ctx)}")
    for r in ctx:
        print(f"  {r['source_path']:<70s} → {r['target_classes']}")


if __name__ == "__main__":
    main()
