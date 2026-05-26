"""Human-readable report for architecture tests."""

from __future__ import annotations

from .pipeline import ArchitectureTestResult, LAYER_ORDER, STATE_PATTERNS
from .verb_frames_loader import ROLE_DISPLAY


def format_architecture_report(result: ArchitectureTestResult) -> str:
    s = result.sample
    lines: list[str] = []
    w = lines.append

    w("=" * 72)
    w("Architecture Test")
    w("اختبار تطبيقي للمعمار")
    w("=" * 72)
    w(f"ID        : {s.get('id', '')}")
    w(f"Reference : {s.get('reference', '')}")
    qa = s.get("quran_ayah") or {}
    if qa:
        w(f"Quran     : surah {qa.get('surah')} ayah {qa.get('ayah')} ({qa.get('lookup', '')})")
    w(f"Text      : ﴿{s.get('text_vocalized', '')}﴾")
    if s.get("prior_context"):
        w(f"Context   : {s['prior_context']}")
    w(f"Tokens    : {len(result.tokens)}")
    w("")

    db = result.diacritization or {}
    if db and not db.get("skipped"):
        w("─" * 72)
        w("STEP −2 — Diacritization (salehan/Models_gpt52)")
        w("─" * 72)
        w(f"  Source : {db.get('source_dir', '')}")
        w(f"  Avail. : {db.get('available', False)}")
        w(f"  Input had tashkil : {db.get('had_sufficient_diacritics', False)}")
        if db.get("applied"):
            w(f"  Raw input : {db.get('text_raw', '')}")
            w(f"  Vocalized : {db.get('text_vocalized', '')}  (model)")
        elif db.get("requested") and db.get("error"):
            w(f"  Note : {db.get('error', '')}")
            w(f"  Text used : {db.get('text_vocalized', '')}")
        else:
            w(f"  Text   : {db.get('text_vocalized', '')}  (unchanged)")
        w("")

    nb = result.normalization or {}
    if nb and not nb.get("skipped"):
        w("─" * 72)
        w("STEP −1 — Normalize (new_arabic_analyzer/normalize.py)")
        w("─" * 72)
        w(f"  Source : {nb.get('source', '')}")
        w(f"  Avail. : {nb.get('available', False)}")
        if nb.get("changed"):
            w(f"  Input  : {nb.get('input_text', '')}")
            w(f"  Output : {nb.get('normalized_text', '')}  (changed)")
        else:
            w(f"  Text   : {nb.get('normalized_text', '')}  (unchanged)")
        w("")

    sb = result.segmentation or {}
    if sb and not sb.get("skipped"):
        w("─" * 72)
        w("STEP 0a — Segmenter (fractal/segmenter)")
        w("─" * 72)
        w(f"  Source : {sb.get('source', '')}")
        w(f"  Engine : {sb.get('engine', '')}")
        w(f"  Avail. : {sb.get('available', False)}")
        counts = sb.get("counts", {})
        w(f"  Counts : segmented={counts.get('segmented', 0)}, unchanged={counts.get('unchanged', 0)}")
        for row in sb.get("per_token", []):
            if row.get("segmented"):
                pref = "+".join(row.get("prefixes") or []) or "—"
                suf = "+".join(row.get("suffixes") or []) or "—"
                w(f"  ✓ {row['surface']}  →  prefixes=[{pref}]  stem={row['stem']}  suffixes=[{suf}]")
            else:
                w(f"  ○ {row['surface']}  →  (unchanged)")
        w("")

    w("─" * 72)
    w("Tokens (surface hints)")
    w("─" * 72)
    for t in result.tokens:
        flags = []
        if t.get("looks_nasikh"):
            flags.append("nasikh")
        if t.get("is_ma_accompaniment"):
            flags.append("مع")
        if t.get("has_al"):
            flags.append("al-")
        if t.get("has_tanwin"):
            flags.append("tanwin")
        if t.get("looks_verbal"):
            flags.append("verbal?")
        h = t.get("huruf") or {}
        huruf_s = f"huruf={h['canonical_id']}" if h.get("in_dataset") else "huruf=—"
        aw = t.get("analyze_word") or {}
        wazn_s = ""
        if aw:
            if aw.get("status") == "MATCHED":
                wazn_s = f"  wazn={aw.get('best_wazn')} root={aw.get('extracted_root')}"
            elif aw.get("status") == "OPERATOR_SKIPPED":
                wazn_s = "  wazn=(operator skipped)"
            elif aw.get("status"):
                wazn_s = f"  wazn=({aw.get('status')})"
        w(
            f"  [{t['index']}] {t['surface']}  "
            f"({t.get('definiteness')}, {t.get('case_hint')})  "
            f"{huruf_s}"
            + wazn_s
            + (f"  [{', '.join(flags)}]" if flags else "")
        )
    w("")

    aw_step = result.analyze_word
    w("─" * 72)
    w("STEP 0b — analyze_word.py (Mushtaqat wazn + root)")
    w("─" * 72)
    if aw_step.get("skipped"):
        w("  (skipped via --skip-analyze-word)")
    else:
        w(f"  Module  : {aw_step.get('source', '')}")
        w(f"  Weights : {aw_step.get('weights_path', '')} ({aw_step.get('weights_count', 0)} rows)")
        sc = aw_step.get("status_counts") or {}
        w(
            "  Status  : "
            + ", ".join(f"{k}={v}" for k, v in sorted(sc.items()))
        )
        for row in aw_step.get("per_token") or []:
            if row.get("status") == "MATCHED":
                w(
                    f"  ✓ {row['surface']} → {row['best_wazn']} "
                    f"({row['bab']}) root={row['extracted_root']} "
                    f"[{row['variant_label']}]"
                )
            elif row.get("status") == "OPERATOR_SKIPPED":
                w(f"  ○ {row['surface']} → operator (no wazn)")
            else:
                w(f"  ✗ {row['surface']} → {row.get('status')}")
        # Stem fallback hits: tokens enriched on stem retry.
        stem_hits = [
            t for t in result.tokens
            if (t.get("analyze_word") or {}).get("via_stem")
        ]
        if stem_hits:
            w("  Stem-retry hits (analyzed via salehan stem):")
            for t in stem_hits:
                aw = t["analyze_word"]
                w(
                    f"    ↪ {t['surface']} → stem={aw.get('stem_used')} → "
                    f"{aw.get('best_wazn')} ({aw.get('bab')}) root={aw.get('extracted_root')}"
                )
    w("")

    w("─" * 72)
    w("STEP 1 — Meaning Flow (03)")
    w("─" * 72)
    mf = result.meaning_flow
    w("Path: " + " → ".join(mf["path"]))
    w("")
    w("Sign → Attention:")
    for note in mf["sign_attention"]:
        w(f"  • {note}")
    w(f"\nInitial conception: {mf['initial_conception']}")
    w("\nPossibility space:")
    for p in mf["possibilities"]:
        w(f"  ? {p}")
    w("\nEvidence:")
    for e in mf["evidence"]:
        w(f"  • {e}")
    w("\nRelations:")
    for r in mf["relations"]:
        w(f"  • {r}")
    w(f"\nWeighing: {mf['weighing']}")
    w(f"\nMeaning: {mf['meaning']}")
    w(f"\nUnderstanding: {mf['understanding']}")
    w("")

    w("─" * 72)
    w("STEP 2 — Layer-Centric Decomposition (01)")
    w("─" * 72)
    for layer in LAYER_ORDER:
        text = result.layers["assignments"].get(layer, "—")
        mark = "○" if layer in result.layers["inactive_layers"] else "●"
        w(f"  {mark} {layer}: {text}")
    w(f"\nNote: {result.layers['structural_note']}")
    w("")

    w("─" * 72)
    w("STEP 3 — Huruf dataset matching")
    w("─" * 72)
    hm = result.huruf_matching
    for el in hm["elements"]:
        if el.get("in_dataset"):
            w(
                f"  ✓ {el['element']} → {el['canonical_id']} "
                f"({el.get('canonical_form')})"
            )
        else:
            w(f"  ✗ {el['element']} — NOT in dataset")
            if el.get("note"):
                w(f"      {el['note']}")
            if el.get("gap"):
                w(f"      {el['gap']}")
    w(f"\n{hm['gap_statement']}")
    w("")

    w("─" * 72)
    w("STEP 3.5 — Word classification (اسم وفعل وحرف) + wazn/root")
    w("─" * 72)
    wc = result.word_classification
    counts = wc["class_counts"]
    w(
        "  "
        + "  |  ".join(f"{k}: {v}" for k, v in counts.items() if v > 0)
    )
    w(f"  coverage: {wc['coverage_pct']}% of tokens classified")
    for row in wc["per_token"]:
        extras = []
        if row.get("aalam_category"):
            extras.append(f"aalam:{row['aalam_category']}")
        if row.get("wazn"):
            wazn_str = f"wazn={row['wazn']}"
            if row.get("root"):
                wazn_str += f" root={row['root']}"
            if row.get("bab"):
                wazn_str += f" ({row['bab']})"
            extras.append(wazn_str)
        if row["jamid_categories"]:
            extras.append("jamid:" + "/".join(row["jamid_categories"]))
        if row["mushtaq_babs"] and not row.get("wazn"):
            extras.append("pattern-only:" + "/".join(row["mushtaq_babs"]))
        if row["huruf_canonical_id"]:
            extras.append(f"huruf:{row['huruf_canonical_id']}")
        extras_str = f"  [{', '.join(extras)}]" if extras else ""
        w(f"  {row['element']} → {row['word_class']}{extras_str}")
    if wc.get("roots_extracted"):
        w("  roots: " + ", ".join(wc["roots_extracted"]))
    if wc["jamid_categories_seen"]:
        w("  jamid categories: " + ", ".join(wc["jamid_categories_seen"]))
    if wc.get("aalam_categories_seen"):
        w("  aalam categories: " + ", ".join(wc["aalam_categories_seen"]))
    if wc["mushtaq_babs_seen"]:
        w("  mushtaq babs: " + ", ".join(wc["mushtaq_babs_seen"]))
    w(f"  {wc['layer_note']}")
    w("")

    # Semantic-field membership block — show tokens that hit a lexical field.
    sem_tokens = [
        t for t in result.tokens
        if (t.get("semantic_fields") or {}).get("in_seed")
    ]
    if sem_tokens:
        w("─" * 72)
        w("STEP 3.55 — Semantic Field membership (lexical sets)")
        w("─" * 72)
        for t in sem_tokens:
            sf = t["semantic_fields"]
            fields_str = " / ".join(sf["fields"])
            mem = sf["members"][0] if sf["members"] else {}
            meta = mem.get("metadata", {})
            meta_str = ", ".join(f"{k}={v}" for k, v in meta.items()) if meta else "—"
            w(f"  {t['surface']} → {fields_str}  [{meta_str}]")
        w("  source: data/extracted/semantic_fields/")
        w("")

    # Verb-suffix classification — show tokens whose segmentation yielded a
    # known verb suffix (provides person/number/gender even without wazn match).
    suffix_tokens = [
        t for t in result.tokens
        if (t.get("verb_suffix") or {}).get("detected")
    ]
    if suffix_tokens:
        w("─" * 72)
        w("STEP 3.65 — Verb suffix classification (تاء/نون/واو/ألف)")
        w("─" * 72)
        for t in suffix_tokens:
            for info in t["verb_suffix"]["infos"]:
                amb = f"  [ambiguous: {info['ambiguity']}]" if info["ambiguity"] else ""
                gender = info["gender"] or "—"
                w(
                    f"  {t['surface']}  suffix={info['suffix']}  → "
                    f"{info['label_ar']}  ({info['person']}, {info['number']}, gender={gender})  "
                    f"pronoun={info['pronoun_ar']}{amb}"
                )
        w("  source: src/architecture_test/verb_suffix_classifier.py")
        w("")

    # Conjugation block — show tokens whose verb form was located in generated paradigm tables.
    conj_tokens = [
        t for t in result.tokens
        if (t.get("conjugation") or {}).get("in_index")
    ]
    if conj_tokens:
        w("─" * 72)
        w("STEP 3.7 — Past-tense conjugation match")
        w("─" * 72)
        for t in conj_tokens:
            conj = t["conjugation"]
            roots_str = " / ".join(conj["roots"])
            persons_str = " or ".join(conj["persons"])
            raw_persons = conj.get("raw_persons") or []
            narrowed = conj.get("narrowed_by_suffix")
            w(f"  {t['surface']} → root={roots_str}  person={persons_str}")
            if narrowed and len(raw_persons) > len(conj["persons"]):
                dropped = [p for p in raw_persons if p not in conj["persons"]]
                w(
                    f"      (narrowed by suffix evidence — "
                    f"dropped: {', '.join(dropped)})"
                )
            elif conj.get("disambiguation_note") and not narrowed and raw_persons:
                w(f"      ({conj['disambiguation_note']})")
            for m in conj["matches"][:2]:
                w(f"      paradigm: {m['past_3sg_m']}  bab: {m['bab']}  masdar: {m['masdar']}")
        w("  source: data/extracted/verb_conjugations_past.csv (sound triliteral, past only)")
        w("")

    # Verb frame semantics block — only if any verb in input has Quranic data.
    verb_tokens_with_frame = [
        t for t in result.tokens
        if (t.get("frame") or {}).get("in_quran")
    ]
    if verb_tokens_with_frame:
        w("─" * 72)
        w("STEP 3.6 — Frame Semantics (from Quranic i'rab corpus)")
        w("─" * 72)
        for t in verb_tokens_with_frame:
            fr = t["frame"]
            roles_str = " | ".join(
                f"{ROLE_DISPLAY.get(d['role'], d['role'])}({d['count']})"
                for d in fr["dominant_roles"]
            )
            w(
                f"  {t['surface']}  ({t['word_class']})  "
                f"→ {fr['occurrences']}x in Quran, {fr['total_args']} args observed"
            )
            w(f"      dominant roles: {roles_str}")
        w("  source: data/extracted/verb_frames_from_quran_i3rab.csv")
        w("")

    w("─" * 72)
    w("STEP 4 — Five state patterns (Q2)")
    w("─" * 72)
    for name in STATE_PATTERNS:
        p = result.state_patterns["patterns"][name]
        flag = p["present"]
        if flag is True:
            status = "YES (strong)" if p.get("strength") == "strong" else "YES"
        elif flag == "partial":
            status = "PARTIAL"
        else:
            status = "no"
        w(f"  {name}: {status}")
        if p.get("reason"):
            w(f"      {p['reason']}")
    w(f"\nDominant: {result.state_patterns['dominant_pattern']}")
    w(f"Discovery: {result.state_patterns['discovery']}")
    w("")

    w("─" * 72)
    w("STEP 5 — Resolution & probability (07)")
    w("─" * 72)
    for row in result.resolution["assignments"]:
        w(
            f"  {row['element']}: {row['designation_degree']} "
            f"({row['factor']})"
        )
    w(f"\n{result.resolution['ontology_note']}")
    w("")

    w("─" * 72)
    w("STEP 6 — Verdict: held / gaps")
    w("─" * 72)
    w("Held:")
    for h in result.verdict["held"]:
        w(f"  + {h}")
    w("\nGaps:")
    for g in result.verdict["gaps"]:
        w(f"  ! [{g['severity']}] {g['id']}: {g['detail']}")
    w(f"\nOverall: {result.verdict['overall']}")
    w("=" * 72)
    return "\n".join(lines)


# Backward-compatible alias
format_sample_01_report = format_architecture_report
