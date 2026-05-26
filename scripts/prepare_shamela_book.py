"""prepare_shamela_book.py — تَنظيف وَ فَهرَسَة أَيّ كِتاب شاملَة.

يَأخُذ:
  data/raw/{slug}/{slug}_raw_pages.jsonl
  data/raw/{slug}/book_meta.json

يُنتِج:
  data/processed/{slug}/{slug}_clean_sections.jsonl
  data/processed/{slug}/{slug}_ayah_index.jsonl  (لِكُتُب التَّفسير)

استِخدام:
  python3 scripts/prepare_shamela_book.py --slug kashaf
  python3 scripts/prepare_shamela_book.py --slug ibn_kathir
  python3 scripts/prepare_shamela_book.py --input data/raw/X/X_raw_pages.jsonl
  python3 scripts/prepare_shamela_book.py --slug kashaf --no-quran-index  # لا فَهرَسَة آيات
  python3 scripts/prepare_shamela_book.py --slug kashaf --strip-diacritics  # نُسخَة بِلا تَشكيل

الخَصائص:
  • generic — أَيّ كِتاب
  • يَحتَفِظ بِالتَّشكيل افتراضيًّا
  • اختياريًّا يُنشِئ نُسخَة مَجرَّدَة مِن التَّشكيل في `cleaned_text_plain`
  • يَكشِف السورَة الحاليَّة في كُتُب التَّفسير
  • يَستَخرِج اقتِباسات قُرآنيَّة بِنِطاقات (1-2) وَ يَدعَم 114 سورَة
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ─── ثَوابِت ────────────────────────────────────────────────────────────

ARABIC_DIACRITICS = "ًٌٍَُِّْـٰٓ"

WHITESPACE_RE = re.compile(r"[ \t]+")
MULTINEWLINE_RE = re.compile(r"\n{3,}")

INTERFACE_NOISE = [
    r"الصفحة\s+التالية", r"الصفحة\s+السابقة",
    r"الفهرس", r"رجوع\s+للأعلى",
    r"شاركها\s+على", r"تابعنا\s+على",
    r"تحميل\s+الكتاب", r"اشترك\s+معنا",
    r"©\s*\d+\s*shamela",
    r"الكلمات\s+الافتتاحية", r"بحث\s+في\s+الكتاب",
    r"المكتبة\s+الشاملة", r"مكتبة\s+الشاملة",
    r"حقوق\s+النشر",
]
INTERFACE_RE = re.compile("|".join(INTERFACE_NOISE))


def strip_diacritics(s: str) -> str:
    return "".join(c for c in s if c not in ARABIC_DIACRITICS)


def clean_text(raw: str) -> str:
    """تَنظيف يَحتَفِظ بِالتَّشكيل + يَنزَع شَوائب الواجِهَة."""
    if not raw:
        return ""
    text = INTERFACE_RE.sub("", raw)
    text = WHITESPACE_RE.sub(" ", text)
    text = MULTINEWLINE_RE.sub("\n\n", text)
    lines = [l.rstrip() for l in text.split("\n")]
    lines = [l for l in lines if l.strip()]
    return "\n".join(lines)


# ─── أَسماء السُّوَر (114) ────────────────────────────────────────────

SURAH_NAMES = {
    1: "الفاتحة", 2: "البقرة", 3: "آل عمران", 4: "النساء", 5: "المائدة",
    6: "الأنعام", 7: "الأعراف", 8: "الأنفال", 9: "التوبة", 10: "يونس",
    11: "هود", 12: "يوسف", 13: "الرعد", 14: "إبراهيم", 15: "الحجر",
    16: "النحل", 17: "الإسراء", 18: "الكهف", 19: "مريم", 20: "طه",
    21: "الأنبياء", 22: "الحج", 23: "المؤمنون", 24: "النور", 25: "الفرقان",
    26: "الشعراء", 27: "النمل", 28: "القصص", 29: "العنكبوت", 30: "الروم",
    31: "لقمان", 32: "السجدة", 33: "الأحزاب", 34: "سبأ", 35: "فاطر",
    36: "يس", 37: "الصافات", 38: "ص", 39: "الزمر", 40: "غافر",
    41: "فصلت", 42: "الشورى", 43: "الزخرف", 44: "الدخان", 45: "الجاثية",
    46: "الأحقاف", 47: "محمد", 48: "الفتح", 49: "الحجرات", 50: "ق",
    51: "الذاريات", 52: "الطور", 53: "النجم", 54: "القمر", 55: "الرحمن",
    56: "الواقعة", 57: "الحديد", 58: "المجادلة", 59: "الحشر", 60: "الممتحنة",
    61: "الصف", 62: "الجمعة", 63: "المنافقون", 64: "التغابن", 65: "الطلاق",
    66: "التحريم", 67: "الملك", 68: "القلم", 69: "الحاقة", 70: "المعارج",
    71: "نوح", 72: "الجن", 73: "المزمل", 74: "المدثر", 75: "القيامة",
    76: "الإنسان", 77: "المرسلات", 78: "النبأ", 79: "النازعات", 80: "عبس",
    81: "التكوير", 82: "الانفطار", 83: "المطففين", 84: "الانشقاق", 85: "البروج",
    86: "الطارق", 87: "الأعلى", 88: "الغاشية", 89: "الفجر", 90: "البلد",
    91: "الشمس", 92: "الليل", 93: "الضحى", 94: "الشرح", 95: "التين",
    96: "العلق", 97: "القدر", 98: "البينة", 99: "الزلزلة", 100: "العاديات",
    101: "القارعة", 102: "التكاثر", 103: "العصر", 104: "الهمزة", 105: "الفيل",
    106: "قريش", 107: "الماعون", 108: "الكوثر", 109: "الكافرون", 110: "النصر",
    111: "المسد", 112: "الإخلاص", 113: "الفلق", 114: "الناس",
}
SURAH_NAME_TO_NUM = {v: k for k, v in SURAH_NAMES.items()}
SURAH_VARIANTS = {
    "اللهب": 111, "تبت": 111, "الانسان": 76, "الدهر": 76,
    "حم السجدة": 41, "بني إسرائيل": 17, "الإسراء": 17,
}
SURAH_NAME_TO_NUM.update(SURAH_VARIANTS)


# ─── كَشف السورَة ─────────────────────────────────────────────────────

SURAH_HEADING_RE = re.compile(r"(?:تَفسير\s+)?سور[ةت]\s+([ء-ي\s]{2,40})")


def detect_current_surah(text: str, prev_surah: int | None) -> int | None:
    head = strip_diacritics(text[:600])
    for m in SURAH_HEADING_RE.finditer(head):
        candidate = m.group(1).strip()
        for name, num in SURAH_NAME_TO_NUM.items():
            name_plain = strip_diacritics(name)
            if name_plain in candidate or candidate in name_plain:
                if 2 <= len(candidate) <= 30:
                    return num
    return prev_surah


# ─── استخراج الآيات ─────────────────────────────────────────────────

AYAH_BRACE_RE = re.compile(r"[\{﴿]([^\}﴾]{5,400})[\}﴾]")
AYAH_PAREN_QURAN_RE = re.compile(
    r"(?:قَوله\s+(?:تَعالى|سُبحانه)|كَقَوله|في\s+قَوله|قال\s+(?:تعالى|سبحانه))\s*[:\.]?\s*[\(﴿]([^\)﴾]{5,400})[\)﴾]"
)
AYAH_REF_RE = re.compile(r"\[([^\]]+?)\s*:\s*([٠-٩\d\-،,\s]+)\]")


def _ar_to_en_digits(s: str) -> str:
    return s.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))


def _parse_ayah_number(num_str: str) -> tuple[int | None, int | None]:
    num_str = _ar_to_en_digits(num_str).strip()
    nums = [int(n) for n in re.findall(r"\d+", num_str)]
    if not nums:
        return None, None
    if len(nums) == 1:
        return nums[0], nums[0]
    return nums[0], nums[-1]


def extract_ayah_quotes(text: str, page_no: int, current_surah: int | None) -> list[dict]:
    quotes = []
    seen_ayah_texts = set()

    def _parse_ref(after_text: str):
        m = AYAH_REF_RE.search(after_text)
        if not m:
            return None, None, None
        name_raw = m.group(1).strip()
        ayah_start, ayah_end = _parse_ayah_number(m.group(2))
        surah_ref = None
        name_raw_plain = strip_diacritics(name_raw)
        for name, num in SURAH_NAME_TO_NUM.items():
            name_plain = strip_diacritics(name)
            if name_plain in name_raw_plain or name_raw_plain in name_plain:
                surah_ref = num
                break
        return surah_ref, ayah_start, ayah_end

    for m in AYAH_BRACE_RE.finditer(text):
        ayah_text = m.group(1).strip()
        ayah_plain = strip_diacritics(ayah_text)
        if len(ayah_text) < 8 or ayah_plain in seen_ayah_texts:
            continue
        seen_ayah_texts.add(ayah_plain)
        after = text[m.end():m.end() + 80]
        surah_ref, ayah_start, ayah_end = _parse_ref(after)
        quotes.append({
            "page_no": page_no,
            "position": m.start(),
            "quote_type": "ornamental_brackets",
            "ayah_text": ayah_text,
            "ayah_text_plain": ayah_plain,
            "surah_num": surah_ref or current_surah,
            "surah_name": SURAH_NAMES.get(surah_ref or current_surah or 0),
            "ayah_no": ayah_start,
            "ayah_range_end": ayah_end if ayah_end != ayah_start else None,
            "context_before": text[max(0, m.start() - 80):m.start()].strip()[-80:],
        })

    for m in AYAH_PAREN_QURAN_RE.finditer(text):
        ayah_text = m.group(1).strip()
        ayah_plain = strip_diacritics(ayah_text)
        if len(ayah_text) < 8 or ayah_plain in seen_ayah_texts:
            continue
        seen_ayah_texts.add(ayah_plain)
        after = text[m.end():m.end() + 80]
        surah_ref, ayah_start, ayah_end = _parse_ref(after)
        quotes.append({
            "page_no": page_no,
            "position": m.start(),
            "quote_type": "qawluh_taala",
            "ayah_text": ayah_text,
            "ayah_text_plain": ayah_plain,
            "surah_num": surah_ref or current_surah,
            "surah_name": SURAH_NAMES.get(surah_ref or current_surah or 0),
            "ayah_no": ayah_start,
            "ayah_range_end": ayah_end if ayah_end != ayah_start else None,
            "context_before": text[max(0, m.start() - 80):m.start()].strip()[-80:],
        })

    return quotes


# ─── المُحَرِّك ────────────────────────────────────────────────────────

def read_jsonl(path: Path) -> list[dict]:
    out = []
    if not path.exists():
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def write_jsonl(records, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def _resolve_paths(args) -> tuple[Path, Path, Path, str]:
    """يُحَدِّد input/clean/index/slug."""
    if args.input:
        inp = Path(args.input)
        slug = args.slug or inp.parent.name
    elif args.slug:
        slug = args.slug
        inp = PROJECT_ROOT / "data" / "raw" / slug / f"{slug}_raw_pages.jsonl"
    else:
        print("خَطَأ: مَرِّر --slug أَو --input", file=sys.stderr)
        sys.exit(2)
    out_clean = (Path(args.clean) if args.clean else
                 PROJECT_ROOT / "data" / "processed" / slug / f"{slug}_clean_sections.jsonl")
    out_index = (Path(args.index) if args.index else
                 PROJECT_ROOT / "data" / "processed" / slug / f"{slug}_ayah_index.jsonl")
    return inp, out_clean, out_index, slug


def main():
    ap = argparse.ArgumentParser(description="تَنظيف وَ فَهرَسَة كِتاب شاملَة")
    ap.add_argument("--slug", help="اسم المُجَلَّد تَحت data/raw/")
    ap.add_argument("--input", help="مَسار jsonl صَريح (يَتَجاوَز --slug)")
    ap.add_argument("--clean", help="مَسار المُخرَج النَّظيف")
    ap.add_argument("--index", help="مَسار فَهرَس الآيات")
    ap.add_argument("--no-quran-index", action="store_true",
                    help="لا تَستَخرِج فَهرَس الآيات (لِكُتُب غَير التَّفسير)")
    ap.add_argument("--strip-diacritics", action="store_true",
                    help="أَنشِئ نُسخَة بِلا تَشكيل (cleaned_text_plain)")
    args = ap.parse_args()

    inp, out_clean, out_index, slug = _resolve_paths(args)
    if not inp.exists():
        print(f"خَطَأ: {inp} غَير مَوجود. شَغِّل download_shamela_book.py أَوَّلًا.",
              file=sys.stderr)
        sys.exit(2)

    print(f"  ► slug: {slug}")
    print(f"  ► قِراءَة: {inp}")
    pages = read_jsonl(inp)
    print(f"    {len(pages)} صَفحَة")

    # metadata
    meta_path = inp.parent / "book_meta.json"
    book_meta = {}
    if meta_path.exists():
        try:
            book_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            print(f"    اسم: {book_meta.get('name')}، مُؤَلِّف: {book_meta.get('author')}")
        except json.JSONDecodeError:
            pass

    clean_records = []
    ayah_index = []
    current_surah = None
    pages_with_diac = 0

    for page in pages:
        raw = page.get("raw_text", "")
        page_no = page.get("page_no")
        cleaned = clean_text(raw)
        has_diac = any(c in cleaned for c in ARABIC_DIACRITICS)
        if has_diac:
            pages_with_diac += 1

        current_surah = detect_current_surah(cleaned, current_surah)

        record = {
            **page,
            "cleaned_text": cleaned,
            "char_count": len(cleaned),
            "has_diacritics": has_diac,
        }
        if args.strip_diacritics:
            record["cleaned_text_plain"] = strip_diacritics(cleaned)
        if not args.no_quran_index:
            record["detected_surah_num"] = current_surah
            record["detected_surah_name"] = SURAH_NAMES.get(current_surah) if current_surah else None
        clean_records.append(record)

        if not args.no_quran_index:
            quotes = extract_ayah_quotes(cleaned, page_no, current_surah)
            ayah_index.extend(quotes)

    n1 = write_jsonl(clean_records, out_clean)
    print(f"  ✓ {n1} صَفحَة نَظيفَة → {out_clean}")
    print(f"    صَفَحات بِتَشكيل: {pages_with_diac}/{n1} "
          f"({pages_with_diac/n1*100 if n1 else 0:.1f}%)")

    if not args.no_quran_index:
        n2 = write_jsonl(ayah_index, out_index)
        print(f"  ✓ {n2} اقتِباس قُرآنيّ → {out_index}")
        by_surah = {}
        for q in ayah_index:
            s = q.get("surah_num")
            if s:
                by_surah[s] = by_surah.get(s, 0) + 1
        if by_surah:
            print(f"  ► top 10 سُوَر:")
            for s, n in sorted(by_surah.items(), key=lambda x: -x[1])[:10]:
                print(f"    سورة {SURAH_NAMES.get(s, '?')} ({s}): {n}")


if __name__ == "__main__":
    main()
