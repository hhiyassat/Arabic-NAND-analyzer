"""meaning_card_builder.py — تَجميع SemanticClaims في MeaningCards.

نَهج open-ended:
  • نَجمَع claims مُتَقارِبَة في صَفحَة/فَقرَة/topic واحِد
  • نُحَدِّد engine_applicability بِناءً على نَوع claim
  • نُنتِج بِطاقات بِأَيّ عَدَد — لا حَدّ

التَّجميع:
  1. Topic-based: claims مُتَّفِقَة في topic + claim_type → bunch
  2. Page-locality: claims مُتَقارِبَة (في نَفس الفَقرَة) تَدخُل بِطاقَة واحِدَة
  3. Trigger-based: claims تَشتَرِك في lemma/particle تَدخُل بِطاقَة واحِدَة

engine_applicability:
  • direct_rule: قاعِدَة قابِلَة لِتَطبيق مُباشِر (مَع triggers + pattern)
  • heuristic_rule: قاعِدَة احتِماليَّة (probabilistic_rule, conditional_rule)
  • interpretive_note: مُلاحَظَة تَفسيريَّة (opinion, author_preference, denial)
  • review_only: ثِقَة مُنخَفِضَة → مُراجَعَة يَدَويَّة
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

import sys
_HERE = Path(__file__).resolve().parent
_KB = _HERE.parent
sys.path.insert(0, str(_KB))
from grammar_kb.models import MeaningCard


# تَوزيع claim_type → engine_applicability + meaning_type
TYPE_MAPPING = {
    "syntactic_semantic_rule": ("construction_meaning", "direct_rule"),
    "syntactic_effect":         ("syntactic_effect", "direct_rule"),
    "semantic_effect":          ("semantic_effect", "heuristic_rule"),
    "semantic_distinction":     ("distinction", "heuristic_rule"),
    "particle_meaning":         ("particle_meaning", "direct_rule"),
    "preposition_meaning":      ("preposition_meaning", "direct_rule"),
    "preposition_distinction":  ("preposition_distinction", "heuristic_rule"),
    "modality":                 ("modality", "heuristic_rule"),
    "discourse_meaning":        ("discourse_meaning", "interpretive_note"),
    "reference_meaning":        ("reference_meaning", "heuristic_rule"),
    "number_counted_meaning":   ("number_counted_meaning", "direct_rule"),
    "tadmeen":                  ("tadmeen", "heuristic_rule"),
    "quranic_usage":            ("quranic_usage", "interpretive_note"),
    "opinion":                  ("opinion", "interpretive_note"),
    "author_preference":        ("author_preference", "interpretive_note"),
    "exception":                ("exception", "heuristic_rule"),
    "warning":                  ("warning", "interpretive_note"),
    "ambiguity":                ("ambiguity", "interpretive_note"),
    "probabilistic_rule":       ("probabilistic_rule", "heuristic_rule"),
    "conditional_rule":         ("conditional_rule", "heuristic_rule"),
    "contrast_rule":            ("distinction", "heuristic_rule"),
    "permission":               ("syntactic_effect", "heuristic_rule"),
    "denial_of_misreading":     ("warning", "interpretive_note"),
}


def _cluster_key(claim: dict) -> tuple:
    """مِفتاح التَّجميع: (part, topic_id, claim_type, primary_trigger)."""
    part = claim.get("part")
    topic_id = claim.get("topic_id") or ""
    ct = claim.get("claim_type")
    triggers = claim.get("triggers") or {}
    lemma = ""
    particle = ""
    if isinstance(triggers, dict):
        lemmas = triggers.get("lemmas") or []
        if lemmas:
            lemma = lemmas[0]
        particles = triggers.get("particles") or []
        if particles:
            particle = particles[0]
    return (part, topic_id, ct, lemma, particle)


def _summarize_claims(claims: list[dict]) -> str:
    """يُرَكِّب وَصفًا مُجَمَّعًا مِن claims."""
    # نَأخُذ أَطول 3 normalized_claims مَع الفِلتَر
    texts = [c.get("normalized_claim") or c.get("cleaned_excerpt", "")
             for c in claims if c.get("normalized_claim")]
    texts = sorted(set(texts), key=lambda s: -len(s))[:3]
    return " — ".join(texts)


def _aggregate_triggers(claims: list[dict]) -> dict:
    lemmas, particles = set(), set()
    for c in claims:
        t = c.get("triggers") or {}
        if isinstance(t, dict):
            for l in t.get("lemmas") or []:
                lemmas.add(l)
            for p in t.get("particles") or []:
                particles.add(p)
    out = {}
    if lemmas:
        out["lemmas"] = sorted(lemmas)
    if particles:
        out["particles"] = sorted(particles)
    return out


def _aggregate_examples(claims: list[dict]) -> list[dict]:
    seen_texts = set()
    out = []
    for c in claims:
        for ex in c.get("examples_mentioned") or []:
            ex_clean = ex.strip()
            if ex_clean in seen_texts or len(ex_clean) < 3:
                continue
            seen_texts.add(ex_clean)
            example = {"text": ex_clean}
            # هَل في الـ claim مَرجِع قُرآنيّ؟
            for q in c.get("quran_refs") or []:
                if isinstance(q, dict):
                    example["quran_ref"] = q
                    break
            out.append(example)
    return out[:8]


def _aggregate_quran_refs(claims: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for c in claims:
        for q in c.get("quran_refs") or []:
            if isinstance(q, dict):
                key = (q.get("surah"), q.get("ayah_str"))
                if key in seen:
                    continue
                seen.add(key)
                out.append(q)
    return out


def _make_title(claims: list[dict], key: tuple) -> str:
    part, topic_id, ct, lemma, particle = key
    topic_title = ""
    for c in claims:
        if c.get("topic_title"):
            topic_title = c["topic_title"]
            break
    type_ar = {
        "semantic_distinction": "تَمييز دَلاليّ",
        "particle_meaning": "مَعنى أَداة",
        "preposition_meaning": "مَعنى حَرف جَرّ",
        "syntactic_effect": "أَثَر نَحويّ",
        "semantic_effect": "أَثَر دَلاليّ",
        "modality": "جِهَة",
        "tadmeen": "تَضمين",
        "opinion": "نَقل خِلاف",
        "author_preference": "تَرجيح المُؤَلِّف",
        "exception": "استِثناء",
        "warning": "تَحذير",
        "ambiguity": "احتِمال",
        "probabilistic_rule": "قاعِدَة احتِماليَّة",
        "conditional_rule": "قاعِدَة شَرطيَّة",
        "contrast_rule": "تَقابُل",
        "permission": "جَواز",
        "denial_of_misreading": "نَفي فَهم خاطِئ",
        "quranic_usage": "استِشهاد قُرآنيّ",
        "discourse_meaning": "خِطاب",
        "reference_meaning": "إِحالَة",
        "number_counted_meaning": "عَدَد وَ مَعدود",
    }.get(ct, ct)
    parts_title = [type_ar]
    if topic_title:
        parts_title.append(f"في «{topic_title}»")
    if lemma:
        parts_title.append(f"حَول الفِعل «{lemma}»")
    elif particle:
        parts_title.append(f"حَول «{particle}»")
    return " — ".join(parts_title)


def build_meaning_cards(claims: list[dict]) -> list[MeaningCard]:
    """يَجمَع claims في cards بِناءً على cluster_key."""
    clusters: dict[tuple, list[dict]] = defaultdict(list)
    for c in claims:
        clusters[_cluster_key(c)].append(c)

    cards: list[MeaningCard] = []
    for key, cluster in clusters.items():
        part, topic_id, ct, lemma, particle = key
        if not cluster:
            continue
        # نَأخُذ أَعلى ثِقَة كَ confidence لِلبِطاقَة
        max_conf = max(c.get("confidence", 0) for c in cluster)
        avg_conf = sum(c.get("confidence", 0) for c in cluster) / len(cluster)
        meaning_type, applicability = TYPE_MAPPING.get(
            ct, ("interpretive_note", "interpretive_note")
        )
        # إِذا الثِّقَة مُنخَفِضَة جِدًّا → review_only
        if avg_conf < 0.55:
            applicability = "review_only"

        # source_refs مِن أَوَّل صَفحَة وَ آخِر صَفحَة
        pages_used = sorted(set(c.get("page") for c in cluster if c.get("page")))
        source_ref = {
            "book": "معاني النحو",
            "author": "فاضل صالح السامرائي",
            "part": part,
            "page_start": pages_used[0] if pages_used else 0,
            "page_end": pages_used[-1] if pages_used else 0,
        }

        # topic_path
        topic_path = []
        topic_title = next((c.get("topic_title") for c in cluster if c.get("topic_title")), None)
        if topic_title:
            topic_path.append(topic_title)
        if lemma:
            topic_path.append(lemma)
        elif particle:
            topic_path.append(particle)

        # warnings/exceptions/conditions
        warnings = [c.get("normalized_claim", "")[:200] for c in cluster
                    if c.get("claim_type") in ("warning", "denial_of_misreading")]
        exceptions = [c.get("normalized_claim", "")[:200] for c in cluster
                      if c.get("claim_type") == "exception"]

        # author_position
        author_positions = [c.get("author_position") for c in cluster if c.get("author_position")]

        card_id_parts = [
            f"MEAN_P{part}",
            ct.upper(),
            topic_id.split("__")[0] if topic_id else "GEN",
            (lemma or particle or "X")[:20],
        ]
        meaning_id = "_".join(card_id_parts)
        # تَنظيف الـ id
        import re as _re
        meaning_id = _re.sub(r'[^\w؀-ۿ_]+', '_', meaning_id)

        card = MeaningCard(
            meaning_id=meaning_id,
            title=_make_title(cluster, key),
            meaning_type=meaning_type,
            topic_path=topic_path,
            description=_summarize_claims(cluster),
            syntactic_effect={},  # يُملَأ مِن heuristic أَدناه
            semantic_effect={},
            triggers=_aggregate_triggers(cluster),
            conditions=[c.get("normalized_claim", "")[:200] for c in cluster
                        if c.get("claim_type") == "conditional_rule"],
            exceptions=exceptions,
            warnings=warnings,
            examples=_aggregate_examples(cluster),
            source_claims=[c.get("claim_id") for c in cluster if c.get("claim_id")],
            source_refs=[source_ref],
            engine_applicability=applicability,
            confidence=round(max_conf, 2),
            needs_manual_review=(avg_conf < 0.6),
        )
        # source_refs إِضافيَّة (آيات)
        quran = _aggregate_quran_refs(cluster)
        if quran:
            card.source_refs.append({"quran_refs": quran})
        if author_positions:
            card.semantic_effect["author_position_markers"] = author_positions[:3]

        cards.append(card)

    # تَرتيب: حَسَب part، ثُمّ ثِقَة (أَعلى)
    cards.sort(key=lambda c: (c.source_refs[0]["part"], -c.confidence))
    return cards


def write_cards_jsonl(cards: list[MeaningCard], output_path) -> int:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for c in cards:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count


# ─── meaning_index ────────────────────────────────────────────────────

def build_meaning_index(cards: list[dict]) -> list[dict]:
    """فهرس مُسَطَّح: meaning_id → عُنوان + رَوابِط."""
    out = []
    for c in cards:
        out.append({
            "meaning_id": c.get("meaning_id"),
            "title": c.get("title"),
            "meaning_type": c.get("meaning_type"),
            "engine_applicability": c.get("engine_applicability"),
            "confidence": c.get("confidence"),
            "n_source_claims": len(c.get("source_claims") or []),
            "n_examples": len(c.get("examples") or []),
            "part": (c.get("source_refs") or [{}])[0].get("part"),
            "page_start": (c.get("source_refs") or [{}])[0].get("page_start"),
        })
    return out


def write_index_jsonl(index: list[dict], output_path) -> int:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for r in index:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            count += 1
    return count
