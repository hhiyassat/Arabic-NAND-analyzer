"""analyze_text.py — تَحليل نَحويّ-دَلاليّ لِأَيّ نَصّ عَرَبيّ.

يَأخُذ نَصًّا عامًّا (لَيسَ بِالضَّرورَة قُرآنًا) وَ يُطَبِّق:
  1. تَوكينَة بَسيطَة
  2. الكَشف عَن العَوامِل الـ 97 (operators_catalog)
  3. الإِثراء بِالبَطاقات مِن «مَعاني النَّحو»
  4. مُلَخَّص دَلاليّ

استِخدام:
  python3 analyze_text.py "إنّ الله غفور رحيم"
  python3 analyze_text.py --file my_text.txt
  python3 analyze_text.py --json "نص ما"
  echo "نَصّ" | python3 analyze_text.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import operators_loader


# ─── تَحميل العَوامِل المُثراة ────────────────────────────────────────

_ENRICHED_PATH = (_HERE.parent / "maani_alnahw" / "data" / "processed"
                   / "maani_alnahw" / "operators_enriched.jsonl")
_ENRICHED_CACHE: dict | None = None


def _load_enriched() -> dict:
    """يُحَمِّل operators_enriched.jsonl كَخَريطَة operator_plain → سَجِلّ."""
    global _ENRICHED_CACHE
    if _ENRICHED_CACHE is not None:
        return _ENRICHED_CACHE
    cache = {}
    if _ENRICHED_PATH.exists():
        with open(_ENRICHED_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rec = json.loads(line)
                        cache[rec["operator_plain"]] = rec
                    except json.JSONDecodeError:
                        pass
    _ENRICHED_CACHE = cache
    return cache


# ─── أَدوات نَصّيَّة ──────────────────────────────────────────────────

DIACRITICS = "ًٌٍَُِّْـٰٓ"
PAUSE_MARKS = "ۖۗۘۙۚۛۜ۝ۭۢۥۤۧۨ"
PUNCT = "،؛؟.!:،\"'(){}[]«»"


def _strip_pause_marks(s: str) -> str:
    return "".join(c for c in s if c not in PAUSE_MARKS)


def _tokenize(text: str) -> list[str]:
    cleaned = _strip_pause_marks(text)
    # نَستَبدِل عَلامات التَّرقيم بِمَسافات
    for p in PUNCT:
        cleaned = cleaned.replace(p, " ")
    return [t.strip() for t in cleaned.split() if t.strip()]


# ─── المُحَلِّل الرَّئيس ────────────────────────────────────────────

CONTRACT_NAME = "TextAnalyzer:v1"


def analyze_text(text: str, source: str = "") -> dict:
    """يُحَلِّل نَصًّا عامًّا وَ يَرجِع نَتيجَة هيكَليَّة."""
    tokens = _tokenize(text)
    enriched = _load_enriched()

    findings = []
    for position, token in enumerate(tokens):
        op_match = operators_loader.lookup_in_word(token)
        if op_match is None:
            continue
        operator_plain = op_match["operator_plain"]
        enrich = enriched.get(operator_plain)

        finding = {
            "position": position,
            "token": token,
            "operator": op_match["operator"],
            "group_id": op_match["group_id"],
            "group_name": op_match["group_ar"],
            "purpose": op_match["purpose"],
            "catalog_example": op_match.get("example_vocalized") or op_match.get("example", ""),
            "match_type": op_match["_match_info"]["match_type"],
            "is_priority": op_match["is_priority"],
            "is_enriched": enrich is not None and enrich.get("is_enriched", False),
        }

        if enrich and enrich.get("is_enriched"):
            # نُضيف الإِثراء
            rule_card = enrich.get("rule_card_from_maani")
            if rule_card:
                finding["maani_rule"] = {
                    "title": rule_card.get("title"),
                    "syntactic_effect": rule_card.get("syntactic_effect"),
                    "semantic_effect": rule_card.get("semantic_effect"),
                    "author_position": rule_card.get("author_position"),
                }
            cards = enrich.get("related_meaning_cards") or []
            if cards:
                finding["meaning_cards"] = cards[:3]  # أَعلى 3 لِلعَرض
            if enrich.get("warnings"):
                finding["warnings"] = enrich["warnings"][:3]
            if enrich.get("author_examples"):
                finding["author_examples"] = enrich["author_examples"][:2]

        findings.append(finding)

    return {
        "contract": CONTRACT_NAME,
        "source": source,
        "text": text,
        "n_words": len(tokens),
        "n_findings": len(findings),
        "tokens": tokens,
        "findings": findings,
    }


# ─── التَّنسيق ──────────────────────────────────────────────────────

def format_arabic(result: dict, show_examples: bool = True) -> str:
    """تَنسيق عَرَبيّ مَقروء."""
    lines = []
    box_w = 78

    def _hr(c="═"):
        return c * box_w

    lines.append(_hr("═"))
    lines.append("  مُحَلِّل النَّصّ العَرَبيّ — TextAnalyzer:v1")
    lines.append(_hr("═"))
    if result.get("source"):
        lines.append(f"  المَصدَر: {result['source']}")
    lines.append(f"  النَّصّ:  {result['text'][:80]}{'...' if len(result['text']) > 80 else ''}")
    lines.append(f"  الكَلِمات: {result['n_words']} · المُطابَقات: {result['n_findings']}")

    findings = result.get("findings", [])
    if not findings:
        lines.append("")
        lines.append("  لا عَوامِل مَكشوفَة في النَّصّ.")
        lines.append(_hr("═"))
        return "\n".join(lines)

    for i, f in enumerate(findings, 1):
        lines.append("")
        lines.append(_hr("─"))
        priority_tag = " ⭐" if f.get("is_priority") else ""
        enriched_tag = " 📚" if f.get("is_enriched") else ""
        lines.append(f"  ◆ [{i}] «{f['token']}» → {f['operator']}{priority_tag}{enriched_tag}")
        lines.append(_hr("─"))
        lines.append(f"     • المَجموعَة:   {f['group_id']} — {f['group_name']}")
        lines.append(f"     • الغَرَض:      {f['purpose']}")
        lines.append(f"     • مِثال شَرحيّ: {f['catalog_example']}")

        if f.get("maani_rule"):
            mr = f["maani_rule"]
            lines.append("")
            lines.append(f"     ▸ مِن مَعاني النَّحو:")
            if mr.get("title"):
                lines.append(f"        • العُنوان: {mr['title']}")
            se = mr.get("syntactic_effect")
            if isinstance(se, dict):
                for k, v in list(se.items())[:3]:
                    lines.append(f"        • {k}: {str(v)[:60]}")
            sem = mr.get("semantic_effect")
            if isinstance(sem, dict) and sem.get("description"):
                lines.append(f"        • المَعنى: {sem['description'][:100]}")
            if mr.get("author_position"):
                lines.append(f"        • رأي المُؤَلِّف: {mr['author_position'][:80]}")

        if f.get("meaning_cards") and show_examples:
            lines.append("")
            lines.append(f"     ▸ بِطاقات مَعنى ({len(f['meaning_cards'])}):")
            for c in f["meaning_cards"]:
                lines.append(f"        ◇ {c['title'][:70]}")
                if c.get("description_excerpt"):
                    lines.append(f"          {c['description_excerpt'][:100]}")

        if f.get("warnings"):
            lines.append("")
            lines.append(f"     ▸ تَحذيرات:")
            for w in f["warnings"]:
                lines.append(f"        ⚠ {w[:120]}")

        if f.get("author_examples") and show_examples:
            lines.append("")
            lines.append(f"     ▸ أَمثلَة مِن المُؤَلِّف:")
            for ex in f["author_examples"]:
                txt = ex.get("text", "")
                if txt:
                    lines.append(f"        • «{txt[:80]}»")

    lines.append("")
    lines.append(_hr("═"))
    lines.append(f"  انتَهى التَّحليل. ⭐ = أولَويَّة، 📚 = مُثرى بِمَعاني النَّحو")
    lines.append(_hr("═"))
    return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="تَحليل نَحويّ-دَلاليّ لِنَصّ عَرَبيّ عامّ"
    )
    ap.add_argument("text", nargs="?", help="النَّصّ المُراد تَحليله (أَو stdin)")
    ap.add_argument("--file", help="قِراءَة النَّصّ مِن مَلَفّ")
    ap.add_argument("--json", action="store_true", help="إِخراج JSON")
    ap.add_argument("--no-examples", action="store_true",
                    help="إِخفاء الأَمثلَة الإِضافيَّة (إِيجاز)")
    args = ap.parse_args()

    text = ""
    source = ""
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
        source = f"file:{args.file}"
    elif args.text:
        text = args.text
        source = "inline"
    else:
        text = sys.stdin.read().strip()
        source = "stdin"

    if not text:
        print("خَطَأ: لَم يُمَرَّر نَصّ.", file=sys.stderr)
        sys.exit(1)

    result = analyze_text(text, source=source)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_arabic(result, show_examples=not args.no_examples))


if __name__ == "__main__":
    main()
