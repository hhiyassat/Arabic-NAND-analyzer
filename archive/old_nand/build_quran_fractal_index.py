"""build_quran_fractal_index.py — فهرس fractal لجميع كلمات القرآن.

لكل token في كل آية، يُخزَّن:
  - معلومات الموقع (سورة، آية، رقم الكلمة)
  - السطح + المُجرَّد
  - التصنيف الكامل (word_class, root, wazn, case, mark, role)
  - الإثبات الثلاثي لكل طبقة (C/H/Z + contract + blockers)
  - الإحداثيّة الستّية (L0..L5 hashes + concatenated)

المخرج: data/quran_fractal_index.csv
"""

from __future__ import annotations

import csv
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "clean_code"))

from i3rab_engine import I3rabEngine  # type: ignore

LABELS_PATH = Path(
    "/Users/husseinhiyassat/fractal/new_arabic_analyzer/data/quran/quran_i3rab_labels.jsonl"
)
if not LABELS_PATH.is_file():
    LABELS_PATH = Path(
        "/sessions/nice-epic-cannon/mnt/new_arabic_analyzer/data/quran/quran_i3rab_labels.jsonl"
    )

OUT_DIR = ROOT / "data"
OUT_PATH = OUT_DIR / "quran_fractal_index.csv"
SUMMARY_PATH = OUT_DIR / "quran_fractal_index_summary.md"


