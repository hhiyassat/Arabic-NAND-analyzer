"""batch_attack_quran.py — تَحليل القُرآن مَع chunked resumability.

يَدعَم استكمال التَّشغيل عَبر state file. كُلّ تَشغيل يُعالِج dishonest chunk
ثُمَّ يَحفَظ، حَتّى يَكتَمِل.

الِاستخدام:
    python batch_attack_quran.py            # يَتابِع تِلقائيًّا
    python batch_attack_quran.py --restart  # يَبدأ مِن الصِّفر
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
sys.path.insert(0, str(_REPO / "clean_code"))

from root_pipeline import RootPipeline
from m1_pipeline import M1Pipeline
from text_graph_assembler import TextGraphAssembler
from clause_segmenter import _strip_pause_marks


QURAN_PATH = _REPO / "data" / "quran-uthmani-with-pause-mark.txt"
STATE = _REPO / "data" / "eval" / "full_quran_state.json"
OUT_TOKEN = _REPO / "data" / "eval" / "full_quran_token_stats.json"
OUT_PATTERNS = _REPO / "data" / "eval" / "full_quran_error_patterns.json"
OUT_SUMMARY = _REPO / "data" / "eval" / "full_quran_summary.md"


PAUSE_AND_REC = {"ۖ", "ۗ", "ۘ", "ۙ", "ۚ", "ۛ", "ۜ", "ۢ", "ۤ", "ۥ", "ۦ", "ۧ", "ۨ", "ۭ"}


def _load_all_verses():
    verses = []
    if not QURAN_PATH.exists():
        return verses
    with QURAN_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|", 2)
            if len(parts) == 3:
                s, a, text = parts
                verses.append((f"{s}:{a}", _strip_pause_marks(text)))
    return verses


def _load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "next_idx": 0,
        "token_status": {},
        "word_per_status": {},
        "root_with_pause": {},
        "root_too_short": {},
        "wazn_with_pause": {},
        "kind_counter": {},
        "no_match": {},
        "n_clauses": 0,
        "n_relations": 0,
        "n_pronouns": 0,
        "n_pronouns_resolved": 0,
        "failed": [],
    }


def _save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def _bump(d: dict, key: str, by: int = 1):
    d[key] = d.get(key, 0) + by


def _bump_nested(d: dict, outer: str, inner: str, by: int = 1):
    if outer not in d:
        d[outer] = {}
    d[outer][inner] = d[outer].get(inner, 0) + by


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--restart", action="store_true")
    ap.add_argument("--max-seconds", type=int, default=40,
                    help="حَدّ زَمَنيّ لِلتَّشغيل قَبل الحَفظ والخُروج (افتراضيّ 40)")
    args = ap.parse_args()

    verses = _load_all_verses()
    total = len(verses)
    state = _load_state() if not args.restart else _load_state.__wrapped__() if False else {
        "next_idx": 0, "token_status": {}, "word_per_status": {},
        "root_with_pause": {}, "root_too_short": {}, "wazn_with_pause": {},
        "kind_counter": {}, "no_match": {}, "n_clauses": 0,
        "n_relations": 0, "n_pronouns": 0, "n_pronouns_resolved": 0,
        "failed": [],
    }
    if args.restart and STATE.exists():
        STATE.unlink()
        state["next_idx"] = 0

    start_idx = state["next_idx"]
    if start_idx >= total:
        print(f"DONE: all {total} verses already processed")
        _write_final(state)
        return

    print(f"Resuming from idx {start_idx}/{total}")
    rp = RootPipeline()
    m1 = M1Pipeline()
    asm = TextGraphAssembler()

    t0 = time.time()
    i = start_idx
    while i < total and (time.time() - t0) < args.max_seconds:
        ref, text = verses[i]
        try:
            for w in text.split():
                if not w:
                    continue
                r = rp.analyze(w)
                status = getattr(r, "status", "?")
                _bump(state["token_status"], status)
                _bump_nested(state["word_per_status"], status, w)
                _bump(state["kind_counter"], getattr(r, "kind", "?"))
                root = (getattr(r, "root", "—") or "—")
                wazn = (getattr(r, "wazn", "—") or "—")
                if root != "—":
                    if any(c in PAUSE_AND_REC for c in root):
                        _bump(state["root_with_pause"], w)
                    elif len(root) <= 1:
                        _bump(state["root_too_short"], w)
                if wazn != "—" and any(c in PAUSE_AND_REC for c in wazn):
                    _bump(state["wazn_with_pause"], w)
                if status == "no_match":
                    _bump(state["no_match"], w)

            r1 = m1.analyze(text)
            state["n_clauses"] += len(r1.clause_analyses)

            tg = asm.assemble(text)
            state["n_relations"] += len(tg.intra_relations)
            n_pron = len(tg.pronoun_references)
            n_res = sum(1 for p in tg.pronoun_references if p.referent_token_idx)
            state["n_pronouns"] += n_pron
            state["n_pronouns_resolved"] += n_res
        except Exception as e:
            state["failed"].append({"ref": ref, "error": str(e)[:200]})

        i += 1

    state["next_idx"] = i
    _save_state(state)
    elapsed = time.time() - t0
    done = i
    pct = done / total * 100
    print(f"Processed {done - start_idx} verses in {elapsed:.1f}s ({(done - start_idx)/max(elapsed,0.01):.1f}/s)")
    print(f"Progress: {done}/{total} ({pct:.1f}%)")

    if i >= total:
        print("ALL DONE — writing final reports")
        _write_final(state)


def _write_final(state):
    total_tokens = sum(state["token_status"].values())
    # Top counters
    def top(d, n=50):
        return sorted(d.items(), key=lambda kv: -kv[1])[:n]

    summary = {
        "n_verses": state["next_idx"],
        "n_failed": len(state["failed"]),
        "tokens": {
            "total": total_tokens,
            "by_status": dict(top(state["token_status"], 20)),
            "by_kind": dict(top(state["kind_counter"], 10)),
        },
        "n_clauses_total": state["n_clauses"],
        "n_relations_total": state["n_relations"],
        "pronouns": {
            "total": state["n_pronouns"],
            "resolved": state["n_pronouns_resolved"],
            "resolution_rate": (
                round(state["n_pronouns_resolved"] / state["n_pronouns"], 4)
                if state["n_pronouns"] else 0.0
            ),
        },
    }
    OUT_TOKEN.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    patterns = {
        "no_match_top_50": top(state["no_match"], 50),
        "root_with_pause_marks_top_50": top(state["root_with_pause"], 50),
        "root_too_short_top_50": top(state["root_too_short"], 50),
        "wazn_with_pause_marks_top_50": top(state["wazn_with_pause"], 50),
        "closed_class_words_top_30": top(state["word_per_status"].get("closed_class", {}), 30),
        "jamid_words_top_30": top(state["word_per_status"].get("jamid", {}), 30),
        "singular_term_words_top_30": top(state["word_per_status"].get("singular_term", {}), 30),
        "no_match_words_top_50": top(state["word_per_status"].get("no_match", {}), 50),
        "failed_verses_first_20": state["failed"][:20],
    }
    OUT_PATTERNS.write_text(json.dumps(patterns, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown summary
    md = [f"# Full-Quran Attack Summary\n"]
    md.append(f"**Verses processed:** {state['next_idx']} · **Failed:** {len(state['failed'])}\n")
    md.append(f"## Tokens\n- Total: {total_tokens}")
    md.append(f"- By status:")
    for status, count in top(state["token_status"], 20):
        pct = count / total_tokens * 100
        md.append(f"  - `{status}`: {count} ({pct:.1f}%)")
    md.append(f"\n## Clauses\n- Total: {state['n_clauses']}\n")
    md.append(f"## Relations (intra-clause)\n- Total: {state['n_relations']}\n")
    md.append(f"## Pronouns\n- Total: {state['n_pronouns']} · Resolved: {state['n_pronouns_resolved']} ({summary['pronouns']['resolution_rate']:.1%})\n")
    md.append(f"## Top fix targets\n")
    md.append(f"### no_match — top 20\n")
    for w, c in top(state["no_match"], 20):
        md.append(f"- `{w}` × {c}")
    md.append(f"\n### root contains recitation mark — top 20\n")
    for w, c in top(state["root_with_pause"], 20):
        md.append(f"- `{w}` × {c}")
    md.append(f"\n### wazn contains recitation mark — top 20\n")
    for w, c in top(state["wazn_with_pause"], 20):
        md.append(f"- `{w}` × {c}")
    md.append(f"\n### root too short (≤1 char) — top 20\n")
    for w, c in top(state["root_too_short"], 20):
        md.append(f"- `{w}` × {c}")
    md.append(f"\n### closed_class — top 30\n")
    for w, c in top(state["word_per_status"].get("closed_class", {}), 30):
        md.append(f"- `{w}` × {c}")
    md.append(f"\n### singular_term — top 20\n")
    for w, c in top(state["word_per_status"].get("singular_term", {}), 20):
        md.append(f"- `{w}` × {c}")
    OUT_SUMMARY.write_text("\n".join(md), encoding="utf-8")

    print(f"Wrote:")
    print(f"  {OUT_TOKEN}")
    print(f"  {OUT_PATTERNS}")
    print(f"  {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
