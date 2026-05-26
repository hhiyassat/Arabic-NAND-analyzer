"""enrich_operators_with_maani.py — إِثراء العَوامِل الـ 97 بِبَطاقات مَعاني السامرَّائيّ.

الـ pipeline:
  1. نُحَمِّل operators_catalog (97 عامِل)
  2. نُحَمِّل meaning_cards.jsonl (1,818 بِطاقَة)
  3. نُحَمِّل rule_cards.jsonl (لِلأَمثلَة المُختارَة يَدَويًّا)
  4. لِكُلّ عامِل: نَجِد أَعلى 5 بِطاقات بِـ lemma matching
  5. نَكتُب operators_enriched.jsonl

مَنطِق المُطابَقَة (صارِم — lemma فَقَط):
  • نَفحَص triggers.lemmas في كُلّ بِطاقَة
  • نُقارِن مَع شَكل العامِل (مَع وَ بِدون تَشكيل)
  • نُرَتِّب بِالثِّقَة + عَلى أَنَّ بِطاقات مِن نَفس topic أَعلى وَزنًا
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_OPERATORS_CSV = _HERE / "data" / "contracts" / "lists" / "operators_catalog.csv"
_MAANI_DIR = _HERE.parent / "maani_alnahw" / "data" / "processed" / "maani_alnahw"
_MEANING_CARDS = _MAANI_DIR / "meaning_cards.jsonl"
_RULE_CARDS = _MAANI_DIR / "rule_cards.jsonl"
_OUTPUT = _MAANI_DIR / "operators_enriched.jsonl"

DIACRITICS = "ًٌٍَُِّْـٰٓ"
MAX_CARDS_PER_OP = 5


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _normalize(s: str) -> str:
    s = _strip_diac(s)
    return s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")


def load_operators() -> list[dict]:
    """يُحَمِّل 102 سَطر مِن الكاتالوغ."""
    ops = []
    with open(_OPERATORS_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            gn = row.get("Group Number", "").strip()
            if not gn or gn.startswith("Group"):
                continue
            ops.append({
                "group_id": gn,
                "group_ar": row.get("Arabic Group Name", "").strip(),
                "group_en": row.get("English Group Name", "").strip(),
                "operator": row.get("Operator", "").strip(),
                "operator_plain": _normalize(row.get("Operator", "").strip()),
                "purpose": row.get("Purpose/Usage", "").strip(),
                "example": row.get("Example", "").strip(),
                "example_vocalized": row.get("Example_Vocalized", "").strip(),
                "note": row.get("Note", "").strip(),
            })
    return ops


def load_meaning_cards() -> list[dict]:
    cards = []
    if not _MEANING_CARDS.exists():
        return cards
    with open(_MEANING_CARDS, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    cards.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return cards


def load_rule_cards() -> list[dict]:
    rules = []
    if not _RULE_CARDS.exists():
        return rules
    with open(_RULE_CARDS, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rules.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rules


def _card_has_lemma(card: dict, lemma_plain: str) -> bool:
    """يَفحَص هَل البِطاقَة تَستَهدِف هذا العامِل (عَبر triggers فَقَط — صارِم)."""
    triggers = card.get("triggers") or {}
    if not isinstance(triggers, dict):
        return False
    # نَفحَص lemmas
    lemmas = triggers.get("lemmas") or []
    for lm in lemmas:
        if _normalize(lm) == lemma_plain:
            return True
    # نَفحَص particles
    particles = triggers.get("particles") or []
    for p in particles:
        if _normalize(p) == lemma_plain:
            return True
    return False


def _rule_has_lemma(rule: dict, lemma_plain: str) -> bool:
    """يَفحَص rule_card."""
    trigger = rule.get("trigger") or {}
    if not isinstance(trigger, dict):
        return False
    lemmas = trigger.get("lemmas") or []
    for lm in lemmas:
        if _normalize(lm) == lemma_plain:
            return True
    particles = trigger.get("particles") or []
    for p in particles:
        if _normalize(p) == lemma_plain:
            return True
    # نَفحَص أَيضًا "particle" فَردي
    particle = trigger.get("particle")
    if particle and _normalize(particle) == lemma_plain:
        return True
    return False


def find_cards_for_operator(operator_plain: str, cards: list[dict],
                              max_n: int = MAX_CARDS_PER_OP) -> list[dict]:
    """يَجلِب أَعلى N بِطاقَة لِعامِل."""
    matched = [c for c in cards if _card_has_lemma(c, operator_plain)]
    # نُرَتِّب: الـ direct_rule + ثِقَة عاليَة أَوَّلًا
    def _score(c):
        appl = c.get("engine_applicability", "")
        appl_rank = {"direct_rule": 4, "heuristic_rule": 3,
                      "interpretive_note": 2, "review_only": 1}.get(appl, 0)
        return (appl_rank, c.get("confidence", 0))
    matched.sort(key=_score, reverse=True)
    return matched[:max_n]


def find_rule_for_operator(operator_plain: str, rules: list[dict]) -> dict | None:
    """يَجلِب rule_card مُتَخَصِّص لِعامِل (إن وُجِد)."""
    for r in rules:
        if _rule_has_lemma(r, operator_plain):
            return r
    return None


def enrich_operator(op: dict, meaning_cards: list[dict],
                     rule_cards: list[dict]) -> dict:
    """يُولِّد سَجِلًّا مُثرى لِعامِل واحِد."""
    operator_plain = op["operator_plain"]
    related_cards = find_cards_for_operator(operator_plain, meaning_cards)
    related_rule = find_rule_for_operator(operator_plain, rule_cards)

    # نَجمَع أَمثلَة المُؤَلِّف
    author_examples = []
    if related_rule:
        for ex in (related_rule.get("examples") or []):
            if isinstance(ex, dict) and ex.get("text"):
                author_examples.append(ex)

    # نَجمَع تَحذيرات
    warnings_set = set()
    if related_rule:
        for w in (related_rule.get("exceptions_or_warnings") or []):
            warnings_set.add(w)
    for c in related_cards:
        for w in (c.get("warnings") or []):
            warnings_set.add(w[:200])

    # نَجمَع شُروط
    conditions = []
    if related_rule:
        conditions.extend(related_rule.get("conditions") or [])

    return {
        "operator": op["operator"],
        "operator_plain": operator_plain,
        "group_id": op["group_id"],
        "group_ar": op["group_ar"],
        "group_en": op["group_en"],
        "catalog_data": {
            "purpose": op["purpose"],
            "example": op["example"],
            "example_vocalized": op["example_vocalized"],
            "note": op["note"],
        },
        "rule_card_from_maani": {
            "rule_id": related_rule.get("rule_id") if related_rule else None,
            "title": related_rule.get("title") if related_rule else None,
            "syntactic_effect": related_rule.get("syntactic_effect") if related_rule else None,
            "semantic_effect": related_rule.get("semantic_effect") if related_rule else None,
            "author_position": related_rule.get("author_position") if related_rule else None,
            "confidence": related_rule.get("confidence") if related_rule else None,
        } if related_rule else None,
        "related_meaning_cards": [
            {
                "meaning_id": c.get("meaning_id"),
                "title": c.get("title"),
                "type": c.get("meaning_type"),
                "applicability": c.get("engine_applicability"),
                "description_excerpt": (c.get("description") or "")[:200],
                "confidence": c.get("confidence"),
                "source_ref": (c.get("source_refs") or [{}])[0],
            }
            for c in related_cards
        ],
        "author_examples": author_examples[:5],
        "warnings": sorted(warnings_set)[:5],
        "conditions": conditions[:5],
        "n_meaning_cards": len(related_cards),
        "is_enriched": len(related_cards) > 0 or related_rule is not None,
    }


def main():
    print("  ► تَحميل operators_catalog...")
    operators = load_operators()
    print(f"    {len(operators)} مُدخَل")

    print("  ► تَحميل meaning_cards...")
    cards = load_meaning_cards()
    print(f"    {len(cards)} بِطاقَة")

    print("  ► تَحميل rule_cards...")
    rules = load_rule_cards()
    print(f"    {len(rules)} قاعِدَة")

    print("  ► إِثراء العَوامِل...")
    enriched = []
    enriched_count = 0
    total_cards_attached = 0
    by_group_enrich = defaultdict(int)
    for op in operators:
        e = enrich_operator(op, cards, rules)
        enriched.append(e)
        if e["is_enriched"]:
            enriched_count += 1
            total_cards_attached += e["n_meaning_cards"]
            by_group_enrich[e["group_id"]] += 1

    # نَكتُب
    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(_OUTPUT, "w", encoding="utf-8") as f:
        for e in enriched:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"  ✓ كُتِبَ: {_OUTPUT}")
    print()
    print(f"  ◆ النَّتيجَة:")
    print(f"     - عَوامِل مُثراة: {enriched_count}/{len(operators)} "
          f"({enriched_count/len(operators)*100:.0f}%)")
    print(f"     - بِطاقات مَربوطَة: {total_cards_attached}")
    print()
    print(f"  ◆ التَّوزيع حَسَب المَجموعَة:")
    for gid, n in sorted(by_group_enrich.items(), key=lambda x: -x[1]):
        # نَجِد اسم المَجموعَة
        gname = next((op["group_ar"] for op in operators if op["group_id"] == gid), "")
        print(f"     مَج {gid:3s} ({gname[:30]:30s}): {n}")

    # عَيِّنَة
    print()
    print(f"  ◆ عَيِّنَة (عامِل «إِنَّ»):")
    sample = next((e for e in enriched if e["operator_plain"] == "ان"), None)
    if sample:
        print(f"     - {sample['n_meaning_cards']} بِطاقَة")
        for c in sample["related_meaning_cards"][:3]:
            print(f"        ▸ {c['title'][:60]}")
            print(f"          {c['description_excerpt'][:80]}")


if __name__ == "__main__":
    main()
