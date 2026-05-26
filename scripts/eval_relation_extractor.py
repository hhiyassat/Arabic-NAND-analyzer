"""eval_relation_extractor.py — جَلسة 17: قِياس RelationExtractor.

يُجري RelationExtractor على 30 آية أُولى مِن سُورة الفاتحة + سُورة الإخلاص +
آيات مُتَنَوِّعَة، ويَستَخرِج إِحصاءات قابِلَة لِلتَّحَقُّق:

  • مَجموع العَلاقات المُستَخرَجَة لِكُلّ آية
  • تَوزيع العَلاقات حَسَب النَّوع
  • تَغطيَة per token: كَم token حَصَل على ≥1 علاقَة

لا ground truth يَدَويّة مُتاحَة بَعد — لذا لا نَدَّعي «دِقَّة». نُسَجِّل
أَرقامًا بِنيويَّة قابِلَة لِلمُقارَنَة في جَلسات لاحِقَة.

النَّتائج → data/eval/m1_phase_c_relation_eval.json
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
sys.path.insert(0, str(_REPO / "clean_code"))

from i3rab_engine.engine import I3rabEngine
from relation_extractor import RelationExtractor


QURAN_PATH = _REPO / "data" / "quran-uthmani-with-pause-mark.txt"
OUT_PATH = _REPO / "data" / "eval" / "m1_phase_c_relation_eval.json"


def _strip_pause_marks(s: str) -> str:
    return "".join(ch for ch in s if ch not in {"ۖ", "ۗ", "ۘ", "ۙ", "ۚ", "ۛ", "ۜ"})


def _load_verses(refs: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    if not QURAN_PATH.exists():
        return out
    targets = set(refs)
    with QURAN_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|", 2)
            if len(parts) != 3:
                continue
            s, a, text = parts
            ref = f"{s}:{a}"
            if ref in targets:
                out[ref] = _strip_pause_marks(text)
    return out


def main():
    engine = I3rabEngine()
    extractor = RelationExtractor()

    # عَيِّنَة: الفاتحة كامِلَة + الإخلاص + آيات مُتَنَوِّعَة
    refs = [
        # الفاتحة (1:1-1:7)
        "1:1", "1:2", "1:3", "1:4", "1:5", "1:6", "1:7",
        # الإخلاص (112:1-112:4)
        "112:1", "112:2", "112:3", "112:4",
        # الكافرون (109:1-109:6)
        "109:1", "109:2", "109:3", "109:4", "109:5", "109:6",
        # النَّاس (114:1-114:6)
        "114:1", "114:2", "114:3", "114:4", "114:5", "114:6",
        # الفَلَق (113:1-113:5)
        "113:1", "113:2", "113:3", "113:4", "113:5",
        # آيات إِضافيَّة
        "2:255",  # آية الكُرسيّ (طَويلة)
        "2:1", "2:2",
    ]
    verses = _load_verses(refs)
    print(f"loaded {len(verses)} verses")

    per_verse = []
    total_tokens = 0
    total_relations = 0
    relation_name_counter: Counter = Counter()
    relation_kind_counter: Counter = Counter()
    proof_kind_counter: Counter = Counter()
    token_coverage_yes = 0
    token_coverage_no = 0

    for ref in refs:
        if ref not in verses:
            continue
        text = verses[ref]
        sent = engine.analyze_sentence(text)
        g = extractor.extract(sent)

        n_tokens = len(sent.tokens)
        n_rels = len(g.relations)
        total_tokens += n_tokens
        total_relations += n_rels

        # توزيع
        token_in_rel: set[str] = set()
        for r in g.relations:
            relation_name_counter[r.name] += 1
            relation_kind_counter[r.kind_type] += 1
            proof_kind_counter[r.kind] += 1
            token_in_rel.add(r.source_id)
            if r.target_id != "—":
                token_in_rel.add(r.target_id)

        token_coverage_yes += len(token_in_rel)
        token_coverage_no += n_tokens - len(token_in_rel)

        per_verse.append({
            "ref": ref,
            "text": text,
            "n_tokens": n_tokens,
            "n_relations": n_rels,
            "tokens_with_relation": len(token_in_rel),
            "relations": [
                {
                    "name": r.name,
                    "kind_type": r.kind_type,
                    "source": r.source_id,
                    "target": r.target_id,
                    "operator": r.operator,
                    "kind": r.kind,
                }
                for r in g.relations
            ],
        })

    coverage_pct = token_coverage_yes / max(token_coverage_yes + token_coverage_no, 1)

    result = {
        "contract": "RelationExtractor:v1_eval",
        "n_verses": len(verses),
        "n_tokens_total": total_tokens,
        "n_relations_total": total_relations,
        "avg_relations_per_verse": round(total_relations / max(len(verses), 1), 2),
        "avg_relations_per_token": round(total_relations / max(total_tokens, 1), 3),
        "token_coverage": {
            "with_relation": token_coverage_yes,
            "without_relation": token_coverage_no,
            "coverage_pct": round(coverage_pct, 4),
        },
        "relation_name_distribution": dict(relation_name_counter.most_common()),
        "relation_kind_distribution": dict(relation_kind_counter.most_common()),
        "proof_kind_distribution": dict(proof_kind_counter.most_common()),
        "note": (
            "هذا قِياس بِنيويّ — لا ground-truth يَدَويّة. الأَرقام تُبَيِّن "
            "تَوزيع العَلاقات وتَغطيَة الـ tokens، لا الدِّقَّة. الدِّقَّة "
            "تَحتاج 50-100 آية مُصَنَّفة يَدَويًّا — مَفتوح كَ task لاحِق."
        ),
        "per_verse": per_verse,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nWrote {OUT_PATH}")
    print()
    print(f"  الآيات:                  {len(verses)}")
    print(f"  مَجموع الـ tokens:        {total_tokens}")
    print(f"  مَجموع العَلاقات:        {total_relations}")
    print(f"  مُتَوسِّط/آية:            {result['avg_relations_per_verse']}")
    print(f"  مُتَوسِّط/token:          {result['avg_relations_per_token']}")
    print(f"  تَغطيَة الـ tokens:       {coverage_pct:.1%}")
    print()
    print(f"  تَوزيع أَسماء العَلاقات:")
    for name, count in relation_name_counter.most_common():
        print(f"    {name:<25} {count}")


if __name__ == "__main__":
    main()
