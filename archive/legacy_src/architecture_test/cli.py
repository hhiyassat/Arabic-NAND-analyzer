"""CLI for the architecture test runner (معمار المعنى العربي)."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .pipeline import ArchitectureTestResult, run_architecture_test, run_sample_01
from .quran_ayah_loader import looks_like_ayah_ref, resolve_ayah_input
from .report import format_architecture_report
from .tokenize import validate_arabic_input

USAGE_EPILOG = """
Examples:
  python run_architecture_test_sample_01.py --sample-01
  python run_architecture_test_sample_01.py --ayah 94:6
  python run_architecture_test_sample_01.py 2:185
  python run_architecture_test_sample_01.py -t "إِنَّ مَعَ الْعُسْرِ يُسْرًا"
  python run_architecture_test_sample_01.py -t "ان مع العسر يسرا" -o out.txt

Unvocalized input is auto-diacritized via salehan/Models_gpt52 before analysis.
"""


@dataclass
class ResolvedInput:
    text: str
    reference: str | None
    quran_ayah: dict[str, Any] | None = None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run architecture test on Arabic text or Quran ayah reference",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=USAGE_EPILOG,
    )
    p.add_argument(
        "text_positional",
        nargs="?",
        help="Arabic text or surah:ayah (e.g. 2:185)",
    )
    p.add_argument("--text", "-t", help="Arabic ayah text (vocalized or unvocalized)")
    p.add_argument(
        "--ayah",
        "-a",
        metavar="SURAH:AYAH",
        help="Load ayah from quran-uthmani.txt (e.g. 94:6, Quran 2:185)",
    )
    p.add_argument(
        "--quran-text",
        type=Path,
        default=None,
        help="Path to quran-uthmani.txt",
    )
    p.add_argument("--file", "-f", type=Path, help="Read text from UTF-8 file")
    p.add_argument("--stdin", action="store_true", help="Read text from stdin")
    p.add_argument("--reference", "-r", help="Optional reference label (e.g. Quran 94:6)")
    p.add_argument("--context", "-c", help="Optional prior-context note")
    p.add_argument("--huruf", type=Path, default=None, help="huruf_maani_unified_master.xlsx")
    p.add_argument(
        "--weights",
        type=Path,
        default=None,
        help="Mushtaqat weights for analyze_word",
    )
    p.add_argument(
        "--weights-sheet",
        default="الأوزان_المصححة",
        help="Excel sheet name when using .xlsx weights",
    )
    p.add_argument(
        "--skip-analyze-word",
        action="store_true",
        help="Skip Step 0 (alasmaa/analyze_word.py)",
    )
    p.add_argument(
        "--gpt52-dir",
        type=Path,
        default=None,
        help="Path to salehan/Models_gpt52",
    )
    p.add_argument(
        "--skip-diacritize",
        action="store_true",
        help="Do not run Models_gpt52 even if input lacks tashkil",
    )
    p.add_argument(
        "--force-diacritize",
        action="store_true",
        help="Always run Models_gpt52 on input text",
    )
    p.add_argument("--json", action="store_true", help="Print JSON to stdout")
    p.add_argument("--output", "-o", type=Path, help="Write text report to file")
    p.add_argument(
        "--sample-01",
        action="store_true",
        help="Force default Sample 01 (Quran 94:6)",
    )
    return p


def validate_args(args: argparse.Namespace) -> None:
    if args.text_positional and args.text:
        raise ValueError("Use either positional text or --text, not both")
    if args.ayah and (args.text or args.text_positional):
        raise ValueError("Use either --ayah or --text/positional text, not both")
    if args.ayah and args.file:
        raise ValueError("Use either --ayah or --file, not both")


def positional_is_ayah_ref(args: argparse.Namespace) -> bool:
    return bool(
        args.text_positional
        and not args.text
        and looks_like_ayah_ref(args.text_positional)
    )


def has_explicit_input(args: argparse.Namespace) -> bool:
    return bool(
        args.text
        or args.text_positional
        or args.file
        or args.stdin
        or args.ayah
        or positional_is_ayah_ref(args)
    )


def pipeline_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "huruf_path": args.huruf,
        "weights_path": args.weights,
        "weights_sheet": args.weights_sheet,
        "skip_analyze_word": args.skip_analyze_word,
        "gpt52_dir": args.gpt52_dir,
        "skip_diacritize": args.skip_diacritize,
        "force_diacritize": args.force_diacritize,
    }


def read_file_or_stdin(args: argparse.Namespace) -> tuple[str, str | None]:
    if args.stdin:
        return sys.stdin.read(), args.reference
    if args.file:
        return Path(args.file).read_text(encoding="utf-8"), args.reference
    if args.text:
        return args.text, args.reference
    return "", None


def prompt_for_text() -> str:
    print("─" * 60, file=sys.stderr)
    print(" أدخل النص العربي (Enter فارغ أو Ctrl-D للإنهاء):", file=sys.stderr)
    print(" Type/paste Arabic text. Empty line or Ctrl-D ends input.", file=sys.stderr)
    print(" مثال نص: إِنَّ مَعَ الْعُسْرِ يُسْرًا", file=sys.stderr)
    print(" مثال آية: 94:6", file=sys.stderr)
    print("─" * 60, file=sys.stderr)
    sys.stderr.flush()
    lines: list[str] = []
    try:
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line == "" and lines:
                break
            if line:
                lines.append(line)
    except KeyboardInterrupt:
        print("\n(Interrupted)", file=sys.stderr)
        raise SystemExit(130) from None
    return "\n".join(lines).strip()


def resolve_ayah_reference(
    ref: str,
    *,
    quran_text: Path | None,
) -> ResolvedInput:
    text, reference, meta = resolve_ayah_input(ref, text_path=quran_text)
    return ResolvedInput(text=text, reference=reference, quran_ayah=meta)


def resolve_input(args: argparse.Namespace) -> ResolvedInput | None:
    """Return resolved text input, or None when --sample-01 (no text needed)."""
    if args.sample_01:
        return None

    ref = args.reference
    ayah_meta: dict[str, Any] | None = None

    if args.ayah or positional_is_ayah_ref(args):
        ayah_ref = args.ayah or args.text_positional
        resolved = resolve_ayah_reference(ayah_ref, quran_text=args.quran_text)
        print(f"آية {resolved.reference}: {resolved.text}", file=sys.stderr)
        return resolved

    if has_explicit_input(args):
        text, ref = read_file_or_stdin(args)
        if args.text_positional:
            text = args.text_positional
        text = (text or "").strip()
        if not text:
            raise ValueError(
                "No input text. Use --text, --ayah, --file, positional arg, or --stdin."
            )
        if looks_like_ayah_ref(text):
            resolved = resolve_ayah_reference(text, quran_text=args.quran_text)
            print(f"آية {resolved.reference}: {resolved.text}", file=sys.stderr)
            return resolved
        validate_arabic_input(text)
        return ResolvedInput(text=text, reference=ref)

    text = prompt_for_text()
    if not text:
        raise ValueError(
            "No input text received. Provide via --text/-t, --ayah/-a, "
            "--file/-f, positional arg, --stdin, or --sample-01."
        )
    if looks_like_ayah_ref(text):
        resolved = resolve_ayah_reference(text, quran_text=args.quran_text)
        print(f"آية {resolved.reference}: {resolved.text}", file=sys.stderr)
        return resolved
    validate_arabic_input(text)
    return ResolvedInput(text=text, reference=ref)


def run_architecture_cli(args: argparse.Namespace) -> ArchitectureTestResult:
    """Execute pipeline from parsed CLI arguments."""
    validate_args(args)
    kw = pipeline_kwargs(args)

    if args.sample_01:
        return run_sample_01(**kw)

    resolved = resolve_input(args)
    assert resolved is not None
    result = run_architecture_test(
        resolved.text,
        reference=resolved.reference or args.reference,
        context=args.context,
        **kw,
    )
    if resolved.quran_ayah:
        result.sample["quran_ayah"] = resolved.quran_ayah
    return result


def print_diacritization_notice(result: ArchitectureTestResult) -> None:
    dia = result.diacritization or {}
    if not dia.get("applied"):
        return
    print("─" * 60, file=sys.stderr)
    print(" التشكيل (Models_gpt52)", file=sys.stderr)
    print(f" النص الأصلي : {dia.get('text_raw', '')}", file=sys.stderr)
    print(f" النص المشكول : {dia.get('text_vocalized', '')}", file=sys.stderr)
    print("─" * 60, file=sys.stderr)


def emit_result(result: ArchitectureTestResult, args: argparse.Namespace) -> None:
    print_diacritization_notice(result)
    report = format_architecture_report(result)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        if not args.json:
            print(f"\nReport written: {args.output}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_architecture_cli(args)
    except ValueError as exc:
        parser.error(str(exc))
    except FileNotFoundError as exc:
        parser.error(str(exc))
    emit_result(result, args)
    return 0
