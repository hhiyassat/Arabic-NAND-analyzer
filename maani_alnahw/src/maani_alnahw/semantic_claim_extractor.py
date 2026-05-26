"""semantic_claim_extractor.py — استخراج SemanticClaims مِن كُلّ صَفحَة.

نَهج open-ended:
  • لا قائِمَة ثابِتَة مِن «التَّراكيب المَطلوبَة»
  • نَفحَص كُلّ فَقرَة عَن أَنماط لُغَويَّة 20 نَوعًا
  • نُولِّد SemanticClaim لِكُلّ مُطابَقَة
  • صَفحَة واحِدَة قَد تُنتِج 0 إلى 50 claim — لا حَدّ أَعلى

الأَنماط (20):
  syntactic_semantic_rule, semantic_distinction, particle_meaning,
  preposition_meaning, preposition_distinction, syntactic_effect,
  semantic_effect, distinction, modality, discourse_meaning,
  reference_meaning, number_counted_meaning, tadmeen, quranic_usage,
  opinion, author_preference, exception, warning, ambiguity,
  probabilistic_rule, testable_rule
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Optional

import sys
_HERE = Path(__file__).resolve().parent
_KB = _HERE.parent
sys.path.insert(0, str(_KB))
from grammar_kb.models import SemanticClaim


_LEX_DIR = _HERE.parent.parent / "lexicons"


def _load_surahs() -> dict:
    with open(_LEX_DIR / "quran_surah_names.json", encoding="utf-8") as f:
        data = json.load(f)
    names = set()
    for s in data.get("surahs", []):
        names.add(s["name"])
        for v in s.get("variants", []):
            names.add(v)
    return names


def _load_scholars() -> set:
    with open(_LEX_DIR / "scholars.json", encoding="utf-8") as f:
        data = json.load(f)
    out = set()
    for s in data.get("scholars", []):
        out.add(s["canonical"])
        for v in s.get("variants", []):
            out.add(v)
    return out


SURAH_NAMES = _load_surahs()
SCHOLAR_NAMES = _load_scholars()


# ─── أَنماط القَبض (rule-based) ──────────────────────────────────────────

PATTERNS = [
    # (claim_type, pattern, certainty_level, base_confidence)
    # نَلتَزِم بِكَلِمات مُفتاحيَّة بِلا تَشكيل وَ نَسمَح بِكَلِمات بَين الإِشارَتَين
    ("semantic_distinction", r"الفرق\s+(?:في\s+المعنى\s+)?بين", "asserted", 0.85),
    ("particle_meaning", r"(?:^|\W)(?:و)?معنى\s+\S+\s+(?:هو|هي|الأصل|الرئيس|الإلصاق|التعليل|الاستعلاء|الظرفية|الإسناد)", "asserted", 0.83),
    ("preposition_meaning", r"(?:^|\W)(?:و)?معنى\s+(?:الباء|اللام|من|إلى|عن|على|في|الكاف)", "asserted", 0.88),
    ("preposition_meaning", r"(?:الباء|اللام|من|إلى|عن|على|في)\s+(?:تفيد|يفيد|تدل|للإلصاق|للسببية|للمصاحبة|للاستعانة|للتعليل|للملك|للاختصاص|للعاقبة|لانتهاء|لابتداء)", "asserted", 0.87),
    ("preposition_meaning", r"(?:أصل|الأصل\s+في)\s+(?:الباء|اللام|من|إلى|عن|على|في)", "asserted", 0.87),
    ("syntactic_effect", r"(?:^|\W)الأصل\s+(?:في|أن|أنّ)", "asserted", 0.82),
    ("syntactic_effect", r"(?:ينصب|تنصب|ينصبهما|فتنصبهما|ناصب|ناصبة)\b", "asserted", 0.86),
    ("syntactic_effect", r"(?:يجزم|تجزم|جازم|جازمة|مجزوم)\b", "asserted", 0.88),
    ("syntactic_effect", r"(?:يرفع|ترفع|رافع|مرفوع)\b", "asserted", 0.86),
    ("syntactic_effect", r"(?:يجر|تجر|جار|مجرور)\s+(?:الاسم|بعده|ما\s+بعده)", "asserted", 0.85),
    ("syntactic_effect", r"(?:تدخل|يدخل|دخلت|دخل)\s+(?:[ء-ي]+\s+){0,5}على\s+(?:المبتدأ|الخبر|الجملة|المضارع|الاسم|الفعل)", "asserted", 0.86),
    ("semantic_effect", r"(?:تفيد|يفيد)\s+(?:الاستقبال|الاستمرار|التوكيد|التعليل|الإلصاق|اليقين|الرجحان|الشك|الظرفية|التحويل)", "asserted", 0.85),
    ("semantic_effect", r"(?:يدل|تدل|دلت|دل)\s+على\s+(?:الثبوت|الحدث|التجدد|اليقين|الاستمرار|الزمن|الإسناد|الحال|المعنى)", "asserted", 0.84),
    ("modality", r"(?:يقين|رجحان|شك|توقع|استمرار|تعجب|استخبار)", "asserted", 0.78),
    ("opinion", r"(?:^|\W)(?:قيل|وقيل|ذهب|ذهبوا|قالوا|ويرى|يرى)\b", "reported", 0.78),
    ("author_preference", r"(?:والصواب|والحق|والذي\s+أراه|الذي\s+أراه|والأولى|والأظهر|والراجح|والمختار|والصحيح)", "preferred", 0.9),
    ("exception", r"(?:بخلاف|إلا\s+(?:أن|إذا)|باستثناء|غير\s+أن)", "asserted", 0.82),
    ("warning", r"(?:لا\s+يصح|لا\s+يجوز|ليس\s+معنى|وفيه\s+نظر|وهذا\s+مردود|لا\s+يفهم|لا\s+يُفهم)", "asserted", 0.85),
    ("probabilistic_rule", r"(?:غالبًا|في\s+الغالب|كثيرًا\s+ما|قد\s+(?:يكون|تكون|يجيء|تجيء|يأتي|تأتي|يجوز))", "probable", 0.78),
    ("conditional_rule", r"(?:^|\W)(?:إذا|متى|إن)\s+\S+\s+(?:كانت?|جاءت?|دخل|سبق|تلا|ذكرت|ذكر|نقص|تم)", "asserted", 0.78),
    ("conditional_rule", r"(?:^|\W)(?:إذا|متى|إن)\s+(?:ذكرت|ذكر|دخل|دخلت|جاء|جاءت|كان|كانت)", "asserted", 0.78),
    ("contrast_rule", r"(?:^|\W)أما\s+\S+(?:\s+\S+){0,8}\s+(?:فإن|فهو|فهي|فلا|ف[ء-ي]+)", "asserted", 0.78),
    ("permission", r"يجوز\s+(?:أن|الجزم|الرفع|النصب|الحذف|التقديم)", "asserted", 0.83),
    ("denial_of_misreading", r"(?:ليس\s+معنى|لا\s+يفهم|لا\s+يُفهم)", "asserted", 0.84),
    ("tadmeen", r"(?:تضمين|ضُمّن|ضُمِّن|أُشرب\s+معنى|تضمّن|إشراب)", "asserted", 0.85),
    ("number_counted_meaning", r"(?:^|\W)(?:العدد|المعدود|تمييز\s+العدد|أحد\s+عشر|ثلاثة\s+(?:رجال|كتب|آلاف)|ثلاث\s+(?:نساء|آيات)|عشرون|مئة|ألف)\b", "asserted", 0.78),
    ("discourse_meaning", r"(?:كاف\s+(?:الخطاب|التنبيه)|توكيد\s+الخطاب|الغفلة|المخاطَب|المخاطب|التنبيه)", "asserted", 0.82),
    ("reference_meaning", r"(?:يرجع\s+(?:إلى|الضمير\s+إلى)|مرجع\s+الضمير|عائد\s+على|يعود\s+على|راجع\s+إلى)", "asserted", 0.83),
    ("quranic_usage", r"كقوله\s+تعالى", "asserted", 0.85),
    ("quranic_usage", r"قال\s+(?:تعالى|سبحانه)", "asserted", 0.85),
    ("ambiguity", r"(?:يحتمل|يجوز\s+فيه)\s+(?:وجهين|أكثر|عدة|معنيين)", "asserted", 0.82),
    # تَفصيل / تَقسيم
    ("syntactic_semantic_rule", r"(?:تنقسم|ينقسم|تقسم|قسم)\s+(?:هذه|إلى|على)", "asserted", 0.82),
]


# ─── أَدوات مُساعِدَة ────────────────────────────────────────────────────

DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _split_paragraphs(text: str) -> list[str]:
    """يَقسِم النَّصّ إلى فَقرات بِأَسطُر فارِغَة أَو نِقاط طَويلَة."""
    paras = re.split(r'\n\s*\n+|\n(?=[؀-ۿ])', text)
    return [p.strip() for p in paras if p.strip()]


def _split_sentences(paragraph: str) -> list[tuple[int, str]]:
    """يَقسِم فَقرَة إلى جُمَل، يَحفَظ مَوقِع البِدايَة."""
    # نَقطَع عَلى نُقطَة / استِفهام / فاصِلَة طَويلَة
    sentences = []
    parts = re.split(r'(?<=[\.؟])\s+|(?<=[\.؟])\n+', paragraph)
    pos = 0
    for p in parts:
        p = p.strip()
        if not p or len(p) < 10:
            pos += len(p) + 1
            continue
        sentences.append((pos, p))
        pos += len(p) + 1
    return sentences


def _extract_quran_refs(text: str) -> list[dict]:
    """يَلتَقِط مَراجِع الآيات: [يوسف: 36]، [البقرة: 282]."""
    refs = []
    for m in re.finditer(r'\[([^\]]+?)\s*:\s*([٠-٩\d]+)\]', text):
        name_raw = m.group(1).strip()
        # تَحويل الأَرقام العَرَبيَّة
        ar_to_en = {ord(c): chr(ord('0') + i) for i, c in enumerate('٠١٢٣٤٥٦٧٨٩')}
        num_str = m.group(2).translate(ar_to_en)
        # تَنظيف اسم السورة
        name_clean = name_raw
        for prefix in ("سورة ", "الـ"):
            if name_clean.startswith(prefix):
                name_clean = name_clean[len(prefix):]
        # نُجَرِّب المُطابَقَة
        if name_clean in SURAH_NAMES or name_raw in SURAH_NAMES:
            refs.append({"surah": name_clean, "ayah_str": num_str, "raw": m.group(0)})
    return refs


def _extract_scholars(text: str) -> list[str]:
    found = []
    for s in SCHOLAR_NAMES:
        if len(s) < 4:
            continue
        if s in text:
            found.append(s)
    return list(dict.fromkeys(found))  # dedupe


def _extract_examples_in_parens(text: str) -> list[str]:
    """يَلتَقِط نُصوصًا بَين قَوسَين عَرَبيَّين."""
    out = []
    for m in re.finditer(r'[\(﴿]([^\)﴾]{3,200})[\)﴾]', text):
        out.append(m.group(1).strip())
    return out


def _grammatical_focus(claim_text: str) -> list[str]:
    """يَلتَقِط مُصطَلَحات نَحويَّة في الـ claim."""
    terms = ["مبتدأ", "خبر", "فاعل", "مفعول", "حال", "تمييز", "ظرف", "نعت",
             "صفة", "بدل", "عطف", "إعراب", "نصب", "رفع", "جر", "جزم",
             "تنوين", "إضافة", "تعريف", "تنكير", "ضمير", "اسم إشارة",
             "اسم موصول", "حرف جر", "حرف ناصب", "حرف جازم", "حرف عطف"]
    found = []
    for t in terms:
        if t in claim_text:
            found.append(t)
    return found


def _semantic_focus(claim_text: str) -> list[str]:
    terms = ["يقين", "رجحان", "شك", "ظن", "علم", "معرفة", "إدراك",
             "ثبوت", "تجدد", "استمرار", "تَوقُّع", "توقع", "نفي", "إثبات",
             "أمر", "نهي", "تَعليل", "سَبَب", "ظَرفيَّة", "إلصاق",
             "مُصاحَبَة", "استِعلاء", "ابتداء", "انتهاء", "تَضمين",
             "مَجاز", "تَوكيد", "خِطاب", "تنبيه", "غَفلَة", "حال"]
    found = []
    for t in terms:
        if _strip_diac(t) in _strip_diac(claim_text):
            found.append(t)
    return found


def _detect_triggers(sentence: str) -> dict:
    """يَلتَقِط lemmas/particles مُحَدَّدَة."""
    triggers = {}
    # أَفعال
    verbs = ["ظن", "حسب", "خال", "زعم", "علم", "عرف", "رأى", "وجد", "درى",
             "جعل", "اتخذ", "صير", "ترك", "ألفى", "أرأيت", "أرأيتك", "أرأيتكم"]
    found_verbs = [v for v in verbs if v in sentence]
    if found_verbs:
        triggers["lemmas"] = found_verbs
    # حُروف
    particles = ["لم", "لمّا", "لما", "لا", "لن", "ما", "إن", "إذا",
                 "إلى", "الباء", "اللام", "من", "عن", "على", "في", "الكاف"]
    found_particles = [p for p in particles if re.search(rf"(^|\W){re.escape(p)}(\W|$)", sentence)]
    if found_particles:
        triggers["particles"] = found_particles
    return triggers


def _detect_author_preference_text(sentence: str) -> Optional[str]:
    for marker in ["والصواب", "والحق", "والذي أراه", "الذي أراه",
                    "والأولى", "والأظهر", "والراجح", "والمختار", "والصحيح"]:
        if marker in sentence:
            return marker
    return None


# ─── المُستَخرِج الرَّئيس ────────────────────────────────────────────────

class SemanticClaimExtractor:

    def __init__(self):
        # نُجَمِّع الأَنماط مُسبَقًا
        self._compiled = [
            (ct, re.compile(p), cl, conf) for ct, p, cl, conf in PATTERNS
        ]

    def extract_from_page(
        self, page: dict, topic: Optional[dict] = None,
    ) -> list[SemanticClaim]:
        """يُرجِع كُلّ claims مِن صَفحَة واحِدَة."""
        text = page.get("cleaned_text") or page.get("raw_text", "")
        if not text:
            return []
        part = page["part"]
        page_num = page["page"]
        topic_id = topic.get("topic_id") if topic else None
        topic_title = topic.get("title") if topic else None

        claims: list[SemanticClaim] = []
        paragraphs = _split_paragraphs(text)
        for p_idx, para in enumerate(paragraphs):
            sentences = _split_sentences(para)
            for s_idx, (offset, sentence) in enumerate(sentences):
                # نَفحَص كُلّ نَمَط
                matched_types = set()
                for claim_type, pattern, certainty, base_conf in self._compiled:
                    if claim_type in matched_types:
                        continue  # نَوع واحِد لِكُلّ جُملَة
                    if pattern.search(sentence):
                        matched_types.add(claim_type)
                        claim = self._build_claim(
                            sentence=sentence,
                            part=part, page=page_num,
                            topic_id=topic_id, topic_title=topic_title,
                            paragraph_id=f"P{part}p{page_num}_para{p_idx}_sent{s_idx}",
                            claim_type=claim_type,
                            certainty_level=certainty,
                            base_confidence=base_conf,
                        )
                        claims.append(claim)
        return claims

    def _build_claim(
        self, sentence: str, part: int, page: int,
        topic_id: Optional[str], topic_title: Optional[str],
        paragraph_id: str, claim_type: str,
        certainty_level: str, base_confidence: float,
    ) -> SemanticClaim:
        cleaned = sentence.strip()
        raw_excerpt = cleaned[:300]
        # تَنظيف الـ excerpt: إِزالة فَواصِل سَطر
        normalized = re.sub(r'\s+', ' ', cleaned)[:400]
        # ضَبط الثِّقَة بِناءً على الإِشارات
        confidence = base_confidence
        author_pos = _detect_author_preference_text(sentence)
        if author_pos:
            confidence = min(0.95, confidence + 0.05)
        # سَطر قَصير جِدًّا → ثِقَة أَقَلّ
        if len(cleaned) < 30:
            confidence -= 0.15
        # لا يَحوي مُصطَلَحات نَحويَّة وَاضِحَة → ثِقَة أَقَلّ
        gram_focus = _grammatical_focus(sentence)
        sem_focus = _semantic_focus(sentence)
        if not gram_focus and not sem_focus and claim_type not in ("opinion", "author_preference"):
            confidence -= 0.1
        confidence = max(0.05, min(0.99, confidence))
        needs_review = confidence < 0.6

        quran_refs = _extract_quran_refs(sentence)
        examples = _extract_examples_in_parens(sentence)
        scholars = _extract_scholars(sentence)
        triggers = _detect_triggers(sentence)

        # claim_id
        claim_id = f"CLAIM_P{part}_{page:03d}_{paragraph_id}_{claim_type}"

        return SemanticClaim(
            claim_id=claim_id,
            part=part,
            page=page,
            topic_id=topic_id,
            topic_title=topic_title,
            paragraph_id=paragraph_id,
            raw_excerpt=raw_excerpt,
            cleaned_excerpt=normalized,
            normalized_claim=normalized,
            claim_type=claim_type,
            grammatical_focus=gram_focus,
            semantic_focus=sem_focus,
            triggers=triggers,
            examples_mentioned=examples,
            quran_refs=quran_refs,
            scholars_mentioned=scholars,
            author_position=author_pos,
            certainty_level=certainty_level,
            confidence=confidence,
            needs_manual_review=needs_review,
        )


def extract_claims_from_pages(
    pages: list[dict], topics: list[dict],
) -> list[SemanticClaim]:
    """يَستَخرِج كُلّ claims مِن كُلّ الصَّفَحات.

    لِكُلّ صَفحَة، نَجِد الـ topic الَّذي تَنتَمي إِليه (لِلتَّسميَة فَقَط).
    """
    extractor = SemanticClaimExtractor()
    # نَبني خَريطَة page → topic
    page_to_topic: dict[tuple[int, int], dict] = {}
    for t in topics:
        part = t["part"]
        start = t["start_page"]
        end = t.get("end_page") or start
        for pg in range(start, end + 1):
            # أَوَّل topic يَحوي الصَّفحَة يَكون له الأَولويَّة (الـ specific قَبل العامّ)
            key = (part, pg)
            if key not in page_to_topic:
                page_to_topic[key] = t
    all_claims = []
    for page in pages:
        topic = page_to_topic.get((page["part"], page["page"]))
        claims = extractor.extract_from_page(page, topic=topic)
        all_claims.extend(claims)
    return all_claims


def write_claims_jsonl(claims: list[SemanticClaim], output_path) -> int:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for c in claims:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count
