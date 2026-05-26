"""download_shamela_book.py — تَنزيل أَيّ كِتاب مِن المَكتَبَة الشاملَة.

استِخدام:
  python3 scripts/download_shamela_book.py --book-id 23627
  python3 scripts/download_shamela_book.py --url https://shamela.ws/book/23627
  python3 scripts/download_shamela_book.py --book-id 23627 --slug kashaf
  python3 scripts/download_shamela_book.py --book-id 1234 --delay 2.0

الخَصائص:
  • generic — أَيّ كِتاب في الشاملَة (لا hard-coding)
  • يَكشِف اسم الكِتاب + المُؤَلِّف تِلقائيًّا مِن الفِهرِس
  • يَحفَظ التَّشكيل كامِلًا (لا تَطبيع)
  • user-agent مُحتَرَم + retry + delay + استِئناف
  • مُخرَج في data/raw/{slug}/ تِلقائيًّا
  • تَقرير شامِل بَعد التَّشغيل

اعتمادات:
  pip install requests beautifulsoup4
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("خَطَأ: تَحتاج تَثبيت requests — `pip install requests`", file=sys.stderr)
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("خَطَأ: تَحتاج تَثبيت beautifulsoup4 — `pip install beautifulsoup4`",
          file=sys.stderr)
    sys.exit(1)


# ─── ثَوابِت عامَّة ──────────────────────────────────────────────────────

SHAMELA_BASE = "https://shamela.ws"

DEFAULT_DELAY = 1.5
MAX_RETRIES = 3
TIMEOUT = 30

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15 "
    "(Educational research; Arabic NLP project)"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ─── parsing ID مِن URL ─────────────────────────────────────────────────

def parse_book_id(arg: str) -> str:
    """يَقبَل '23627' أَو 'https://shamela.ws/book/23627' أَو '.../book/23627/5'."""
    arg = arg.strip()
    if arg.isdigit():
        return arg
    m = re.search(r"/book/(\d+)", arg)
    if m:
        return m.group(1)
    raise ValueError(f"لَم نَستَطِع استخراج book_id مِن: {arg}")


# ─── slug — اسم مُجَلَّد آمِن ────────────────────────────────────────────

ARABIC_DIACRITICS = "ًٌٍَُِّْـٰٓ"


def make_slug(name: str, book_id: str) -> str:
    """يُحَوِّل اسم عَرَبيّ إلى slug لاتينيّ-آمِن لِلمُجَلَّد."""
    if not name:
        return f"shamela_{book_id}"
    # نَزع التَّشكيل
    base = "".join(c for c in name if c not in ARABIC_DIACRITICS)
    # نَزع رُموز خاصَّة
    base = re.sub(r"[^\w؀-ۿ\s]+", "", base, flags=re.UNICODE)
    # تَطبيع ال + هَمزَة
    base = base.replace("ال", "").strip()
    # نَزع المَسافات وَ استبدالها بِـ _
    base = re.sub(r"\s+", "_", base)
    # إِن لَم يَبقَ شَيء، نَعتَمِد book_id
    if not base or len(base) > 40:
        # نَأخُذ أَوَّل كَلِمَة فَقَط
        first = name.split()[0] if name.split() else ""
        first_clean = "".join(c for c in first if c not in ARABIC_DIACRITICS)
        if first_clean:
            base = re.sub(r"[^\w؀-ۿ]+", "", first_clean)
        else:
            base = f"shamela_{book_id}"
    return base


# ─── أَدوات شَبَكَة ──────────────────────────────────────────────────────

def fetch_with_retries(url: str, session: requests.Session,
                        max_retries: int = MAX_RETRIES,
                        timeout: int = TIMEOUT) -> requests.Response | None:
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, headers=HEADERS, timeout=timeout)
            if resp.status_code == 200:
                return resp
            elif resp.status_code in (429, 500, 502, 503, 504):
                wait = attempt * 5
                print(f"    [{attempt}/{max_retries}] {resp.status_code} — اِنتِظار {wait}ث...",
                      file=sys.stderr)
                time.sleep(wait)
                continue
            elif resp.status_code == 404:
                return resp
            else:
                print(f"    [{attempt}/{max_retries}] HTTP {resp.status_code}",
                      file=sys.stderr)
                time.sleep(attempt * 2)
        except requests.exceptions.RequestException as e:
            print(f"    [{attempt}/{max_retries}] خَطَأ: {e}", file=sys.stderr)
            if attempt < max_retries:
                time.sleep(attempt * 3)
    return None


# ─── كَشف الـ metadata ────────────────────────────────────────────────

def detect_book_metadata(html: str) -> dict:
    """يَكشِف اسم الكِتاب + المُؤَلِّف + عَدَد الصَّفَحات مِن صَفحَة الفِهرِس."""
    soup = BeautifulSoup(html, "html.parser")
    meta = {"name": None, "author": None, "max_page": None}

    # 1. اسم الكِتاب — مِن <title> أَو <h1>
    title_tag = soup.find("title")
    if title_tag:
        title_text = title_tag.get_text(strip=True)
        # شاملَة عادَةً: «اسم الكتاب - المكتبة الشاملة الحديثة»
        if " - " in title_text:
            meta["name"] = title_text.split(" - ")[0].strip()
        else:
            meta["name"] = title_text
    if not meta["name"]:
        h1 = soup.find("h1")
        if h1:
            meta["name"] = h1.get_text(strip=True)

    # 2. المُؤَلِّف — نَبحَث في الـ meta tags أَو في النَّصّ
    # شاملَة تَستَخدِم أَحيانًا <span> أَو <div> مَع تَسميَة «المؤلف»
    for label in ["المؤلف", "تأليف", "اسم المؤلف"]:
        # نَبحَث عَن العُنصُر الَّذي يَحوي اللَّفظ
        for tag in soup.find_all(string=re.compile(label)):
            parent = tag.parent
            if parent:
                # نَستَخرِج النَّصّ التالي
                next_text = ""
                # نُجَرِّب أَخا الـ tag
                sib = parent.find_next_sibling()
                if sib:
                    next_text = sib.get_text(strip=True)
                if not next_text:
                    # نَستَخرِج بَقيَّة نَصّ الأَب
                    full = parent.get_text(strip=True)
                    if label in full:
                        after = full.split(label, 1)[1]
                        next_text = after.lstrip(": ").strip()
                if next_text and 3 < len(next_text) < 100:
                    meta["author"] = next_text
                    break
        if meta["author"]:
            break

    # 3. أَقصى صَفحَة
    max_page = 0
    book_id_in_url = None
    # نَستَخرِج book_id مِن أَوَّل رابِط داخِليّ
    for a in soup.find_all("a", href=True):
        m = re.search(r"/book/(\d+)/(\d+)", a["href"])
        if m:
            book_id_in_url = m.group(1)
            n = int(m.group(2))
            if n > max_page:
                max_page = n
    if max_page > 0:
        meta["max_page"] = max_page

    return meta


# ─── تَحليل صَفحَة المُحتَوى ─────────────────────────────────────────────

def parse_page(html: str, url: str, page_no: int, book_meta: dict, book_id: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    content_candidates = [
        ("div", {"class": "nass"}),
        ("div", {"id": "book-text"}),
        ("div", {"class": "text"}),
        ("div", {"class": "page-content"}),
        ("div", {"id": "content"}),
        ("article", {}),
    ]
    raw_text = ""
    for tag, attrs in content_candidates:
        node = soup.find(tag, attrs)
        if node:
            raw_text = node.get_text(separator="\n", strip=True)
            if raw_text:
                break
    if not raw_text:
        for s in soup(["script", "style", "nav", "header", "footer"]):
            s.decompose()
        raw_text = soup.get_text(separator="\n", strip=True)

    section_title = None
    for tag, attrs in [("h1", {}), ("h2", {}),
                        ("div", {"class": "title"}),
                        ("span", {"class": "section-title"})]:
        node = soup.find(tag, attrs)
        if node:
            t = node.get_text(strip=True)
            if t and len(t) < 200:
                section_title = t
                break

    # تَنظيف خَفيف — أَسطُر فارِغَة فَقَط
    # (لا نَنزِع التَّشكيل — يَبقى كَما هو)
    lines = [l.rstrip() for l in raw_text.split("\n")]
    lines = [l for l in lines if l.strip()]
    raw_text = "\n".join(lines)

    # هَل النَّصّ يَحوي تَشكيل؟
    has_diacritics = any(c in raw_text for c in ARABIC_DIACRITICS)

    return {
        "book": book_meta.get("name") or f"shamela_{book_id}",
        "author": book_meta.get("author"),
        "source": "shamela",
        "book_id": book_id,
        "url": url,
        "page_no": page_no,
        "section_title": section_title,
        "raw_text": raw_text,
        "has_diacritics": has_diacritics,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
    }


# ─── الـ JSONL ──────────────────────────────────────────────────────────

def load_completed_pages(path: Path) -> set[int]:
    completed = set()
    if not path.exists():
        return completed
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("page_no") is not None and rec.get("raw_text"):
                    completed.add(rec["page_no"])
            except json.JSONDecodeError:
                pass
    return completed


def append_record(path: Path, record: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ─── التَّقرير ─────────────────────────────────────────────────────────

def write_report(report: dict, raw_dir: Path, book_meta: dict, book_id: str,
                  output_jsonl_name: str, index_html_name: str):
    lines = []
    book_name = book_meta.get("name") or f"shamela_{book_id}"
    lines.append(f"# تَقرير تَنزيل «{book_name}» مِن الشاملَة\n\n")
    lines.append(f"- المَصدَر: {SHAMELA_BASE}/book/{book_id}\n")
    lines.append(f"- المُؤَلِّف: {book_meta.get('author') or '(لَم يُكشَف)'}\n")
    lines.append(f"- تاريخ التَّنزيل: {datetime.now(timezone.utc).isoformat()}\n\n")
    lines.append(f"## الإِحصاءات\n\n")
    lines.append(f"- صَفَحات مُكتَشَفَة في الفِهرِس: {report.get('total_pages_detected', '?')}\n")
    lines.append(f"- صَفَحات مُنَزَّلَة: {report.get('downloaded_pages', 0)}\n")
    lines.append(f"- صَفَحات بِتَشكيل: {report.get('pages_with_diacritics', 0)}\n")
    lines.append(f"- صَفَحات بِلا تَشكيل: {report.get('pages_without_diacritics', 0)}\n")
    lines.append(f"- صَفَحات فاشِلَة: {report.get('failed_pages', 0)}\n")
    lines.append(f"- صَفَحات مُتَخَطّاة: {report.get('skipped_pages', 0)}\n\n")
    if report.get("errors"):
        lines.append(f"## أَخطاء\n\n")
        for err in report["errors"][:50]:
            lines.append(f"- صَفحَة {err['page_no']}: {err['reason']}\n")
        lines.append("\n")
    if report.get("warnings"):
        lines.append(f"## تَحذيرات\n\n")
        for w in report["warnings"]:
            lines.append(f"- {w}\n")
        lines.append("\n")
    lines.append(f"## المُخرَجات\n\n")
    lines.append(f"- البَيانات الخام: `{output_jsonl_name}`\n")
    lines.append(f"- نُسخَة الفِهرِس: `{index_html_name}`\n")
    report_path = raw_dir / "download_report.md"
    report_path.write_text("".join(lines), encoding="utf-8")
    print(f"  ✓ تَقرير: {report_path}")


# ─── المُحَرِّك ────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="تَنزيل أَيّ كِتاب مِن المَكتَبَة الشاملَة")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--book-id", help="رَقم الكِتاب (مَثَلًا 23627)")
    g.add_argument("--url", help="رابِط الكِتاب الكامِل (مَثَلًا https://shamela.ws/book/23627)")

    ap.add_argument("--slug", default=None,
                    help="اسم المُجَلَّد (يُكشَف تِلقائيًّا إِن لَم يُمَرَّر)")
    ap.add_argument("--out-dir", default=None,
                    help="مُجَلَّد المُخرَجات (افتراضيّ data/raw/{slug}/)")
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--max-empty-streak", type=int, default=10)
    args = ap.parse_args()

    # 1. حُصول عَلى book_id
    src = args.book_id or args.url
    try:
        book_id = parse_book_id(src)
    except ValueError as e:
        print(f"خَطَأ: {e}", file=sys.stderr)
        sys.exit(2)

    session = requests.Session()
    base_url = f"{SHAMELA_BASE}/book/{book_id}"
    print(f"  ► كِتاب رَقم: {book_id}")
    print(f"  ► رابِط أَساسيّ: {base_url}")

    # 2. الفِهرِس + كَشف الـ metadata
    print(f"  → جَلب الفِهرِس...")
    resp = fetch_with_retries(base_url, session)
    if not resp or resp.status_code != 200:
        print(f"خَطَأ: تَعَذَّر جَلب الفِهرِس (status={resp.status_code if resp else 'no response'})",
              file=sys.stderr)
        sys.exit(3)
    index_html = resp.text

    book_meta = detect_book_metadata(index_html)
    print(f"  ✓ اسم الكِتاب: {book_meta.get('name') or '(غَير مَعروف)'}")
    print(f"  ✓ المُؤَلِّف:   {book_meta.get('author') or '(غَير مَعروف)'}")
    print(f"  ✓ عَدَد الصَّفَحات المُكتَشَف: {book_meta.get('max_page') or '?'}")

    # 3. slug + مُجَلَّد المُخرَجات
    slug = args.slug or make_slug(book_meta.get("name") or "", book_id)
    if args.out_dir:
        raw_dir = Path(args.out_dir)
    else:
        raw_dir = PROJECT_ROOT / "data" / "raw" / slug
    raw_dir.mkdir(parents=True, exist_ok=True)
    print(f"  ► slug: {slug}")
    print(f"  ► مُجَلَّد المُخرَجات: {raw_dir}")

    output_jsonl = raw_dir / f"{slug}_raw_pages.jsonl"
    index_html_path = raw_dir / f"{slug}_index.html"
    index_html_path.write_text(index_html, encoding="utf-8")

    if args.no_resume and output_jsonl.exists():
        backup = output_jsonl.with_suffix(".jsonl.bak")
        output_jsonl.rename(backup)
        print(f"  ⚠ نُسخَة احتِياط: {backup.name}")

    completed = load_completed_pages(output_jsonl)
    print(f"  ► صَفَحات سَبَق تَنزيلها: {len(completed)}")

    # 4. تَحديد النِّطاق
    report = {
        "total_pages_detected": book_meta.get("max_page"),
        "downloaded_pages": 0,
        "pages_with_diacritics": 0,
        "pages_without_diacritics": 0,
        "failed_pages": 0,
        "skipped_pages": 0,
        "errors": [],
        "warnings": [],
    }

    max_page = book_meta.get("max_page")
    if not max_page:
        report["warnings"].append("لَم يُكشَف عَدَد الصَّفَحات — اعتمَدنا max_empty_streak")
        max_page = 99999
    end_page = args.end if args.end else max_page
    print(f"  ► نِطاق التَّنزيل: {args.start} → {end_page}")
    print(f"  ► فاصِل: {args.delay}ث · max_empty_streak: {args.max_empty_streak}")
    print()

    # 5. التَّنزيل
    empty_streak = 0
    for page_no in range(args.start, end_page + 1):
        if page_no in completed:
            report["skipped_pages"] += 1
            continue

        url = f"{base_url}/{page_no}"
        print(f"  • صَفحَة {page_no}: {url}", flush=True)
        resp = fetch_with_retries(url, session)
        if resp is None:
            report["failed_pages"] += 1
            report["errors"].append({"page_no": page_no, "reason": "max retries exceeded"})
            empty_streak += 1
        elif resp.status_code == 404:
            print(f"    ↳ 404 — نِهايَة مُحتَمَلَة")
            empty_streak += 1
        elif resp.status_code != 200:
            report["failed_pages"] += 1
            report["errors"].append({"page_no": page_no, "reason": f"HTTP {resp.status_code}"})
            empty_streak += 1
        else:
            try:
                record = parse_page(resp.text, url, page_no, book_meta, book_id)
                if record["raw_text"] and len(record["raw_text"]) > 30:
                    append_record(output_jsonl, record)
                    report["downloaded_pages"] += 1
                    if record["has_diacritics"]:
                        report["pages_with_diacritics"] += 1
                    else:
                        report["pages_without_diacritics"] += 1
                    empty_streak = 0
                    diac = "✓" if record["has_diacritics"] else "—"
                    print(f"    ↳ ✓ {len(record['raw_text'])} حَرف · تَشكيل: {diac}")
                else:
                    print(f"    ↳ صَفحَة فارِغَة")
                    empty_streak += 1
            except Exception as e:
                report["failed_pages"] += 1
                report["errors"].append({"page_no": page_no, "reason": f"parse: {e}"})

        if empty_streak >= args.max_empty_streak:
            print(f"  ⏹ {empty_streak} صَفحَة فارِغَة مُتَوالِيَة — نِهايَة الكِتاب.")
            report["warnings"].append(
                f"تَوَقَّفنا في الصَّفحَة {page_no} بَعد {empty_streak} صَفَحات فارِغَة"
            )
            break

        time.sleep(args.delay)

    # 6. حِفظ metadata الكِتاب
    meta_path = raw_dir / "book_meta.json"
    meta_path.write_text(
        json.dumps({**book_meta, "book_id": book_id, "slug": slug,
                    "base_url": base_url}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    write_report(report, raw_dir, book_meta, book_id,
                 output_jsonl.name, index_html_path.name)
    print()
    diac_pct = (report["pages_with_diacritics"] / report["downloaded_pages"] * 100
                if report["downloaded_pages"] else 0)
    print(f"  ◆ النَّتيجَة: {report['downloaded_pages']} مُنَزَّلَة "
          f"({report['pages_with_diacritics']} بِتَشكيل = {diac_pct:.1f}%)، "
          f"{report['skipped_pages']} مُتَخَطّاة، {report['failed_pages']} فاشِلَة")
    print(f"  ◆ المَلَفّ: {output_jsonl}")


if __name__ == "__main__":
    main()
