"""eval_end_to_end_surahs.py — جَلسة 22: اختبار end-to-end على سُور قَصيرة.

يُجري TextGraphAssembler على:
  • الفاتحة كامِلَة (1:1-1:7)
  • الإخلاص كامِلَة (112:1-112:4)

ويَجمَع إِحصاءات بِنيويَّة لِكُلّ طَبَقَة:
  Layer 0 (Sign):          # كَلِمات، # بَعد تَنظيف pause marks
  Layer 1 (Perception):    # كَلِمات مُصَنَّفَة كَ FIIL/ISM_*/HARF/...
  Layer 2 (Conceptual):    # جُمَل، # عَلاقات بَين الجُمَل
  Layer 3 (Relations):     # عَلاقات داخِل الجُمَل، # ضَمائر بِمُحَلّ

النَّتائج → data/eval/end_to_end_surahs.json
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
sys.path.insert(0, str(_REPO / "clean_code"))

from text_graph_assembler import TextGraphAssembler


QURAN_PATH = _REPO / "data" / "quran-uthmani-with-pause-mark.txt"
OUT_PATH = _REPO / "data" / "eval" / "end_to_end_surahs.json"

PAUSE_MARKS = {"ۖ", "ۗ", "ۘ", "ۙ", "ۚ", "ۛ", "ۜ"}


def _load_verses(refs: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    targets = set(refs)
    if not QURAN_PATH.exists():
        return out
    with QURAN_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|", 2)
            if len(parts) != 3:
                continue
            s, a, text = parts
            ref = f"{s}:{a}"
            if ref in targets:
                # نَنزع pause marks لِأَنّها ground-truth، لا signal
                out[ref] = "".join(c for c in text if c not in PAUSE_MARKS)
    return out


def evaluate_surah(name: str, refs: list[str], verses: dict[str, str]) -> dict:
    asm = TextGraphAssembler()

    total_tokens = 0
    total_clauses = 0
    total_intra = 0
    total_inter = 0
    total_pronouns = 0
    pronouns_resolved = 0
    wc_counter: Counter = Counter()
    rel_name_counter: Counter = Counter()
    inter_name_counter: Counter = Counter()
    per_verse = []

    for ref in refs:
        if ref not in verses:
            continue
        text = verses[ref]
        tg = asm.assemble(text)
        n_tokens = len(tg.nodes)
        n_clauses = len(tg.clauses_text)
        n_intra = len(tg.intra_relations)
        n_inter = len(tg.inter_clause_relations)
        n_pronouns = len(tg.pronoun_references)
        n_pronouns_resolved = sum(1 for p in tg.pronoun_references if p.referent_token_idx is not None)

        total_tokens += n_tokens
        total_clauses += n_clauses
        total_intra += n_intra
        total_inter += n_inter
        total_pronouns += n_pronouns
        pronouns_resolved += n_pronouns_resolved

        for nid, node in tg.nodes.items():
            wc_counter[node.word_class] += 1
        for r in tg.intra_relations:
            rel_name_counter[r.name] += 1
        for r in tg.inter_clause_relations:
            inter_name_counter[r.name] += 1

        per_verse.append({
            "ref": ref,
            "text": text,
            "n_tokens": n_tokens,
            "n_clauses": n_clauses,
            "n_intra_relations": n_intra,
            "n_inter_clause_relations": n_inter,
            "n_pronouns": n_pronouns,
            "n_pronouns_resolved": n_pronouns_resolved,
        })

    return {
        "surah": name,
        "n_verses": len(per_verse),
        "totals": {
            "tokens": total_tokens,
            "clauses": total_clauses,
            "intra_relations": total_intra,
            "inter_clause_relations": total_inter,
            "pronouns": total_pronouns,
            "pronouns_resolved": pronouns_resolved,
        },
        "averages": {
            "intra_per_verse": round(total_intra / max(len(per_verse), 1), 2),
            "intra_per_token": round(total_intra / max(total_tokens, 1), 3),
            "pronoun_resolution_rate": (
                round(pronouns_resolved / total_pronouns, 4) if total_pronouns else 0.0
            ),
        },
        "word_class_distribution": dict(wc_counter.most_common()),
        "intra_relation_distribution": dict(rel_name_counter.most_common()),
        "inter_clause_distribution": dict(inter_name_counter.most_common()),
        "per_verse": per_verse,
    }


def main():
    fatiha_refs = [f"1:{i}" for i in range(1, 8)]
    ikhlas_refs = [f"112:{i}" for i in range(1, 5)]
    all_refs = fatiha_refs + ikhlas_refs
    verses = _load_verses(all_refs)
    print(f"loaded {len(verses)} verses")

    result = {
        "contract": "EndToEndEval:v1",
        "fatiha": evaluate_surah("الفاتحة", fatiha_refs, verses),
        "ikhlas": evaluate_surah("الإخلاص", ikhlas_refs, verses),
        "note": (
            "هذا قِياس بِنيويّ شامِل عَلى السُّورَتَين. لا ground-truth يَدَويّة، "
            "لذلِك لا نَدَّعي «دِقَّة». الأَرقام تُبَيِّن كَثافَة العَلاقات "
            "وانتِظام الـ extractor عَبر السُّورَتَين."
        ),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nWrote {OUT_PATH}\n")
    for surah_key in ("fatiha", "ikhlas"):
        s = result[surah_key]
        print(f"=== {s['surah']} ({s['n_verses']} آيات) ===")
        print(f"  tokens={s['totals']['tokens']}  clauses={s['totals']['clauses']}")
        print(f"  intra={s['totals']['intra_relations']}  inter={s['totals']['inter_clause_relations']}")
        print(f"  pronouns={s['totals']['pronouns']}  resolved={s['totals']['pronouns_resolved']} "
              f"({s['averages']['pronoun_resolution_rate']:.1%})")
        print(f"  avg intra/verse = {s['averages']['intra_per_verse']}")
        print(f"  avg intra/token = {s['averages']['intra_per_token']}")
        print()


if __name__ == "__main__":
    main()
