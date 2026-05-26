"""
Architecture test pipeline — six constitutional steps on arbitrary input text.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .aalam_loader import AalamIndex, load_aalam_index
from .analyze_word_adapter import run_analyze_word_step
from .diacritizer_adapter import prepare_vocalized_text
from .conjugation_loader import ConjugationIndex, load_conjugation_index
from .huruf_loader import HurufIndex, load_huruf_index
from .jawamid_loader import JawamidIndex, load_jawamid_index
from .mushtaqat_loader import MushtaqatIndex, load_mushtaqat_index
from .semantic_fields_loader import (
    SemanticFieldsIndex,
    load_semantic_fields_index,
)
from .verb_frames_loader import VerbFramesIndex, load_verb_frames_index
from .verb_suffix_classifier import (
    classify_segmentation_suffixes,
    classify_segmentation_suffixes_with_context,
    conj_persons_from_suffix_infos,
)
from .segmenter_adapter import (
    normalize_summary,
    normalize_text_pre_pipeline,
    segment_tokens,
)
from .tokenize import (
    normalize_input_text,
    token_sequence_label,
    tokenize_text,
    validate_arabic_input,
)

# Alasmaa is optional — degrade gracefully if not installed.
try:
    from .alasmaa_analyzer import AlasmaaAnalyzer, load_alasmaa_analyzer
    _ALASMAA_AVAILABLE = True
except (ImportError, FileNotFoundError):
    _ALASMAA_AVAILABLE = False
    AlasmaaAnalyzer = None  # type: ignore
    load_alasmaa_analyzer = None  # type: ignore

STATE_PATTERNS = [
    "Event-Residue",
    "Event-Continuation",
    "Identity-Pattern",
    "Pure Attribute",
    "Structural-Condition Inducer",
]

LAYER_ORDER = [
    "Sign",
    "Perception",
    "Relation",
    "Event_Transformation",
    "Context",
    "Resolution",
    "Time",
    "Identity",
    "Reasoning",
]

DEFAULT_SAMPLE = {
    "id": "architecture_test_sample_01",
    "reference": "Quran 94:6",
    "text_vocalized": "إِنَّ مَعَ الْعُسْرِ يُسْرًا",
    "prior_context": "94:5 repeats the same sentence",
}


@dataclass
class ArchitectureTestResult:
    sample: dict[str, Any]
    tokens: list[dict[str, Any]]
    diacritization: dict[str, Any]
    normalization: dict[str, Any]
    segmentation: dict[str, Any]
    analyze_word: dict[str, Any]
    meaning_flow: dict[str, Any]
    layers: dict[str, Any]
    huruf_matching: dict[str, Any]
    word_classification: dict[str, Any]
    state_patterns: dict[str, Any]
    resolution: dict[str, Any]
    verdict: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample": self.sample,
            "tokens": self.tokens,
            "diacritization": self.diacritization,
            "normalization": self.normalization,
            "segmentation": self.segmentation,
            "analyze_word": self.analyze_word,
            "meaning_flow": self.meaning_flow,
            "layers": self.layers,
            "huruf_matching": self.huruf_matching,
            "word_classification": self.word_classification,
            "state_patterns": self.state_patterns,
            "resolution": self.resolution,
            "verdict": self.verdict,
        }


def _build_sample_meta(
    text: str,
    *,
    reference: str | None = None,
    context: str | None = None,
    sample_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": sample_id or "architecture_test_input",
        "reference": reference or "(user input)",
        "text_vocalized": text,
        "prior_context": context or "",
        "token_count": len(text.split()),
    }


def _enrich_tokens(
    tokens: list[dict[str, Any]],
    huruf: HurufIndex,
    jawamid: JawamidIndex,
    mushtaqat: MushtaqatIndex,
    aalam: AalamIndex | None = None,
    verb_frames: VerbFramesIndex | None = None,
    sem_fields: SemanticFieldsIndex | None = None,
    conjugations: ConjugationIndex | None = None,
) -> list[dict[str, Any]]:
    """Enrich each token with huruf / jamid / mushtaq matches + word_class decision.

    Reads wazn/root/bab from ``tok["analyze_word"]`` if Step 0 already ran
    (via ``analyze_word_adapter.run_analyze_word_step``). This is the
    authoritative source for derivational analysis when available.

    Layer separation (per 11_Abstraction_Levels.md):
    - All data layers are at the COMPUTATIONAL level.
    - They serve the LINGUISTIC level (classification of اسم vs حرف vs فعل).
    - They do NOT replace the philosophical Entity definition.
    """
    out: list[dict[str, Any]] = []
    for tok_idx, tok in enumerate(tokens):
        surf = tok["surface"]
        plain_no_al = tok.get("plain_no_al", tok["plain"])
        # Peek at next token's definiteness/aalam status for context-aware
        # disambiguation (e.g. رُبَّ vs رَبّ the noun — رُبَّ only enters on نكرة).
        next_tok = tokens[tok_idx + 1] if tok_idx + 1 < len(tokens) else None

        # Harf lookup
        entry = huruf.lookup(surf)
        # Context filter: H090 (رُبَّ) is a literary حرف جر that enters ONLY on
        # an indefinite noun ("ولا تدخل إلا على نكرة غالبًا"). If the next
        # token is معرَّف (al-, or aalam), رَبِّ is the noun (Lord), not the harf.
        # We suppress the harf reading so the downstream classifier can pick up
        # the noun/aalam interpretation. See huruf row H090, notes column.
        if entry is not None and entry.canonical_id == "H090":
            if next_tok is not None and (
                next_tok.get("definiteness") == "definite"
                or next_tok.get("has_al")
            ):
                entry = None  # demote: not the literary رُبَّ in this context
        # Jamid lookup: try surface, then plain_no_al, then salehan stem.
        jamid_cats = jawamid.lookup(surf)
        if not jamid_cats:
            jamid_cats = jawamid.lookup(plain_no_al)
        if not jamid_cats:
            seg = tok.get("segmentation") or {}
            seg_stem = seg.get("stem")
            if seg_stem and seg_stem != surf:
                jamid_cats = jawamid.lookup(seg_stem)
        # Mushtaq pattern matches (only attempt on plausible nouns)
        mushtaq_hits = []
        if not entry and not tok.get("looks_verbal"):
            target = plain_no_al if tok.get("has_al") else tok["plain"]
            mushtaq_hits = mushtaqat.lookup_by_pattern_match(target)

        enriched = {**tok}
        enriched["huruf"] = {
            "in_dataset": entry is not None,
            "canonical_id": entry.canonical_id if entry else None,
            "canonical_form": entry.canonical_form if entry else None,
            "category": entry.category if entry else None,
        }
        enriched["looks_nasikh"] = looks_nasikh(
            surf, entry.category if entry else None
        )
        enriched["jamid"] = {
            "categories": jamid_cats,
            "in_seed": bool(jamid_cats),
        }
        enriched["mushtaq"] = {
            "pattern_matches": [
                {"bab": w.bab, "wazn": w.wazn_voweled, "example": w.example_voweled}
                for w in mushtaq_hits[:3]  # cap to first 3
            ],
            "has_match": bool(mushtaq_hits),
            "babs": sorted({w.bab for w in mushtaq_hits}),
        }

        # Pull wazn/root/bab from Step 0 (analyze_word_adapter) if present.
        aw = tok.get("analyze_word") or {}
        aw_status = aw.get("status")
        aw_operator = (aw_status == "OPERATOR_SKIPPED")
        aw_matched = (aw_status == "MATCHED")
        # Same disambiguation as H090 above — surfaces like رَبِّ / رَبٌّ are in
        # alasmaa's operator catalog (treated as رُبَّ the particle), but in
        # iḍāfa context (next token معرَّف) they're nouns. Demote the operator
        # decision so the downstream classifier picks aalam/jamid/mushtaq.
        # The set is intentionally narrow — only forms that have a clear noun
        # reading and whose operator role requires a نكرة.
        AMBIGUOUS_NOUN_PARTICLES = {"رَبِّ", "رَبَّ", "رَبٌّ", "رَبٍّ", "رب", "ربّ"}
        if (
            aw_operator
            and surf in AMBIGUOUS_NOUN_PARTICLES
            and next_tok is not None
            and (
                next_tok.get("definiteness") == "definite"
                or next_tok.get("has_al")
            )
        ):
            aw_operator = False
        enriched["wazn"] = aw.get("best_wazn") if aw_matched else None
        enriched["root"] = aw.get("extracted_root") if aw_matched else None
        enriched["bab"] = aw.get("bab") if aw_matched else None

        # Aalam (proper noun) lookup — try surface, plain_no_al, and segmented stem.
        aalam_cat = None
        aalam_hits = []
        if aalam is not None:
            for candidate in (surf, plain_no_al, (tok.get("segmentation") or {}).get("stem")):
                if not candidate:
                    continue
                hits = aalam.lookup(candidate)
                if hits:
                    aalam_hits = hits
                    aalam_cat = aalam.category_for(candidate)
                    break
        enriched["aalam"] = {
            "is_aalam": bool(aalam_hits),
            "category": aalam_cat,
            "hit_count": len(aalam_hits),
            "matches": [
                {"plain": h.canonical_plain, "vocalized": h.canonical_vocalized,
                 "category": h.category, "count": h.count}
                for h in aalam_hits[:3]
            ],
        }

        # Decide word_class. Priority (data-authoritative before heuristics):
        #   harf > alasmaa-operator > jamid-seed > AALAM > verb-heuristic
        #     > alasmaa-mushtaq (wazn matched) > pattern-only-mushtaq > unknown
        # Rationale: closed-class data (huruf, operator, jamid seed, aalam) is
        # authoritative. AALAM placed BEFORE verb-heuristic to prevent proper
        # nouns like رَمَضَانَ from being mis-classified as verbs.
        if entry:
            enriched["word_class"] = "harf"
        elif aw_operator:
            enriched["word_class"] = "operator"
        elif jamid_cats:
            enriched["word_class"] = "jamid"
        elif aalam_hits:
            enriched["word_class"] = "aalam"
        elif tok.get("looks_verbal"):
            enriched["word_class"] = "verb"
        elif aw_matched:
            enriched["word_class"] = "mushtaq"
        elif mushtaq_hits:
            enriched["word_class"] = "mushtaq_pattern_only"
        else:
            enriched["word_class"] = "unknown"

        # Frame Semantics lookup for verbs (and verb-like mushtaq forms).
        # The lookup is purely informational and never changes word_class.
        frame_obj = None
        if verb_frames is not None and enriched["word_class"] in ("verb", "mushtaq"):
            # Try surface, segmented stem
            for candidate in (surf, (tok.get("segmentation") or {}).get("stem")):
                if not candidate:
                    continue
                f = verb_frames.lookup(candidate)
                if f is not None:
                    frame_obj = f
                    break
        if frame_obj is not None:
            enriched["frame"] = {
                "in_quran": True,
                "occurrences": frame_obj.occurrences,
                "total_args": frame_obj.total_args,
                "dominant_roles": [
                    {"role": r, "count": c}
                    for r, c in frame_obj.dominant_roles(n=6)
                ],
            }
        else:
            enriched["frame"] = {"in_quran": False}

        # Semantic-field lookup (lexical set membership).
        sem_hits = []
        if sem_fields is not None:
            for candidate in (surf, plain_no_al, (tok.get("segmentation") or {}).get("stem")):
                if not candidate:
                    continue
                hits = sem_fields.lookup(candidate)
                if hits:
                    sem_hits = hits
                    break
        enriched["semantic_fields"] = {
            "in_seed": bool(sem_hits),
            "fields": sorted({h.field_name_ar for h in sem_hits}),
            "members": [
                {
                    "field_ar": h.field_name_ar,
                    "field_en": h.field_name_en,
                    "word": h.word,
                    "metadata": h.metadata,
                }
                for h in sem_hits[:3]
            ],
        }

        # Verb-suffix classification — extract person/number/gender from
        # segmenter-detected suffixes (works even when wazn match fails).
        # Gated by word_class (don't run on aalam/jamid/harf) and uses the
        # stem ending to distinguish نون النسوة (ذَهَبْنَ) from نون الرفع
        # (تَشْكُرُونَ / تَكْتُبِينَ).
        seg = tok.get("segmentation") or {}
        seg_suffixes = seg.get("suffixes") or []
        seg_stem = seg.get("stem") or ""
        suffix_infos = classify_segmentation_suffixes_with_context(
            seg_suffixes,
            stem=seg_stem,
            word_class=enriched.get("word_class"),
        )
        if suffix_infos:
            enriched["verb_suffix"] = {
                "detected": True,
                "infos": [
                    {
                        "suffix": info.suffix,
                        "label_ar": info.label_ar,
                        "person": info.person,
                        "number": info.number,
                        "gender": info.gender,
                        "pronoun_ar": info.pronoun_ar,
                        "ambiguity": info.ambiguity,
                    }
                    for info in suffix_infos
                ],
            }
        else:
            enriched["verb_suffix"] = {"detected": False, "infos": []}

        # Conjugation lookup — only attempt for verb-like forms.
        # Lookup is plain-form (diacritic-stripped) so we have to try
        # several candidates and prefer the one that yields the most
        # specific hit (more persons → less specific, single person → most).
        conj_hits = []
        if conjugations is not None and enriched["word_class"] in ("verb", "mushtaq"):
            seg = tok.get("segmentation") or {}
            stem = seg.get("stem") or ""
            seg_suffixes_raw = seg.get("suffixes") or []
            # Rebuild the prefix-stripped *full* form (stem + suffixes joined).
            # This is what lets ذَهَبُوا (3pl_m) be found instead of falling
            # back to the bare stem ذَهَبُ (which collides with 3sg_m on
            # plain form).
            stem_plus_suffix = stem + "".join(s for s in seg_suffixes_raw if s)
            candidates = [stem_plus_suffix, surf, stem]
            seen: set[str] = set()
            for candidate in candidates:
                if not candidate or candidate in seen:
                    continue
                seen.add(candidate)
                hits = conjugations.lookup_by_form(candidate)
                if hits:
                    conj_hits = hits
                    break

        # Disambiguate conjugation persons using suffix evidence (Step 3.65).
        # Surface-form lookup is many-to-one in past tense (e.g. كَتَبْتُ matches
        # 1sg/2sg_m/2sg_f/3sg_f because all four share the same plain form).
        # The vocalized suffix tells us which of those persons is actually present.
        allowed_persons = conj_persons_from_suffix_infos(suffix_infos)
        if conj_hits and allowed_persons:
            filtered = [h for h in conj_hits if h["person"] in allowed_persons]
            if filtered:
                conj_hits_disambig = filtered
                disambig_note = (
                    "narrowed by Step 3.65 suffix evidence → "
                    + ", ".join(sorted({h["person"] for h in filtered}))
                )
            else:
                # Suffix says X but no paradigm row matched that person — keep
                # the raw hits and flag the conflict.
                conj_hits_disambig = conj_hits
                disambig_note = (
                    "suffix evidence (" + ", ".join(allowed_persons)
                    + ") did not intersect form-matched persons; kept raw hits"
                )
        else:
            conj_hits_disambig = conj_hits
            disambig_note = (
                "no suffix evidence — persons left ambiguous"
                if conj_hits else ""
            )

        enriched["conjugation"] = {
            "in_index": bool(conj_hits),
            # Unique roots that matched (form may collide across persons/bābs)
            "roots": sorted({h["root"] for h in conj_hits_disambig}),
            "persons": sorted({h["person"] for h in conj_hits_disambig}),
            "matches": conj_hits_disambig[:4],  # cap
            "raw_persons": sorted({h["person"] for h in conj_hits}),
            "disambiguation_note": disambig_note,
            "narrowed_by_suffix": bool(
                conj_hits and allowed_persons
                and any(h["person"] in allowed_persons for h in conj_hits)
            ),
        }

        out.append(enriched)
    return out


def looks_nasikh(surface: str, huruf_category: str | None) -> bool:
    from .tokenize import looks_nasikh as _ln

    return _ln(surface, huruf_category)


def _step_meaning_flow(tokens: list[dict[str, Any]], sample: dict[str, Any]) -> dict[str, Any]:
    seq = token_sequence_label(tokens)
    nasikh = [t for t in tokens if t.get("looks_nasikh")]
    ma_tok = next((t for t in tokens if t.get("is_ma_accompaniment")), None)
    def_toks = [t for t in tokens if t.get("definiteness") == "definite"]
    indef = [t for t in tokens if t.get("definiteness") == "indefinite"]
    verbal = [t for t in tokens if t.get("looks_verbal")]

    attention = [f"Lexical sequence ({len(tokens)} units): {seq}"]
    if nasikh:
        attention.append(
            f"Opening / embedded nasikh-like particle(s): "
            + ", ".join(t["surface"] for t in nasikh)
        )
    if ma_tok:
        attention.append(f"Accompaniment operator: {ma_tok['surface']}")
    if def_toks and indef:
        attention.append(
            "Definite vs indefinite contrast: "
            + ", ".join(t["surface"] for t in def_toks)
            + " vs "
            + ", ".join(t["surface"] for t in indef)
        )
    if verbal:
        attention.append(
            "Verbal morphology detected: " + ", ".join(t["surface"] for t in verbal)
        )

    if nasikh and not verbal:
        conception = "Nominal / operator-headed composition (nasikh present, no clear finite verb)"
    elif verbal:
        conception = "Clause with verbal nucleus — event-bearing structure possible"
    else:
        conception = "Static lexical composition — rule or description without clear event nucleus"

    possibilities = []
    if ma_tok:
        possibilities.append(
            f"Is {ma_tok['surface']} locative, temporal, or purely relational accompaniment?"
        )
    if len(tokens) >= 2 and nasikh:
        possibilities.append("What is ism vs khabar under nasikh assignment?")
    if def_toks and indef:
        possibilities.append("Does al- mark genus, deixis, or prior mention?")
        possibilities.append("Does tanwin mark indefiniteness, type, or multiplicity?")

    evidence = []
    for t in nasikh:
        evidence.append(f"{t['surface']}: huruf/nasikh behavior imposes clausal structure")
    for t in tokens:
        if t.get("has_al"):
            evidence.append(f"{t['surface']}: definite (al-) — often genus or known referent")
        if t.get("has_tanwin"):
            evidence.append(f"{t['surface']}: tanwin — indefiniteness / type reading")
        if t.get("case_hint") != "unknown":
            evidence.append(f"{t['surface']}: surface case hint = {t['case_hint']}")

    relations = []
    for t in nasikh:
        relations.append(f"{t['surface']} → structural operator on clause")
    if ma_tok:
        relations.append(f"{ma_tok['surface']} → accompaniment between surrounding bearers")
    for t in def_toks + indef:
        relations.append(f"{t['surface']} → lexical bearer (definiteness={t['definiteness']})")

    weighing = (
        f"Weighted reading follows surface order and morphology on: {seq}. "
        + (sample.get("prior_context") or "No external context supplied.")
    )

    designation = {
        t["plain"]: f"definiteness={t['definiteness']}, case_hint={t['case_hint']}"
        for t in tokens
        if t.get("definiteness") != "unknown" or t.get("case_hint") != "unknown"
    }

    meaning = (
        "Compositional meaning built from operators + bearers in input order "
        "(no tafsir beyond structural linguistics)"
    )

    inference = []
    if ma_tok and len(tokens) >= 3:
        inference.append("Accompaniment links hardship/ease-like bearers if present — co-presence reading")
    if nasikh and not verbal:
        inference.append("Without event nucleus, reading tends toward rule-statement not narrative event")

    understanding = (
        f"Structural understanding of input ({len(tokens)} units): "
        + ("operator-headed static rule" if nasikh and not verbal else "mixed / verbal clause")
    )

    return {
        "path": [
            "sign",
            "attention",
            "initial_conception",
            "possibility_space",
            "evidence_gathering",
            "relation_building",
            "weighing",
            "designation",
            "meaning_construction",
            "inference",
            "understanding",
        ],
        "sign_attention": attention,
        "initial_conception": conception,
        "possibilities": possibilities or ["(no major structural ambiguities flagged heuristically)"],
        "evidence": evidence or ["(minimal surface evidence — undiacritized or sparse input)"],
        "relations": relations or ["(no relations inferred)"],
        "weighing": weighing,
        "designation": designation,
        "meaning": meaning,
        "inference": inference or ["(no extra inference recorded)"],
        "understanding": understanding,
    }


def _step_layers(tokens: list[dict[str, Any]], sample: dict[str, Any]) -> dict[str, Any]:
    verbal = any(t.get("looks_verbal") for t in tokens)
    nasikh = any(t.get("looks_nasikh") for t in tokens)
    ma = any(t.get("is_ma_accompaniment") for t in tokens)
    has_def = any(t.get("definiteness") == "definite" for t in tokens)
    has_indef = any(t.get("definiteness") == "indefinite" for t in tokens)

    event_status = (
        "ACTIVE — verbal morphology detected"
        if verbal
        else "INACTIVE — no clear finite verb; nominal/static composition"
    )

    assignments = {
        "Sign": f"{len(tokens)} vocalized units + diacritics/marks as present in input",
        "Perception": (
            "Nasikh vs plain; definite vs indefinite; operator vs bearer "
            "(heuristic from surface)"
        ),
        "Relation": (
            ("Nasikh/operator relations; " if nasikh else "")
            + ("مع accompaniment; " if ma else "")
            + "inter-token order preserved"
        ).strip("; ") or "Order and juxtaposition only",
        "Event_Transformation": event_status,
        "Context": sample.get("prior_context") or "(none supplied)",
        "Resolution": (
            "Definite/indefinite and case hints mapped per token"
            if (has_def or has_indef)
            else "Resolution thin — no clear def/indef markers"
        ),
        "Time": (
            "Verbal input may carry tense; otherwise timeless/rule-like"
            if verbal
            else "No explicit tense; static rule reading possible"
        ),
        "Identity": (
            "Definite tokens lean genus/referent; indefinite toward type/multiplicity"
            if has_def and has_indef
            else "Identity layer weakly triggered"
        ),
        "Reasoning": (
            "Cross-token constraints from operators and def/indef pattern"
            if (nasikh or ma or (has_def and has_indef))
            else "Limited cross-token reasoning"
        ),
    }

    inactive = [] if verbal else ["Event_Transformation"]
    active = [layer for layer in LAYER_ORDER if layer not in inactive]

    return {
        "assignments": assignments,
        "active_layers": active,
        "inactive_layers": inactive,
        "structural_note": (
            "Event layer dormant on static texts — valid per architecture (not failure)"
            if not verbal
            else "Verbal nucleus activates Event/Transformation"
        ),
    }


def _step_huruf(tokens: list[dict[str, Any]], huruf: HurufIndex) -> dict[str, Any]:
    elements: list[dict[str, Any]] = []

    for tok in tokens:
        surf = tok["surface"]
        rep = huruf.match_report(surf)
        rep["element"] = surf
        rep["role_in_text"] = tok.get("huruf", {}).get("category") or "lexical bearer"
        elements.append(rep)

        if tok.get("has_al"):
            elements.append(
                {
                    "element": f"ال (in {surf})",
                    "type": "definite_article",
                    "in_dataset": False,
                    "note": "definiteness marker; not a standalone huruf row",
                }
            )
        if tok.get("has_tanwin"):
            elements.append(
                {
                    "element": f"تنوين (in {surf})",
                    "type": "tanwin",
                    "in_dataset": False,
                    "note": "indefiniteness / case marking; not in huruf catalog",
                }
            )
        if tok.get("is_ma_accompaniment") and not rep.get("in_dataset"):
            elements.append(
                {
                    "element": surf,
                    "in_dataset": False,
                    "gap": "مع — accompaniment operator outside huruf_maani_unified_master",
                }
            )

    outside = [e for e in elements if not e.get("in_dataset")]
    in_ds = sum(1 for e in elements if e.get("in_dataset"))

    gap_statement = (
        f"{len(outside)} surface factor(s) outside huruf dataset "
        f"({in_ds} huruf hit(s) on {len(tokens)} token(s)) — "
        "catalog is classical huruf, not all quasi-harf operators"
    )

    return {
        "elements": elements,
        "in_dataset_count": in_ds,
        "outside_dataset_count": len(outside),
        "outside_dataset": [e["element"] for e in outside],
        "gap_statement": gap_statement,
    }


def _step_word_classification(tokens: list[dict[str, Any]]) -> dict[str, Any]:
    """Step (new): اسم وفعل وحرف — distribute tokens across the three classical classes.

    Computational realization of the classical Arabic distinction
    (الكلام = اسم وفعل وحرف). Each token is placed in one of:
      - harf (matched in huruf dataset)
      - verb (surface-heuristic verbal morphology)
      - jamid (matched in jawamid seed table)
      - mushtaq (matches a derivational wazn from mushtaqat table)
      - unknown (none of the above triggered)

    This step bridges:
      - data/الجوامد.xlsx (jamid seed examples)
      - data/Mushtaqat_Weights_Final_Corrected_With_Fa3l-minimall.xlsx (derivational patterns)
      - huruf_maani_normalization/huruf_maani_unified_master.xlsx (huruf canonical)

    Layer note (per 11_Abstraction_Levels.md):
      This is a COMPUTATIONAL step that serves the LINGUISTIC classification of
      الاسم/الفعل/الحرف. It does NOT replace the philosophical Entity definition.
    """
    counts: dict[str, int] = {
        "harf": 0, "verb": 0, "operator": 0, "jamid": 0, "aalam": 0,
        "mushtaq": 0, "mushtaq_pattern_only": 0, "unknown": 0,
    }
    per_token: list[dict[str, Any]] = []
    jamid_categories_seen: set[str] = set()
    mushtaq_babs_seen: set[str] = set()
    roots_extracted: set[str] = set()
    aalam_categories_seen: set[str] = set()

    for tok in tokens:
        cls = tok.get("word_class", "unknown")
        counts[cls] = counts.get(cls, 0) + 1
        if cls == "jamid":
            jamid_categories_seen.update(tok.get("jamid", {}).get("categories", []))
        if cls == "aalam":
            cat = (tok.get("aalam") or {}).get("category")
            if cat:
                aalam_categories_seen.add(cat)
        if cls == "mushtaq":
            bab = tok.get("bab")
            if bab:
                mushtaq_babs_seen.add(bab)
            root = tok.get("root")
            if root:
                roots_extracted.add(root)
        if cls == "mushtaq_pattern_only":
            mushtaq_babs_seen.update(tok.get("mushtaq", {}).get("babs", []))
        per_token.append(
            {
                "element": tok["surface"],
                "word_class": cls,
                "wazn": tok.get("wazn"),
                "root": tok.get("root"),
                "bab": tok.get("bab"),
                "jamid_categories": tok.get("jamid", {}).get("categories", []),
                "mushtaq_babs": tok.get("mushtaq", {}).get("babs", []),
                "huruf_canonical_id": tok.get("huruf", {}).get("canonical_id"),
                "aalam_category": (tok.get("aalam") or {}).get("category"),
            }
        )

    coverage_pct = (
        round(100 * (len(tokens) - counts["unknown"]) / len(tokens), 1) if tokens else 0.0
    )

    return {
        "per_token": per_token,
        "class_counts": counts,
        "jamid_categories_seen": sorted(jamid_categories_seen),
        "aalam_categories_seen": sorted(aalam_categories_seen),
        "mushtaq_babs_seen": sorted(mushtaq_babs_seen),
        "roots_extracted": sorted(roots_extracted),
        "coverage_pct": coverage_pct,
        "data_sources": {
            "harf": "huruf_maani_normalization/huruf_maani_unified_master.xlsx",
            "jamid": "data/الجوامد.xlsx",
            "aalam": "data/extracted/aalam_from_masaq.csv",
            "mushtaq_table": "data/Mushtaqat_Weights_Final_Corrected_With_Fa3l-minimall.xlsx",
            "alasmaa_weights": "/Users/husseinhiyassat/fractal/alasmaa/Mushtaqat_Weights_Final_Corrected_With_Fa3ll.xlsx",
            "alasmaa_analyzer": "/Users/husseinhiyassat/fractal/alasmaa/analyze_word.py",
        },
        "layer_note": (
            "Computational classification (per 11_Abstraction_Levels.md). "
            "Serves linguistic level; does not replace philosophical Entity definition. "
            "Wazn + root extraction via alasmaa/analyze_word.py. "
            "Proper-noun classification via MASAQ-extracted aalam_from_masaq.csv."
        ),
    }


def _step_state_patterns(tokens: list[dict[str, Any]]) -> dict[str, Any]:
    verbal = [t for t in tokens if t.get("looks_verbal")]
    nasikh = [t for t in tokens if t.get("looks_nasikh")]
    nouns = [t for t in tokens if not t.get("looks_verbal") and not t.get("huruf", {}).get("in_dataset")]

    patterns: dict[str, Any] = {
        "Event-Residue": {
            "present": False,
            "locus": None,
            "reason": "No clear event-residue morphology (passive participle etc.) detected",
        },
        "Event-Continuation": {
            "present": bool(verbal),
            "locus": ", ".join(t["surface"] for t in verbal) if verbal else None,
            "reason": "Verbal nucleus suggests ongoing or event-bearing clause" if verbal else "No ongoing event",
            "strength": "moderate" if verbal else None,
        },
        "Identity-Pattern": {
            "present": "partial" if nouns else False,
            "locus": ", ".join(t["surface"] for t in nouns[:4]) if nouns else None,
            "reason": "Nominal bearers may carry kind-identity readings",
        },
        "Pure Attribute": {
            "present": False,
            "locus": None,
            "reason": "No dedicated adjectival predicate pattern detected heuristically",
        },
        "Structural-Condition Inducer": {
            "present": bool(nasikh),
            "locus": ", ".join(t["surface"] for t in nasikh) if nasikh else None,
            "reason": "Nasikh / operator imposes structural clause condition" if nasikh else "No nasikh detected",
            "strength": "strong" if nasikh else None,
        },
    }

    dominant = None
    if nasikh:
        dominant = "Structural-Condition Inducer"
    elif verbal:
        dominant = "Event-Continuation"
    elif nouns:
        dominant = "Identity-Pattern (partial)"

    return {
        "patterns": patterns,
        "dominant_pattern": dominant or "(none strong)",
        "discovery": "Not all five patterns expected in every text — record what appears",
    }


def _step_resolution(tokens: list[dict[str, Any]]) -> dict[str, Any]:
    assignments = []
    for t in tokens:
        h = t.get("huruf") or {}
        if h.get("in_dataset"):
            degree = "fully_determined"
            factor = f"huruf match {h.get('canonical_id')}"
        elif t.get("looks_nasikh"):
            degree = "fully_determined"
            factor = "nasikh surface form"
        elif t.get("is_ma_accompaniment"):
            degree = "contextually_determined"
            factor = "accompaniment reading from context"
        elif t.get("definiteness") == "definite":
            degree = "genus_or_referent"
            factor = "definite al-"
        elif t.get("definiteness") == "indefinite":
            degree = "type_level"
            factor = "tanwin / indefiniteness"
        else:
            degree = "underdetermined"
            factor = "sparse surface markers"

        assignments.append(
            {
                "element": t["surface"],
                "designation_degree": degree,
                "factor": factor,
            }
        )

    def_indef = (
        sum(1 for t in tokens if t.get("definiteness") == "definite"),
        sum(1 for t in tokens if t.get("definiteness") == "indefinite"),
    )

    return {
        "assignments": assignments,
        "ontology_note": (
            f"Definite tokens: {def_indef[0]}, indefinite: {def_indef[1]} — "
            "Resolution + Identity layers scale with these markers"
        ),
        "balagha_unrepresented": (
            "Word-order rhetoric (tقديم/تأخير) not a dedicated layer in current archive"
        ),
    }


def _step_verdict(
    huruf: dict[str, Any],
    layers: dict[str, Any],
    tokens: list[dict[str, Any]],
) -> dict[str, Any]:
    held = [
        "Layer-centric decomposition applied to input tokens without manual retrofit",
        "Meaning flow path (03) executed on supplied text",
        "Huruf dataset consulted per token surface",
        "Five Q2 patterns scored from surface heuristics",
        "Resolution recorded per token",
    ]
    gaps: list[dict[str, Any]] = []

    if huruf["outside_dataset_count"]:
        gaps.append(
            {
                "id": "huruf_dataset_coverage",
                "severity": "medium",
                "detail": huruf["gap_statement"],
                "elements": huruf["outside_dataset"],
            }
        )

    if "Event_Transformation" in layers["inactive_layers"]:
        gaps.append(
            {
                "id": "event_layer_dormant_on_static_texts",
                "severity": "low",
                "detail": (
                    "Event/Transformation inactive — valid for static/rule-like inputs"
                ),
            }
        )

    if any(t.get("is_ma_accompaniment") for t in tokens):
        gaps.append(
            {
                "id": "accompaniment_relation_untyped",
                "severity": "medium",
                "detail": (
                    "مع present — accompaniment subtype (temporal/spatial/logical) not distinguished"
                ),
            }
        )

    if not any(t.get("looks_verbal") for t in tokens) and len(tokens) <= 6:
        gaps.append(
            {
                "id": "universal_rule_vs_particular_case",
                "severity": "medium",
                "detail": (
                    "Short static input may be universal rule — not yet a first-class distinction"
                ),
            }
        )

    overall = (
        "Architecture pipeline completed on input; gaps recorded explicitly (no constitutional expansion)"
    )

    return {
        "held": held,
        "gaps": gaps,
        "overall": overall,
        "inactive_layers": layers["inactive_layers"],
    }


def run_architecture_test(
    text: str,
    *,
    reference: str | None = None,
    context: str | None = None,
    sample_id: str | None = None,
    huruf_path: Path | None = None,
    jawamid_path: Path | None = None,
    mushtaqat_path: Path | None = None,
    weights_path: Path | None = None,
    weights_sheet: str = "الأوزان_المصححة",
    skip_analyze_word: bool = False,
    skip_normalize: bool = False,
    skip_segment: bool = False,
    gpt52_dir: Path | None = None,
    skip_diacritize: bool = False,
    force_diacritize: bool = False,
) -> ArchitectureTestResult:
    """Run all steps on ``text`` (Arabic, vocalized preferred).

    Step −2: ``salehan/Models_gpt52`` diacritization when input is unvocalized.
    Step −1: ``new_arabic_analyzer/normalize.py`` (NFC + آ → ءَ) on full text.
    Step  0a: ``salehan/segmenter.py`` per token (prefix/stem/suffix peeling).
    Step  0b: ``alasmaa/analyze_word.py`` Mushtaqat wazn per token (also tries stem).
    Then loads huruf / jamid / mushtaqat indices for the constitutional steps.
    """
    original_input = text
    text, diac_block = prepare_vocalized_text(
        text,
        gpt52_dir=gpt52_dir,
        skip_diacritize=skip_diacritize,
        force_diacritize=force_diacritize,
    )

    # Step −1: pre-pipeline normalize (full text).
    if skip_normalize:
        normalized_text = text
        norm_block: dict[str, Any] = {"skipped": True}
    else:
        normalized_text = normalize_text_pre_pipeline(text)
        norm_block = {
            **normalize_summary(),
            "input_text": text,
            "normalized_text": normalized_text,
            "changed": normalized_text != text,
        }

    clean = validate_arabic_input(normalized_text)
    raw_tokens = tokenize_text(clean)

    # Step 0a: salehan segmenter per token.
    if skip_segment:
        seg_block: dict[str, Any] = {"skipped": True}
        tokens_after_seg = raw_tokens
    else:
        tokens_after_seg, seg_block = segment_tokens(raw_tokens)

    # Step 0b: alasmaa analyze_word per token (still on full surface;
    # also tries the salehan stem if the surface fails).
    if skip_analyze_word:
        analyze_word_step: dict[str, Any] = {"skipped": True}
        tokens_pre = tokens_after_seg
    else:
        tokens_pre, analyze_word_step = run_analyze_word_step(
            tokens_after_seg,
            weights_path=weights_path,
            sheet=weights_sheet,
        )
        # Stem fallback: if surface yielded NO_WAZN but salehan provided a
        # different stem, retry analyze_word against the stem.
        tokens_pre = _retry_analyze_word_on_stem(
            tokens_pre,
            weights_path=weights_path,
            sheet=weights_sheet,
        )

    huruf = load_huruf_index(huruf_path)
    jawamid = load_jawamid_index(jawamid_path)
    mushtaqat = load_mushtaqat_index(mushtaqat_path)
    try:
        aalam = load_aalam_index()
    except FileNotFoundError:
        aalam = None
    try:
        verb_frames = load_verb_frames_index()
    except FileNotFoundError:
        verb_frames = None
    try:
        sem_fields = load_semantic_fields_index()
    except FileNotFoundError:
        sem_fields = None
    try:
        conjugations = load_conjugation_index()
    except FileNotFoundError:
        conjugations = None
    tokens = _enrich_tokens(
        tokens_pre, huruf, jawamid, mushtaqat,
        aalam=aalam, verb_frames=verb_frames, sem_fields=sem_fields,
        conjugations=conjugations,
    )
    sample = _build_sample_meta(
        clean,
        reference=reference,
        context=context,
        sample_id=sample_id,
    )
    sample["text_vocalized"] = clean
    sample["original_input"] = original_input
    sample["text_after_diacritization"] = text

    layers = _step_layers(tokens, sample)
    huruf_step = _step_huruf(tokens, huruf)
    word_class_step = _step_word_classification(tokens)

    return ArchitectureTestResult(
        sample=sample,
        tokens=tokens,
        diacritization=diac_block,
        normalization=norm_block,
        segmentation=seg_block,
        analyze_word=analyze_word_step,
        meaning_flow=_step_meaning_flow(tokens, sample),
        layers=layers,
        huruf_matching=huruf_step,
        word_classification=word_class_step,
        state_patterns=_step_state_patterns(tokens),
        resolution=_step_resolution(tokens),
        verdict=_step_verdict(huruf_step, layers, tokens),
    )


def _retry_analyze_word_on_stem(
    tokens: list[dict[str, Any]],
    *,
    weights_path: Path | None,
    sheet: str,
) -> list[dict[str, Any]]:
    """For tokens with NO_WAZN, try analyze_word on the salehan stem.

    Updates tok['analyze_word'] in place if stem analysis succeeds.
    """
    from .analyze_word_adapter import (
        analyze_token_surface,
        load_analyze_word_module,
        load_mushtaqat_weights,
    )

    needs_retry = [
        t for t in tokens
        if t.get("analyze_word", {}).get("status") == "NO_WAZN"
        and t.get("segmentation", {}).get("segmented")
        and t.get("segmentation", {}).get("stem")
        and t["segmentation"]["stem"] != t["surface"]
    ]
    if not needs_retry:
        return tokens

    mod = load_analyze_word_module()
    weights = load_mushtaqat_weights(mod, weights_path, sheet=sheet)

    for tok in needs_retry:
        stem = tok["segmentation"]["stem"]
        stem_res = analyze_token_surface(mod, weights, stem)
        if stem_res.get("status") == "MATCHED":
            old = tok["analyze_word"]
            tok["analyze_word"] = {
                **stem_res,
                "via_stem": True,
                "stem_used": stem,
                "surface_status": old.get("status"),
            }
    return tokens


def run_sample_01(
    *,
    huruf_path: Path | None = None,
    jawamid_path: Path | None = None,
    mushtaqat_path: Path | None = None,
    weights_path: Path | None = None,
    weights_sheet: str = "الأوزان_المصححة",
    skip_analyze_word: bool = False,
    gpt52_dir: Path | None = None,
    skip_diacritize: bool = False,
    force_diacritize: bool = False,
) -> ArchitectureTestResult:
    """Default locked Sample 01 (Quran 94:6)."""
    return run_architecture_test(
        DEFAULT_SAMPLE["text_vocalized"],
        reference=DEFAULT_SAMPLE["reference"],
        context=DEFAULT_SAMPLE["prior_context"],
        sample_id=DEFAULT_SAMPLE["id"],
        huruf_path=huruf_path,
        jawamid_path=jawamid_path,
        mushtaqat_path=mushtaqat_path,
        weights_path=weights_path,
        weights_sheet=weights_sheet,
        skip_analyze_word=skip_analyze_word,
        gpt52_dir=gpt52_dir,
        skip_diacritize=skip_diacritize,
        force_diacritize=force_diacritize,
    )
