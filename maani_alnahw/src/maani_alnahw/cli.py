"""cli.py — واجِهَة سَطر الأَوامِر.

الأَوامِر:
  split-pages       — تَقسيم الصَّفحات
  normalize         — تَنظيف OCR
  detect-topics     — كَشف الأَبواب
  extract-rules     — استخراج بِطاقات القَواعِد
  extract-examples  — استخراج الأَمثلة
  extract-opinions  — استخراج الخِلاف
  build-constructions — تَوليد قَواعِد التَّراكيب
  report            — تَوليد التَّقرير
  all               — كُلّ الخَطَوات بِالتَّسَلسُل
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from maani_alnahw import page_splitter, ocr_normalizer, topic_detector
from maani_alnahw import rule_extractor, example_extractor, opinion_extractor
from maani_alnahw import construction_mapper, exporter
from maani_alnahw import semantic_claim_extractor, meaning_card_builder
from maani_alnahw import coverage_analyzer, manual_review


def cmd_split(args):
    pages = page_splitter.split_directory(args.input)
    n = page_splitter.write_jsonl(pages, args.output)
    print(f"split-pages: {n} صَفحَة → {args.output}")


def cmd_normalize(args):
    pages = page_splitter.read_jsonl(args.input)
    cleaned, corrections = ocr_normalizer.normalize_pages(pages)
    n1 = ocr_normalizer.write_pages_jsonl(cleaned, args.output)
    corr_path = Path(args.output).parent / "ocr_corrections.jsonl"
    n2 = ocr_normalizer.write_corrections_jsonl(corrections, corr_path)
    print(f"normalize: {n1} صَفحَة، {n2} تَصحيح → {args.output} + {corr_path}")


def cmd_detect_topics(args):
    pages = page_splitter.read_jsonl(args.input)
    detector = topic_detector.TopicDetector()
    topics = detector.detect(pages)
    n = topic_detector.write_topics_jsonl(topics, args.output)
    print(f"detect-topics: {n} عُنوان → {args.output}")


def cmd_extract_rules(args):
    pages = page_splitter.read_jsonl(args.pages)
    topics = page_splitter.read_jsonl(args.topics)
    rules = rule_extractor.extract_all_rules(pages, topics)
    n = rule_extractor.write_rule_cards_jsonl(rules, args.output)
    print(f"extract-rules: {n} قاعِدَة → {args.output}")


def cmd_extract_examples(args):
    pages = page_splitter.read_jsonl(args.pages)
    rules = page_splitter.read_jsonl(args.rules)
    examples = example_extractor.extract_examples(pages, rules)
    n = example_extractor.write_examples_jsonl(examples, args.output)
    print(f"extract-examples: {n} مِثال → {args.output}")


def cmd_extract_opinions(args):
    pages = page_splitter.read_jsonl(args.pages)
    topics = page_splitter.read_jsonl(args.topics)
    opinions = opinion_extractor.extract_all_opinions(pages, topics)
    n = opinion_extractor.write_opinions_jsonl(opinions, args.output)
    print(f"extract-opinions: {n} مَوضِع خِلاف → {args.output}")


def cmd_build_constructions(args):
    rules = page_splitter.read_jsonl(args.rules)
    constructions = construction_mapper.build_constructions(rules)
    n = construction_mapper.write_constructions_jsonl(constructions, args.output)
    print(f"build-constructions: {n} تَركيب → {args.output}")


def cmd_report(args):
    exporter.write_report(args.processed, args.output)
    print(f"report → {args.output}")


def cmd_extract_claims(args):
    pages = page_splitter.read_jsonl(args.pages)
    topics = page_splitter.read_jsonl(args.topics)
    claims = semantic_claim_extractor.extract_claims_from_pages(pages, topics)
    n = semantic_claim_extractor.write_claims_jsonl(claims, args.output)
    print(f"extract-claims: {n} claim → {args.output}")


def cmd_build_meaning_cards(args):
    claims = page_splitter.read_jsonl(args.claims)
    cards = meaning_card_builder.build_meaning_cards(claims)
    n = meaning_card_builder.write_cards_jsonl(cards, args.output)
    idx = meaning_card_builder.build_meaning_index([c.to_dict() for c in cards])
    idx_path = Path(args.output).parent / "meaning_index.jsonl"
    n2 = meaning_card_builder.write_index_jsonl(idx, idx_path)
    print(f"build-meaning-cards: {n} card، {n2} index → {args.output}")


def cmd_analyze_coverage(args):
    pages = page_splitter.read_jsonl(args.pages)
    claims = page_splitter.read_jsonl(args.claims)
    cards = page_splitter.read_jsonl(args.cards)
    corrections = page_splitter.read_jsonl(
        str(Path(args.pages).parent / "ocr_corrections.jsonl")
    )
    topics = page_splitter.read_jsonl(
        str(Path(args.pages).parent / "topics.jsonl")
    )
    coverage = coverage_analyzer.build_page_coverage(
        pages, claims, cards, corrections, topics
    )
    n = coverage_analyzer.write_coverage_jsonl(coverage, args.output)
    # manual review
    review_items = manual_review.build_review_queue(
        pages, claims, cards,
        [c.to_dict() for c in coverage], topics,
    )
    review_path = Path(args.output).parent / "manual_review_queue.jsonl"
    n2 = manual_review.write_review_jsonl(review_items, review_path)
    print(f"analyze-coverage: {n} page، {n2} review items → {args.output}")


def cmd_all(args):
    root = Path(args.root)
    raw_dir = root / "data" / "raw" / "maani_alnahw"
    proc_dir = root / "data" / "processed" / "maani_alnahw"
    proc_dir.mkdir(parents=True, exist_ok=True)

    pages = page_splitter.split_directory(raw_dir)
    page_splitter.write_jsonl(pages, proc_dir / "pages.jsonl")
    print(f"  ✓ split-pages: {len(pages)}")

    cleaned, corrections = ocr_normalizer.normalize_pages(
        [p.to_dict() for p in pages]
    )
    ocr_normalizer.write_pages_jsonl(cleaned, proc_dir / "cleaned_pages.jsonl")
    ocr_normalizer.write_corrections_jsonl(corrections, proc_dir / "ocr_corrections.jsonl")
    print(f"  ✓ normalize: {len(corrections)} تَصحيح")

    detector = topic_detector.TopicDetector()
    topics_objs = detector.detect(cleaned)
    topic_detector.write_topics_jsonl(topics_objs, proc_dir / "topics.jsonl")
    topics = [t.to_dict() for t in topics_objs]
    print(f"  ✓ detect-topics: {len(topics)}")

    rule_objs = rule_extractor.extract_all_rules(cleaned, topics)
    rule_extractor.write_rule_cards_jsonl(rule_objs, proc_dir / "rule_cards.jsonl")
    rules = [r.to_dict() for r in rule_objs]
    print(f"  ✓ extract-rules: {len(rules)}")

    ex_objs = example_extractor.extract_examples(cleaned, rules)
    example_extractor.write_examples_jsonl(ex_objs, proc_dir / "examples.jsonl")
    print(f"  ✓ extract-examples: {len(ex_objs)}")

    op_objs = opinion_extractor.extract_all_opinions(cleaned, topics)
    opinion_extractor.write_opinions_jsonl(op_objs, proc_dir / "opinions.jsonl")
    print(f"  ✓ extract-opinions: {len(op_objs)}")

    # ── المَرحَلَة 4: استخراج SemanticClaims (open-ended) ──
    claim_objs = semantic_claim_extractor.extract_claims_from_pages(cleaned, topics)
    semantic_claim_extractor.write_claims_jsonl(claim_objs, proc_dir / "semantic_claims.jsonl")
    claims = [c.to_dict() for c in claim_objs]
    print(f"  ✓ extract-claims: {len(claims)} claim")

    # ── المَرحَلَة 5: بِناء MeaningCards ──
    card_objs = meaning_card_builder.build_meaning_cards(claims)
    meaning_card_builder.write_cards_jsonl(card_objs, proc_dir / "meaning_cards.jsonl")
    cards = [c.to_dict() for c in card_objs]
    idx = meaning_card_builder.build_meaning_index(cards)
    meaning_card_builder.write_index_jsonl(idx, proc_dir / "meaning_index.jsonl")
    print(f"  ✓ meaning-cards: {len(cards)} card")

    # ── المَرحَلَة 6: constructions كَ subset مِن meaning_cards ──
    constructions_from_cards = construction_mapper.build_constructions_from_meaning_cards(cards)
    # نَدمِج مَع الـ legacy constructions (rule_cards)
    legacy_constructions = construction_mapper.build_constructions(rules)
    all_constructions = constructions_from_cards + legacy_constructions
    construction_mapper.write_constructions_jsonl(
        all_constructions, proc_dir / "construction_rules.jsonl"
    )
    print(f"  ✓ build-constructions: {len(all_constructions)} "
          f"(مِن meaning_cards: {len(constructions_from_cards)}، legacy: {len(legacy_constructions)})")

    # ── المَرحَلَة 7: Coverage + Manual Review ──
    corrections_objs = page_splitter.read_jsonl(proc_dir / "ocr_corrections.jsonl")
    coverage_objs = coverage_analyzer.build_page_coverage(
        cleaned, claims, cards, corrections_objs, topics
    )
    coverage_analyzer.write_coverage_jsonl(coverage_objs, proc_dir / "page_coverage.jsonl")
    coverage_dicts = [c.to_dict() for c in coverage_objs]
    review_items = manual_review.build_review_queue(
        cleaned, claims, cards, coverage_dicts, topics
    )
    manual_review.write_review_jsonl(review_items, proc_dir / "manual_review_queue.jsonl")
    print(f"  ✓ coverage: {len(coverage_objs)} page، {len(review_items)} review item")

    exporter.write_report(proc_dir, proc_dir / "extraction_report.md")
    print(f"  ✓ report: {proc_dir / 'extraction_report.md'}")


def main():
    parser = argparse.ArgumentParser(prog="maani_alnahw", description="Maani Al-Nahw KB builder")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("split-pages")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_split)

    p = sub.add_parser("normalize")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_normalize)

    p = sub.add_parser("detect-topics")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_detect_topics)

    p = sub.add_parser("extract-rules")
    p.add_argument("--pages", required=True)
    p.add_argument("--topics", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_extract_rules)

    p = sub.add_parser("extract-examples")
    p.add_argument("--pages", required=True)
    p.add_argument("--rules", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_extract_examples)

    p = sub.add_parser("extract-opinions")
    p.add_argument("--pages", required=True)
    p.add_argument("--topics", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_extract_opinions)

    p = sub.add_parser("build-constructions")
    p.add_argument("--rules", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_build_constructions)

    p = sub.add_parser("extract-claims")
    p.add_argument("--pages", required=True)
    p.add_argument("--topics", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_extract_claims)

    p = sub.add_parser("build-meaning-cards")
    p.add_argument("--claims", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_build_meaning_cards)

    p = sub.add_parser("analyze-coverage")
    p.add_argument("--pages", required=True)
    p.add_argument("--claims", required=True)
    p.add_argument("--cards", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_analyze_coverage)

    p = sub.add_parser("report")
    p.add_argument("--processed", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("all", help="تَنفيذ كُلّ الخَطَوات")
    p.add_argument("--root", default=".", help="جَذر المَشروع (يَحوي data/)")
    p.set_defaults(func=cmd_all)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