def load_ayahs() -> dict[tuple[int, int], list[str]]:
    """Map (surah, ayah) → list of words from labels.jsonl."""
    ayahs: dict[tuple[int, int], list[str]] = defaultdict(list)
    with LABELS_PATH.open(encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
                key = (int(d["surah"]), int(d["ayah"]))
                ayahs[key].append(d["word"])
            except Exception:
                continue
    return ayahs


def main(max_ayahs: int = 0, *, start: int = 0, end: int = 0,
         append: bool = False) -> int:
    if not LABELS_PATH.is_file():
        print(f"خطأ: ملف الـ labels غير موجود: {LABELS_PATH}", file=sys.stderr)
        return 1

    print(f"تحميل الآيات...", file=sys.stderr)
    ayahs = load_ayahs()
    keys = sorted(ayahs.keys())
    if max_ayahs:
        keys = keys[:max_ayahs]
    elif start or end:
        end = end or len(keys)
        keys = keys[start:end]
    print(f"عدد الآيات: {len(keys)} (slice [{start}:{end or len(keys)}])",
          file=sys.stderr)

    print(f"تهيئة المحرّك...", file=sys.stderr)
    eng = I3rabEngine()

    # Output CSV header
    fieldnames = [
        "surah", "ayah", "position",
        "token", "token_plain",
        "word_class", "root", "wazn",
        "case_id", "mark_id", "role_phrase",
        "wc_kind", "case_kind", "role_kind",
        "wc_contract", "case_contract", "role_contract",
        "wc_blockers", "case_blockers", "role_blockers",
        "L0_hash", "L1_hash", "L2_hash",
        "L3_hash", "L4_hash", "L5_hash",
        "coord_hash",
        # L1 detail (segmentation)
        "prefixes", "stem", "suffixes",
    ]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_mode = "a" if append else "w"
    write_header = not append

    # Statistics
    stats = Counter()
    proof_kinds = Counter()
    coord_collisions = Counter()  # coord_hash → count
    same_surface_diff_coord = defaultdict(set)  # token → set of coord_hashes

    t_start = time.time()

    with OUT_PATH.open(write_mode, encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()

        for idx, (s, a) in enumerate(keys, start=1):
            tokens = ayahs[(s, a)]
            text = " ".join(tokens)
            sent = eng.analyze_sentence(text)

            for pos, ti in enumerate(sent.tokens):
                row = {
                    "surah": s, "ayah": a, "position": pos,
                    "token": ti.token,
                    "token_plain": "".join(
                        c for c in ti.token if c not in "ًٌٍَُِّْٰٕۣٓٔۜ۟۠ۡۢۤۥۦ۪ۭۧۨ۫۬"
                    ),
                    "word_class": ti.word_class,
                    "root": ti.root,
                    "wazn": ti.wazn,
                    "case_id": ti.case_id or "",
                    "mark_id": ti.mark_id or "",
                    "role_phrase": ti.role_phrase,
                    "wc_kind": ti.wordclass_kind,
                    "case_kind": ti.case_kind,
                    "role_kind": ti.role_kind,
                    "wc_contract": ti.wordclass_contract,
                    "case_contract": ti.case_contract,
                    "role_contract": ti.role_contract,
                    "wc_blockers": "|".join(ti.wordclass_blockers),
                    "case_blockers": "|".join(ti.case_blockers),
                    "role_blockers": "|".join(ti.role_blockers),
                    "L0_hash": ti.coord_hash[0:6],
                    "L1_hash": ti.coord_hash[6:12],
                    "L2_hash": ti.coord_hash[12:18],
                    "L3_hash": ti.coord_hash[18:24],
                    "L4_hash": ti.coord_hash[24:30],
                    "L5_hash": ti.coord_hash[30:36],
                    "coord_hash": ti.coord_hash,
                    "prefixes": "+".join(ti.prefixes),
                    "stem": ti.stem,
                    "suffixes": "+".join(ti.suffixes),
                }
                writer.writerow(row)

                # Accumulate stats
                stats["total_tokens"] += 1
                if ti.wordclass_kind:
                    proof_kinds[("wc", ti.wordclass_kind)] += 1
                if ti.case_kind:
                    proof_kinds[("case", ti.case_kind)] += 1
                if ti.role_kind:
                    proof_kinds[("role", ti.role_kind)] += 1
                coord_collisions[ti.coord_hash] += 1
                same_surface_diff_coord[ti.token].add(ti.coord_hash)

            if idx % 200 == 0:
                elapsed = time.time() - t_start
                rate = idx / elapsed if elapsed > 0 else 0
                eta = (len(keys) - idx) / rate if rate > 0 else 0
                print(
                    f"  ... {idx}/{len(keys)} آية "
                    f"({stats['total_tokens']} token) · "
                    f"معدّل={rate:.1f}/ث · ETA={eta:.0f}ث",
                    file=sys.stderr,
                )

    elapsed = time.time() - t_start
    print(f"\nاكتمل في {elapsed:.1f}ث", file=sys.stderr)

    if append:
        # Append mode = chunk in a series; skip summary
        print(f"chunk done: {stats['total_tokens']} tokens", file=sys.stderr)
        return 0

    # Write summary markdown
    with SUMMARY_PATH.open("w", encoding="utf-8") as f:
        f.write("# Quran Fractal Index — ملخّص\n\n")
        f.write(f"**Source**: quran_i3rab_labels.jsonl ({len(keys)} آية)\n\n")
        f.write(f"**Tokens**: {stats['total_tokens']:,}\n\n")
        f.write(f"**Output**: `data/quran_fractal_index.csv`\n\n")
        f.write(f"**Build time**: {elapsed:.1f}s ({stats['total_tokens']/elapsed:.0f} tokens/s)\n\n")

        f.write("## Proof Kinds — التوزّع الكامل\n\n")
        f.write("| الطبقة | Certificate | Hypothesis | Zero | إجمالي |\n")
        f.write("|---|---:|---:|---:|---:|\n")
        for layer in ("wc", "case", "role"):
            c = proof_kinds.get((layer, "Certificate"), 0)
            h = proof_kinds.get((layer, "Hypothesis"), 0)
            z = proof_kinds.get((layer, "Zero"), 0)
            tot = c + h + z
            name = {"wc": "WordClass", "case": "Case", "role": "Role"}[layer]
            if tot:
                f.write(
                    f"| {name} | {c:,} ({100*c/tot:.1f}%) | "
                    f"{h:,} ({100*h/tot:.1f}%) | "
                    f"{z:,} ({100*z/tot:.1f}%) | {tot:,} |\n"
                )

        # Coord uniqueness
        unique_coords = len(coord_collisions)
        f.write(f"\n## الإحداثيّات\n\n")
        f.write(f"- **إحداثيّات فريدة**: {unique_coords:,}\n")
        f.write(f"- **إجمالي tokens**: {stats['total_tokens']:,}\n")
        f.write(f"- **معدّل التكرار**: {stats['total_tokens']/unique_coords:.2f} token لكل إحداثيّة فريدة\n\n")

        # Top recurring coords
        f.write("### أكثر 10 إحداثيّات تكرارًا\n\n")
        f.write("| الإحداثيّة | عدد التكرارات |\n")
        f.write("|---|---:|\n")
        for coord, n in coord_collisions.most_common(10):
            f.write(f"| `{coord}` | {n} |\n")

        # Same-surface diff-coord examples (context-distinguishing power)
        examples = sorted(
            ((tok, len(coords)) for tok, coords in same_surface_diff_coord.items()),
            key=lambda x: -x[1],
        )[:15]
        f.write("\n### أكثر 15 كلمة تأخذ إحداثيّات مختلفة بحسب السياق\n\n")
        f.write("هذا يقيس قوّة الفهرس في التمييز السياقي.\n\n")
        f.write("| الكلمة | عدد الإحداثيّات المختلفة |\n")
        f.write("|---|---:|\n")
        for tok, n in examples:
            f.write(f"| {tok} | {n} |\n")

    print(f"\n=== الملخّص ===")
    print(f"إجمالي tokens: {stats['total_tokens']:,}")
    print(f"إحداثيّات فريدة: {len(coord_collisions):,}")
    print(f"المخرج: {OUT_PATH}")
    print(f"الملخّص: {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--max-ayahs", type=int, default=0)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--end", type=int, default=0)
    p.add_argument("--append", action="store_true")
    args = p.parse_args()
    sys.exit(main(
        max_ayahs=args.max_ayahs,
        start=args.start,
        end=args.end,
        append=args.append,
    ))
