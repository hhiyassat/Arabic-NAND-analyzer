"""analyze_maani.py — استخراج طَبَقَة «مَعاني النَّحو» مِن آيَة.

يَأخُذ آيَة (سُورَة:آيَة أَو نَصّ)، يَستَخرِج كُلّ المُطابَقات مَع
قاعِدَة مَعرِفَة «مَعاني النَّحو»، وَ يَعرِضها بِتَفاصيل أَعمَق مِن
analyze_verse --maani:

  • التَّراكيب المَكشوفَة (constructions)
  • Modalities + warnings
  • المَصادِر (الجُزء + الصَّفحَة)
  • أَمثلَة المُؤَلِّف
  • meaning_cards مُرتَبِطَة
  • semantic_claims مُرتَبِطَة (لِلتَّعَمُّق)

استِخدام:
  python3 analyze_maani.py 2:214
  python3 analyze_maani.py "حسبتم أن تدخلوا الجنة"
  python3 analyze_maani.py 2:214 --json
  python3 analyze_maani.py 2:214 --deep  # يَعرِض meaning_cards كامِلَة
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import maani_kb_loader
from analyze_verse import _resolve_input, analyze_verse


CONTRACT_NAME = "MaaniAnalyzer:v1"


def _strip_diac(s: str) -> str:
    diacritics = "ًٌٍَُِّْـٰٓ"
    return "".join(c for c in s if c not in diacritics)


def _normalize(s: str) -> str:
    s = _strip_diac(s)
    s = s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return s


# ─── أَوصاف عَرَبيَّة لِـ modalities وَ relations ──────────────────────────

MODALITY_AR = {
    "probable_belief": "رُجحان واعتِقاد (لا يَقين قَطعيّ)",
    "claim_or_assumption": "ادِّعاء أَو افتِراض",
    "knowledge": "يَقين وَ عِلم",
    "belief_or_vision_depending_context": "اعتِقاد أَو رُؤيَة بَصَريَّة بِحَسَب السِّياق",
    "finding_or_certain_judgment": "اكتِشاف بَعد بَحث / حُكم يَقينيّ",
    "directive": "أَمر",
    "prohibition": "نَهي",
    "causative_transformation": "تَحويل سَبَبيّ",
    "request_information": "طَلَب إِخبار",
    "sensory_perception": "إِدراك حِسِّيّ",
    "belief_or_certainty": "اعتِقاد قَلبيّ",
    "dream_vision": "رُؤيا مَنام",
    "encounter": "مُصادَفَة",
    "knowledge_after_question": "عِلم بَعدَ سُؤال أَو جَهل",
}

RELATION_AR = {
    "judgment_about_object_1": "نِسبَة حُكم أَو صِفَة إلى المَفعول الأَوَّل",
    "transformation": "تَحويل الذَّات إلى حالَة جَديدَة",
    "predication": "إِسناد صِفَة لِذات",
    "predication_under_modal_operator": "إِسناد دَلاليّ تَحتَ مُعامِل جِهيّ (ظَنّ/علم)",
    "conditional_implicature": "تَرَتُّب جَزائيّ ضِمنيّ (أُسلوب شَرطيّ)",
}


def _is_verb_form(word: str, lemma: str) -> bool:
    """Heuristic: هَل الكَلِمَة في النَّصّ صورَة فِعليَّة لِلـ lemma؟

    مَعايير: تَبدَأ بِـ ي/ت/أ/ن (مُضارع) أَو تَنتَهي بِـ ت/تم/تما/ا/وا/ت (ماضي)،
    أَو الفِعل في صيغَة الأَمر، أَو تَحوي حُروف اللَّمَة كَجَذر.
    """
    bare = _normalize(word).strip()
    bare_lemma = _normalize(lemma).strip()
    if not bare or not bare_lemma:
        return False
    # نَقبَل تَطابُق مُباشَر
    if bare == bare_lemma:
        return True
    # حُروف الجَذر يَجِب أَن تَكون بِنَفس التَّرتيب وَ مَوجودَة
    # (يَحوي حُروف اللَّمَة كَجَذر داخِليّ)
    j = 0
    for c in bare:
        if j < len(bare_lemma) and c == bare_lemma[j]:
            j += 1
    if j < len(bare_lemma):
        return False  # لَيس كُلّ حُروف الجَذر مَوجودَة
    # رَفض «بحسب» — حَرف جَرّ بِـ + اسم
    if bare.startswith("ب") and bare_lemma in bare[1:]:
        # نَفحَص هَل بَقيَّة الكَلِمَة بَعد بـ هي الجَذر تَمامًا
        rest = bare[1:]
        if rest == bare_lemma or rest.startswith(bare_lemma):
            # هذا غالِبًا حَرف جَرّ + اسم → لَيس فِعلًا
            return False
    return True


def _claim_uses_verb(claim_text: str, lemma: str, verb_form: str) -> bool:
    """يَفحَص هَل الـ claim يَستَخدِم اللَّمَة كَفِعل لا كَجُزء مِن كَلِمَة أُخرى."""
    if not claim_text:
        return False
    text = _normalize(claim_text)
    bare_lemma = _normalize(lemma)
    # نَرفُض الذِّكر فَقَط في «بحسب / حسب أن / على حسب» — الاستِخدام كَمَعنى لِكَلِمَة، لا كَفِعل
    bad_phrases = [f"بحسب", f"بـحسب", f"على حسب", f"بحسبه", f"بحسبها"]
    if bare_lemma == "حسب":
        bad_count = sum(text.count(p) for p in bad_phrases)
        # نَعدّ ظُهور حسب كُلّيًّا
        total = text.count("حسب")
        if total > 0 and bad_count >= total:
            return False  # كُلّ الظُّهور في حَرف جَرّ / اسم
    # نَفحَص هَل يَظهَر الفِعل بِصورَة فِعليَّة (مَع لاحِقَة فِعل)
    verb_markers = [
        f"{bare_lemma}ت", f"{bare_lemma}تم", f"{bare_lemma}وا", f"{bare_lemma}نا",
        f"ي{bare_lemma}", f"ت{bare_lemma}", f"ن{bare_lemma}", f"أ{bare_lemma}",
        f"يَ{bare_lemma}", f"تَ{bare_lemma}",
    ]
    for vm in verb_markers:
        if _normalize(vm) in text:
            return True
    # تَطابُق مُباشَر
    if bare_lemma in text and len(text) < 200:
        return True
    return False


def extract_maani_for_verse(verse_text: str, source: str = "") -> dict:
    """يُحَلِّل آيَة وَ يَستَخرِج طَبَقَة Maani KB كامِلَة."""
    result = analyze_verse(verse_text, source=source)
    words = result.get("tokens", {}).get("words", [])
    maani_hits = result.get("maani_kb", {}).get("hits", [])

    kb = maani_kb_loader.get_kb()
    expanded_hits = []
    for hit in maani_hits:
        cid = hit.get("construction_id")
        construction = kb.by_construction(cid) if cid else None
        lemma = hit.get("matched_lemma") or ""
        token = hit.get("token") or ""

        # ─ تَأكيد: هَل الكَلِمَة فِعلًا صورَة فِعليَّة؟ ─
        is_verb = _is_verb_form(token, lemma)

        # ─ بِناء مَعنى دَلاليّ مُحَدَّد ─
        semantic_interpretation = _build_semantic_interpretation(
            construction, lemma, token
        )

        # ─ أَمثلَة مُؤَلِّف (مُختارَة يَدَويًّا في construction) ─
        author_examples = []
        if construction:
            # نَجلِب الأَمثلَة مِن rule_cards (يُحفَظ في source_refs)
            author_examples = _get_construction_examples(cid)

        # ─ فِلتَر صارِم لِـ related_meaning_cards ─
        related_cards = []
        if is_verb:
            related_cards = _filter_related_cards(lemma, token, cid, construction)

        expanded_hits.append({
            **hit,
            "is_verb_form": is_verb,
            "semantic_interpretation": semantic_interpretation,
            "construction_detail": construction,
            "author_examples": author_examples,
            "related_meaning_cards": related_cards,
        })

    return {
        "contract": CONTRACT_NAME,
        "source": source,
        "verse": verse_text,
        "n_words": len(words),
        "n_hits": len(maani_hits),
        "hits": expanded_hits,
        "kb_stats": kb.stats(),
    }


def _build_semantic_interpretation(construction: dict | None, lemma: str, token: str) -> dict:
    """يُولِّد تَفسيرًا دَلاليًّا مَفهومًا مِن الـ construction."""
    if not construction:
        return {}
    sem = construction.get("semantic_output") or {}
    transform = construction.get("deep_transform") or {}
    modality_key = (sem.get("modality_by_lemma") or {}).get(lemma)
    if not modality_key:
        modality_key = sem.get("primary_modality") or ""
    relation_key = sem.get("relation") or ""
    out = {
        "construction_title": construction.get("title", ""),
        "lemma": lemma,
        "token": token,
        "modality_ar": MODALITY_AR.get(modality_key, modality_key),
        "modality_key": modality_key,
        "relation_ar": RELATION_AR.get(relation_key, relation_key),
        "deep_transform_from": transform.get("from", ""),
        "deep_transform_to": transform.get("to", ""),
        "deep_predication": transform.get("deep_predication", ""),
    }
    # نَصّ تَفسيريّ مَوحَّد
    pieces = []
    if construction.get("title"):
        pieces.append(f"«{token}» مِن باب «{construction['title']}»")
    if out["modality_ar"]:
        pieces.append(f"بِجِهَة {out['modality_ar']}")
    if out["relation_ar"]:
        pieces.append(f"يُنشِئ عَلاقَة {out['relation_ar']}")
    if out["deep_transform_from"] and out["deep_transform_to"]:
        pieces.append(f"يُحَوِّل «{out['deep_transform_from']}» إلى «{out['deep_transform_to']}»")
    out["summary"] = " · ".join(pieces)
    return out


def _get_construction_examples(construction_id: str) -> list[dict]:
    """يَجلِب أَمثلَة construction مِن rule_cards.jsonl."""
    path = _HERE.parent / "maani_alnahw" / "data" / "processed" / "maani_alnahw" / "rule_cards.jsonl"
    if not path.exists():
        return []
    examples = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rule = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rid = rule.get("rule_id", "")
                base = rid.split("__")[0]
                if base != construction_id:
                    continue
                for ex in rule.get("examples", []):
                    if isinstance(ex, dict) and ex.get("text"):
                        examples.append(ex)
    except Exception:
        pass
    return examples[:6]


def _filter_related_cards(lemma: str, token: str, cid: str,
                           construction: dict | None) -> list[dict]:
    """يَختار meaning_cards مُرتَبِطَة بِالمَعنى الفِعليّ — لا مُجَرَّد ذِكر الكَلِمَة."""
    if not lemma:
        return []
    # نَتَوَقَّع cards تَتَّفِق في construction_parent أَو في القُرب لِلجُزء/الصَّفحَة
    target_ref = (construction.get("source_refs") or [{}])[0] if construction else {}
    target_part = target_ref.get("part")
    target_page = target_ref.get("page_start")

    accepted = []
    for card in _read_meaning_cards():
        triggers = card.get("triggers", {}) or {}
        lemmas = triggers.get("lemmas", []) if isinstance(triggers, dict) else []
        if lemma not in lemmas:
            continue
        # نَفحَص هَل الـ description تَستَخدِم اللَّمَة كَفِعل
        description = card.get("description", "")
        if not _claim_uses_verb(description, lemma, token):
            continue
        # تَفضيل cards مِن نَفس الجُزء أَو القَريب
        card_ref = (card.get("source_refs") or [{}])[0]
        card_part = card_ref.get("part")
        card_page = card_ref.get("page_start")
        proximity = 999
        if target_part and target_page and card_part and card_page:
            if card_part == target_part:
                proximity = abs(card_page - target_page)
            else:
                proximity = 1000 + abs(card_part - target_part) * 500
        # نَستَبعِد cards مِن نَوع review_only
        if card.get("engine_applicability") == "review_only":
            continue
        accepted.append({
            "meaning_id": card.get("meaning_id"),
            "title": card.get("title"),
            "type": card.get("meaning_type"),
            "applicability": card.get("engine_applicability"),
            "description": (description or "")[:240],
            "source_ref": card_ref,
            "confidence": card.get("confidence"),
            "_proximity": proximity,
        })
    # رَتِّب بِالقُرب ثُمّ الثِّقَة
    accepted.sort(key=lambda c: (c.get("_proximity", 999), -c.get("confidence", 0)))
    # نَزع الحَقل المُؤَقَّت
    for c in accepted:
        c.pop("_proximity", None)
    return accepted[:5]


_CARDS_CACHE = None


def _read_meaning_cards() -> list[dict]:
    global _CARDS_CACHE
    if _CARDS_CACHE is not None:
        return _CARDS_CACHE
    path = _HERE.parent / "maani_alnahw" / "data" / "processed" / "maani_alnahw" / "meaning_cards.jsonl"
    out = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    _CARDS_CACHE = out
    return out


def format_report(result: dict, deep: bool = False) -> str:
    """تَنسيق نَتيجَة كَتَقرير عَرَبيّ."""
    lines = []
    box_w = 78

    def _hline(c="═"):
        return c * box_w

    lines.append(_hline("═"))
    lines.append("  مُحَلِّل «مَعاني النَّحو» — MaaniAnalyzer:v1")
    lines.append(_hline("═"))
    lines.append(f"  المَصدَر: {result.get('source') or 'نَصّ مُباشَر'}")
    lines.append(f"  النَّصّ:  {result.get('verse', '')[:80]}")
    lines.append(f"  عَدَد الكَلِمات: {result.get('n_words', 0)} · "
                 f"المُطابَقات: {result.get('n_hits', 0)}")
    stats = result.get("kb_stats", {})
    lines.append(f"  قاعِدَة المَعرِفَة: {stats.get('rules', 0)} rule، "
                 f"{stats.get('constructions', 0)} construction، "
                 f"{stats.get('topics', 0)} topic")

    hits = result.get("hits", [])
    if not hits:
        lines.append("")
        lines.append(_hline("─"))
        lines.append("  لا مُطابَقَة مِن مَعاني النَّحو لِهذِه الآيَة.")
        lines.append("  (لا فِعل أَو حَرف مَكشوف في قاعِدَة المَعرِفَة)")
        lines.append(_hline("═"))
        return "\n".join(lines)

    for i, hit in enumerate(hits, 1):
        lines.append("")
        lines.append(_hline("─"))
        lines.append(f"  ◆ مُطابَقَة [{i}]: «{hit.get('token','')}» → "
                     f"{hit.get('construction_id','')}")
        lines.append(_hline("─"))

        # ── ① المَعنى الدَّلاليّ (المُهِمّ) ──
        interp = hit.get("semantic_interpretation") or {}
        if interp.get("summary"):
            lines.append("")
            lines.append(f"  ▸ المَعنى:")
            lines.append(f"     {interp['summary']}.")

        # ── ② التَّحويل العَميق ──
        if interp.get("deep_transform_from"):
            lines.append("")
            lines.append(f"  ▸ التَّحويل العَميق:")
            lines.append(f"     • الأَصل:    {interp['deep_transform_from']}")
            lines.append(f"     • الناتِج:  {interp['deep_transform_to']}")
            if interp.get("deep_predication"):
                lines.append(f"     • الإِسناد العَميق:  {interp['deep_predication']}")

        # ── ③ الجِهَة (modality) وَ العَلاقَة ──
        lines.append("")
        lines.append(f"  ▸ السِّمات الدَّلاليَّة:")
        if interp.get("modality_ar"):
            lines.append(f"     • الجِهَة:    {interp['modality_ar']}")
        if interp.get("relation_ar"):
            lines.append(f"     • العَلاقَة:  {interp['relation_ar']}")
        lines.append(f"     • lemma مُطابِق:  {hit.get('matched_lemma','')}")
        if not hit.get("is_verb_form", True):
            lines.append(f"     ⚠ تَنبيه: قَد لا يَكون هذا فِعلًا — رُبَّما اسم أَو حَرف")

        # ── ④ النَّمَط النَّحويّ ──
        detail = hit.get("construction_detail") or {}
        pattern = detail.get("pattern") or []
        if pattern:
            lines.append("")
            lines.append(f"  ▸ النَّمَط النَّحويّ:")
            for slot in pattern:
                slot_name = slot.get("slot", "?")
                role = slot.get("role", "?")
                case = slot.get("case", "—")
                lines.append(f"     • {slot_name:12s} ← {role} ({case})")

        # ── ⑤ تَحذيرات المُؤَلِّف ──
        warnings = hit.get("warnings") or []
        if warnings:
            lines.append("")
            lines.append(f"  ▸ تَحذيرات المُؤَلِّف:")
            for w in warnings[:4]:
                lines.append(f"     ⚠ {w}")

        # ── ⑥ أَمثلَة المُؤَلِّف (مُختارَة يَدَويًّا) ──
        examples = hit.get("author_examples") or []
        if examples:
            lines.append("")
            lines.append(f"  ▸ أَمثلَة مِن المُؤَلِّف ({len(examples)}):")
            for ex in examples[:5]:
                txt = ex.get("text", "")
                obj1 = ex.get("object_1", "")
                obj2 = ex.get("object_2", "")
                deep = ex.get("deep_predication", "")
                if txt:
                    line = f"     • «{txt}»"
                    if obj1 or obj2:
                        parts = []
                        if obj1: parts.append(f"م1={obj1}")
                        if obj2: parts.append(f"م2={obj2}")
                        line += f"   ({', '.join(parts)})"
                    lines.append(line)
                    if deep:
                        lines.append(f"        ⇨ الإِسناد العَميق: «{deep}»")
                src = ex.get("source")
                if isinstance(src, dict) and src.get("surah"):
                    lines.append(f"        ⤷ {src.get('surah')}: {src.get('ayah','?')}")

        # ── ⑦ المَصدَر ──
        src = hit.get("source_ref", {})
        if src:
            lines.append("")
            lines.append(f"  ▸ المَصدَر: «مَعاني النَّحو» ج{src.get('part','?')} "
                         f"ص{src.get('page_start','?')}")

        # ── ⑧ (مَع --deep) cards إِضافيَّة مَع وَصف ──
        if deep:
            cards = hit.get("related_meaning_cards") or []
            if cards:
                lines.append("")
                lines.append(f"  ▸ بِطاقات إِضافيَّة مُرشَّحَة ({len(cards)}):")
                for card in cards:
                    lines.append(f"     ◇ {card['title']}")
                    lines.append(f"       نَوع={card['type']}، ثِقَة={card['confidence']}")
                    if card.get("description"):
                        lines.append(f"       {card['description'][:160]}")
                    if card.get("source_ref"):
                        sr = card["source_ref"]
                        lines.append(f"       المَصدَر: ج{sr.get('part','?')} ص{sr.get('page_start','?')}")
            else:
                lines.append("")
                lines.append("  ▸ لا بِطاقات إِضافيَّة عالية الثِّقَة.")

    lines.append("")
    lines.append(_hline("═"))
    lines.append("  انتَهى استخراج مَعاني النَّحو.")
    lines.append(_hline("═"))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="استخراج طَبَقَة «مَعاني النَّحو» مِن آيَة"
    )
    ap.add_argument(
        "verse",
        nargs="?",
        help="رَقم آية (سُورَة:آيَة) أَو نَصّ مُباشَر",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="إخراج JSON بَدَل تَقرير عَرَبيّ",
    )
    ap.add_argument(
        "--deep",
        action="store_true",
        help="عَرض meaning_cards بِوَصف كامِل",
    )
    args = ap.parse_args()

    if args.verse:
        raw = args.verse
    else:
        raw = sys.stdin.read().strip()
    if not raw:
        print("خَطَأ: لَم يُمَرَّر نَصّ ولا رَقم آية.", file=sys.stderr)
        sys.exit(1)

    try:
        verse, source = _resolve_input(raw)
    except (FileNotFoundError, ValueError) as e:
        print(f"خَطَأ: {e}", file=sys.stderr)
        sys.exit(2)

    result = extract_maani_for_verse(verse, source=source)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(result, deep=args.deep))


if __name__ == "__main__":
    main()
