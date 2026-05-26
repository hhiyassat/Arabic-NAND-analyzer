"""exporter.py — تَوليد extraction_report.md.

التَّقرير الجَديد يَعرِض:
  • Page Coverage (لا «عَدَد constructions»)
  • Semantic Claims (حَسَب النَّوع، الجُزء، الـ topic)
  • Meaning Cards (حَسَب النَّوع، applicability)
  • Engine Mapping (subset مِن meaning_cards)
  • Warnings + Manual Review Queue
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def build_report(processed_dir: str | Path) -> str:
    processed_dir = Path(processed_dir)
    pages = _read_jsonl(processed_dir / "pages.jsonl")
    cleaned = _read_jsonl(processed_dir / "cleaned_pages.jsonl")
    topics = _read_jsonl(processed_dir / "topics.jsonl")
    rules = _read_jsonl(processed_dir / "rule_cards.jsonl")
    examples = _read_jsonl(processed_dir / "examples.jsonl")
    opinions = _read_jsonl(processed_dir / "opinions.jsonl")
    corrections = _read_jsonl(processed_dir / "ocr_corrections.jsonl")
    constructions = _read_jsonl(processed_dir / "construction_rules.jsonl")
    claims = _read_jsonl(processed_dir / "semantic_claims.jsonl")
    cards = _read_jsonl(processed_dir / "meaning_cards.jsonl")
    coverage = _read_jsonl(processed_dir / "page_coverage.jsonl")
    review = _read_jsonl(processed_dir / "manual_review_queue.jsonl")

    pages_per_part = Counter(p["part"] for p in pages)
    topic_titles = Counter(t["title"] for t in topics)
    corr_freq = Counter(c["raw"] for c in corrections)

    # claims
    claims_by_type = Counter(c.get("claim_type") for c in claims)
    claims_by_part = Counter(c.get("part") for c in claims)
    claims_by_topic = Counter(c.get("topic_title") or "(لا topic)" for c in claims)
    low_conf_claims = [c for c in claims if c.get("confidence", 1.0) < 0.6]

    # cards
    cards_by_type = Counter(c.get("meaning_type") for c in cards)
    cards_by_applicability = Counter(c.get("engine_applicability") for c in cards)
    review_only_cards = [c for c in cards if c.get("engine_applicability") == "review_only"]

    # coverage
    coverage_by_status = Counter(c.get("extraction_status") for c in coverage)
    total_pages = len(coverage)
    pages_with_claims = sum(1 for c in coverage if c.get("claims_count", 0) > 0)

    lines = []
    lines.append("# Extraction Report — مَعاني النَّحو\n")
    lines.append("> قاعِدَة مَعرِفَة دَلاليَّة-نَحويَّة مُستَخرَجَة open-ended\n")
    lines.append("> مِن كِتاب «مَعاني النَّحو» لِلسَّامَرَّائيّ (4 أَجزاء).\n")
    lines.append("> **مِعيار النَّجاح: التَّغطيَة، لا عَدَد التَّراكيب.**\n\n")

    # ── 1. Page Coverage ────────────────────────────────────────────
    lines.append("## 1. تَغطيَة الصَّفَحات (Page Coverage)\n\n")
    for part in sorted(pages_per_part):
        lines.append(f"- الجُزء {part}: **{pages_per_part[part]}** صَفحَة\n")
    lines.append(f"\n**الإِجماليّ:** {len(pages)} صَفحَة\n\n")
    lines.append("### حالَة الاستخراج\n\n")
    for status, count in coverage_by_status.most_common():
        pct = (count / total_pages * 100) if total_pages else 0
        lines.append(f"- `{status}`: **{count}** صَفحَة ({pct:.1f}%)\n")
    lines.append(f"\n- صَفَحات أَنتَجَت claims: **{pages_with_claims}** / {total_pages} "
                 f"({(pages_with_claims/total_pages*100 if total_pages else 0):.1f}%)\n\n")

    # ── 2. Semantic Claims ──────────────────────────────────────────
    lines.append("## 2. الدَّعاوى الدَّلاليَّة (Semantic Claims)\n\n")
    lines.append(f"- إِجماليّ: **{len(claims)}** claim\n")
    lines.append(f"- مُنخَفِض الثِّقَة (<0.6): **{len(low_conf_claims)}**\n")
    lines.append(f"- مُتَوَسِّط claims/صَفحَة: "
                 f"**{(len(claims)/total_pages if total_pages else 0):.2f}**\n\n")
    lines.append("### حَسَب النَّوع (Top 20)\n\n")
    for ct, count in claims_by_type.most_common(20):
        lines.append(f"- `{ct}`: **{count}**\n")
    lines.append("\n### حَسَب الجُزء\n\n")
    for part in sorted(claims_by_part):
        lines.append(f"- الجُزء {part}: **{claims_by_part[part]}** claim\n")
    lines.append("\n### أَكثَر 15 topic إِنتاجًا لِـ claims\n\n")
    for topic_title, count in claims_by_topic.most_common(15):
        lines.append(f"- {topic_title}: **{count}** claim\n")
    lines.append("\n")

    # ── 3. Meaning Cards ────────────────────────────────────────────
    lines.append("## 3. بِطاقات المَعاني (Meaning Cards)\n\n")
    lines.append(f"- إِجماليّ: **{len(cards)}** بِطاقَة\n\n")
    lines.append("### حَسَب النَّوع (meaning_type)\n\n")
    for mt, count in cards_by_type.most_common(25):
        lines.append(f"- `{mt}`: **{count}**\n")
    lines.append("\n### حَسَب القابِليَّة لِلتَّشغيل (engine_applicability)\n\n")
    for appl, count in cards_by_applicability.most_common():
        lines.append(f"- `{appl}`: **{count}**\n")
    lines.append(f"\n- بِطاقات لِلمُراجَعَة فَقَط: **{len(review_only_cards)}**\n\n")

    # ── 4. Engine Mapping ───────────────────────────────────────────
    lines.append("## 4. تَحويل لِلمُحَرِّك (Engine Mapping)\n\n")
    lines.append(f"- إِجماليّ construction_rules: **{len(constructions)}**\n")
    from_cards = sum(1 for c in constructions if c.get("source_meaning_card"))
    legacy = len(constructions) - from_cards
    lines.append(f"  - مِن meaning_cards (الجَديد): **{from_cards}**\n")
    lines.append(f"  - legacy (rule_cards): **{legacy}**\n\n")

    # ── 5. OCR ──────────────────────────────────────────────────────
    lines.append("## 5. تَصحيحات OCR\n\n")
    lines.append(f"- إِجماليّ: **{len(corrections)}**\n")
    applied = sum(1 for c in corrections if c.get("action") == "applied")
    suggested = sum(1 for c in corrections if c.get("action") == "suggest_only")
    lines.append(f"  - مُطَبَّق: {applied}\n")
    lines.append(f"  - مُقتَرَح فَقَط: {suggested}\n\n")
    lines.append("### أَعلى 20 تَصحيحًا\n\n")
    for raw, freq in corr_freq.most_common(20):
        normalized = next((c["normalized"] for c in corrections if c["raw"] == raw), "")
        lines.append(f"- `{raw}` → `{normalized}` ({freq} مَرَّة)\n")
    lines.append("\n")

    # ── 6. Manual Review Queue ──────────────────────────────────────
    lines.append("## 6. طابور المُراجَعَة اليَدَويَّة\n\n")
    lines.append(f"- إِجماليّ سَجَلّات تَحتاج مُراجَعَة: **{len(review)}**\n\n")
    if review:
        lines.append("### عَيِّنات (أَوَّل 15)\n\n")
        for r in review[:15]:
            lines.append(f"- ج{r['part']} ص{r['page']}: {r.get('reason', '')}\n")
        lines.append("\n")

    # ── 7. Warnings ─────────────────────────────────────────────────
    lines.append("## 7. تَحذيرات\n\n")
    topics_zero_claims = []
    cards_by_topic = defaultdict(int)
    for c in cards:
        path = c.get("topic_path") or []
        if path:
            cards_by_topic[path[0]] += 1
    for t in topics:
        if cards_by_topic.get(t.get("title"), 0) == 0:
            topics_zero_claims.append(t.get("title"))
    if topics_zero_claims:
        lines.append(f"- topics بِلا meaning_cards ({len(topics_zero_claims)}):\n")
        for tt in topics_zero_claims[:20]:
            lines.append(f"  - {tt}\n")
        lines.append("\n")
    long_pages_no_claims = [c for c in coverage
                            if c.get("char_count", 0) > 1000 and c.get("claims_count", 0) == 0]
    if long_pages_no_claims:
        lines.append(f"- صَفَحات طَويلَة (>1000 حَرف) بِلا claims: **{len(long_pages_no_claims)}**\n")
    cards_no_examples = [c for c in cards if not c.get("examples")]
    if cards_no_examples:
        lines.append(f"- meaning_cards بِلا أَمثلة: **{len(cards_no_examples)}**\n")
    lines.append("\n")

    # ── 8. مَقاييس النَّجاح الجَديدَة ────────────────────────────────
    lines.append("## 8. مَقاييس النَّجاح\n\n")
    lines.append(f"| مَقياس | قِيمَة |\n|---|---|\n")
    lines.append(f"| Page Coverage | {pages_with_claims}/{total_pages} = "
                 f"{(pages_with_claims/total_pages*100 if total_pages else 0):.1f}% |\n")
    lines.append(f"| Claim Density | {(len(claims)/total_pages if total_pages else 0):.2f} claim/page |\n")
    lines.append(f"| Topic Coverage | {len(topic_titles)-len(topics_zero_claims)}/{len(topic_titles)} "
                 f"topic مُغَطَّى |\n")
    lines.append(f"| Engine Coverage | {from_cards} construction مِن {len(cards)} card "
                 f"({(from_cards/len(cards)*100 if cards else 0):.1f}%) |\n")
    lines.append(f"| Review Coverage | {len(review)} سَجَلّ في طابور المُراجَعَة |\n")
    lines.append("\n")

    lines.append("---\n")
    lines.append("_تَمَّ التَّوليد آليًّا. مَنهَج: open-ended semantic extraction._\n")

    return "".join(lines)


def write_report(processed_dir: str | Path, output_path: str | Path) -> str:
    content = build_report(processed_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return content
