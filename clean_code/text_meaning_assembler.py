"""text_meaning_assembler.py — Phase F: تَجميع MeaningGraph لِنَصّ مُتَعَدِّد الجُمَل.

يَأخُذ نَصًّا، يَقسِمه لِجُمَل، يَبني MeaningGraph لِكُلّ جُملَة،
ثُمّ يَربِط الـ graphs عَبر الإِحالات المُشتَرَكَة.

CLI:
  python3 text_meaning_assembler.py --file text.txt
  python3 text_meaning_assembler.py --surah 1
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from meaning_graph import MeaningGraph, MeaningNode, MeaningEdge
from meaning_assembler import MeaningAssembler, format_graph

_HERE = Path(__file__).resolve().parent

# عَلامات تَقسيم الجُمَل (لَيسَت ground truth — قَواعِد heuristic بَسيطَة)
SENTENCE_BOUNDARY = re.compile(r"[.؟!\n]+|\.\s+")


def split_sentences(text: str) -> list[str]:
    """تَقسيم بَسيط لِنَصّ إلى جُمَل."""
    parts = SENTENCE_BOUNDARY.split(text)
    return [p.strip() for p in parts if p.strip()]


def assemble_text(text: str, ma: MeaningAssembler | None = None) -> MeaningGraph:
    """يَبني MeaningGraph مُوَحَّد لِكُلّ النَّصّ.

    Strategy:
      1. قَسِّم النَّصّ إلى جُمَل
      2. ابنِ MeaningGraph لِكُلّ جُملَة بِمُعَرِّفات unique (s0_t0، s1_t0...)
      3. ادمِجها في graph واحِد
      4. أَضِف cross-sentence edges عِندَ تَطابُق entities
    """
    if ma is None:
        ma = MeaningAssembler()

    sentences = split_sentences(text)
    combined = MeaningGraph(text=text, contract="TextMeaningGraph:v1")

    entity_index: dict[str, list[tuple[int, str]]] = {}  # surface_plain → [(sent_idx, node_id)]

    for s_idx, sent in enumerate(sentences):
        try:
            sg = ma.assemble(sent)
        except Exception:
            continue

        # نَقل العُقَد بِمُعَرِّفات mangled
        for n in sg.nodes:
            new_id = f"s{s_idx}_{n.node_id}"
            combined.add_node(MeaningNode(
                node_id=new_id,
                node_type=n.node_type,
                surface=n.surface,
                position=n.position + s_idx * 1000,  # offset
                proof_kind=n.proof_kind,
                contract=n.contract,
                source_of_claim=n.source_of_claim,
                attributes={**n.attributes, "sentence_idx": s_idx, "sentence_text": sent},
            ))
            # سَجِّل الـ entity
            if n.node_type == "entity":
                # تَطبيع بَسيط لِلسَّطح
                from samarrai_loaders.volume1_loader import _normalize
                surface_plain = _normalize(n.surface)
                entity_index.setdefault(surface_plain, []).append((s_idx, new_id))

        # نَقل الرَّوابِط
        for e in sg.edges:
            combined.add_edge(MeaningEdge(
                edge_id=f"s{s_idx}_{e.edge_id}",
                edge_type=e.edge_type,
                source=f"s{s_idx}_{e.source}" if not e.source.startswith("s") else e.source,
                target=f"s{s_idx}_{e.target}" if not e.target.startswith("s") else e.target,
                operator=e.operator,
                proof_kind=e.proof_kind,
                contract=e.contract,
                source_of_claim=e.source_of_claim,
                confidence=e.confidence,
                alternatives=e.alternatives,
            ))

    # cross-sentence edges: نَفس الـ entity في جُمَل مُتَعَدِّدَة → coreference
    for surface_plain, occurrences in entity_index.items():
        if len(occurrences) < 2:
            continue
        # اربِط كُلّ ظُهور بِالأَوَّل
        first_sent, first_id = occurrences[0]
        for s_idx, node_id in occurrences[1:]:
            combined.add_edge(MeaningEdge(
                edge_id=f"coref_{first_id}_{node_id}",
                edge_type="anaphora_to",  # نَفس النَّوع
                source=node_id,
                target=first_id,
                proof_kind="Hypothesis",
                contract="TextCorefHeuristic:v1",
                source_of_claim=f"surface_plain:«{surface_plain}» مُكَرَّر في جُمَل {first_sent} وَ {s_idx}",
                blockers=["heuristic: مُجَرَّد تَطابُق سَطحيّ، يَحتاج تَأكيد سياقيّ"],
            ))

    return combined


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file")
    p.add_argument("--surah", type=int, help="سورَة بِأَكمَلها")
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    elif args.surah:
        verses_path = _HERE.parent / "data" / "quran-uthmani-with-pause-mark.txt"
        verses = []
        with open(verses_path, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) >= 3 and parts[0] == str(args.surah):
                    verses.append(parts[2])
        text = " . ".join(verses)
    else:
        p.print_help()
        sys.exit(1)

    print(f"النَّصّ: {len(text)} حَرف\n")
    g = assemble_text(text)
    print(format_graph(g, verbose=args.verbose))


if __name__ == "__main__":
    main()
