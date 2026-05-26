"""maani_kb_loader.py — مُحَمِّل قاعِدَة مَعرِفَة «مَعاني النَّحو».

يَجِسر بَين خَطّ تَحليل القُرآن (analyze_verse) وَ بَين قاعِدَة المَعرِفَة
المُستَخرَجَة في `maani_alnahw/data/processed/maani_alnahw/`.

API:
  • get_kb() — يُرجِع GrammarKB singleton
  • lookup_construction_for_verb(lemma) — يَجِد التَّركيب المُناسِب
  • get_modality_for_verb(lemma) — modality مِن construction
  • get_lam_lamma_semantics() — لِنَفي المُضارع
  • get_jawab_talab_test() — لِفَحص جَواب الطَّلَب

CONSTITUTIONAL: لا قَرارات هُنا، فَقَط lookup.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional


_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
_MAANI_KB_SRC = _PROJECT_ROOT / "maani_alnahw" / "src"
_MAANI_PROCESSED = _PROJECT_ROOT / "maani_alnahw" / "data" / "processed" / "maani_alnahw"


if str(_MAANI_KB_SRC) not in sys.path:
    sys.path.insert(0, str(_MAANI_KB_SRC))


CONTRACT_NAME = "MaaniKBLoader:v1"


_kb_instance = None


def get_kb():
    """يُرجِع GrammarKB singleton (lazy-loaded)."""
    global _kb_instance
    if _kb_instance is None:
        try:
            from grammar_kb.query import GrammarKB
            _kb_instance = GrammarKB(_MAANI_PROCESSED)
            # نُضيف curated constructions (يَدَويَّة) إِن وُجِدَت
            _load_curated_constructions(_kb_instance)
        except Exception as e:
            print(f"[MaaniKBLoader] فَشِل التَّحميل: {e}", file=sys.stderr)
            _kb_instance = _NullKB()
    return _kb_instance


def _load_curated_constructions(kb):
    """يُضيف constructions يَدَويَّة (تَقديم، إِيَّاك، إلخ) لِلـ KB."""
    import json
    curated_path = _MAANI_PROCESSED / "curated_constructions.jsonl"
    if not curated_path.exists():
        return
    with open(curated_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                cons = json.loads(line)
                cid = cons.get("construction_id")
                if cid and cid not in kb._by_construction:
                    kb._constructions.append(cons)
                    kb._by_construction[cid] = cons
            except json.JSONDecodeError:
                pass


class _NullKB:
    """KB فارغَة — لِلتَّوَقّيّ مِن الانهيار."""
    def by_lemma(self, lemma): return []
    def by_construction(self, cid): return None
    def by_topic(self, tid): return []
    def all_constructions(self): return []
    def all_rules(self): return []
    def find_by_text(self, q): return []
    def stats(self): return {"rules": 0, "constructions": 0, "topics": 0}


# ─── API مُسَطَّحَة لِلاستِخدام مِن خَطّ التَّحليل ────────────────────────

def _strip_diac_simple(s: str) -> str:
    diacritics = "ًٌٍَُِّْـٰٓ"
    return "".join(c for c in s if c not in diacritics)


def _normalize_alef(s: str) -> str:
    return s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")


# ─── PACKAGE A — Extensions ─────────────────────────────────────────────
# ① نَزع البَوادِئ ② تَمديد بِالجَذر ④ لاحِقات إِيَّا

# بَوادِئ شائعَة: حَرف عَطف/جَرّ/استِفهام/سين تَنفيس + ال التَّعريف
# نَزعها رُتَبَ مِن الأَطوَل لِلأَقصَر مَع تَكرار حَتَّى الاستِقرار
PREFIX_CASCADE = [
    # ال التَّعريف
    "ال", "ٱل",
    # حَرف واحِد
    "و", "ف", "ل", "ب", "س", "ك", "أ", "ي", "ت", "ن",
]


def _strip_prefixes(word: str, max_iterations: int = 3) -> list[str]:
    """يُعيد قائِمَة مِن صُوَر الكَلِمَة بَعد نَزع البَوادِئ تَدريجيًّا.

    مَثَلًا «وَحَسِبَ» → ["وحسب", "حسب"].
    لا نَنزَع تَلقائيًّا أَكثَر مِن 3 بَوادِئ (و+س+فِعل = الحَدّ).
    """
    plain = _normalize_alef(_strip_diac_simple(word))
    forms = [plain]
    current = plain
    # حَرف عَطف/جَرّ (واحِد) — نُجَرِّب نَزعه
    for prefix in ["و", "ف", "ل", "ب", "ك", "س", "أ", "ي", "ت", "ن"]:
        if current.startswith(prefix) and len(current) > len(prefix) + 1:
            stripped = current[len(prefix):]
            if stripped not in forms:
                forms.append(stripped)
            # نَزع ال التَّعريف بَعد البادِئَة
            if stripped.startswith("ال") and len(stripped) > 3:
                forms.append(stripped[2:])
            break  # بادِئَة واحِدَة فَقَط
    # نَزع ال التَّعريف مُباشَرَةً
    if plain.startswith("ال") and len(plain) > 3:
        without_al = plain[2:]
        if without_al not in forms:
            forms.append(without_al)
    return forms


def _root_from_word(word: str, root: str = "") -> str:
    """يُحَوِّل الجَذر إلى صورَة مُوَحَّدَة (مَثَلًا «ظ ن ن» → «ظنن»)."""
    if root:
        return root.replace(" ", "").strip()
    return ""


def _lemma_root(lemma: str) -> str:
    """يَستَنبِط جَذر lemma بَسيط (يَعمَل لِلأَفعال الثُّلاثيَّة)."""
    plain = _strip_diac_simple(lemma)
    # نَزع و/ف/ل بادِئَة
    for p in ["و", "ف", "ل"]:
        if plain.startswith(p) and len(plain) > 1:
            plain = plain[1:]
            break
    return plain


def _strip_first_prefix_keep_diac(word: str) -> str:
    """يَنزَع بادِئَة واحِدَة (و/ف/ب/ل/ك) بِالاحتِفاظ بِالتَّشكيل لِلباقي.

    «وَحَسِبَ» → «حَسِبَ»  (نَزع وَ بِفَتحَتها)
    """
    diacritics = set("ًٌٍَُِّْـٰٓ")
    if not word:
        return word
    # نَجِد الحَرف الأَوَّل غَير المُشَكَّل
    first_letter = word[0]
    if first_letter not in "وفبلكسأ":
        return word
    # نَتَجاوَز البادِئَة + تَشكيلها
    i = 1
    while i < len(word) and word[i] in diacritics:
        i += 1
    return word[i:]


def _is_verb_form_quick(word: str) -> bool:
    """heuristic سَريع لِتَمييز الفِعل — يَحتَفِظ بِالتَّشكيل عِندَ نَزع البَوادِئ.

    يَستَخدِم i3rab_engine.layer1._looks_like_verb_by_surface عَلى:
      1. الكَلِمَة كَما هي
      2. بَعد نَزع بادِئَة واحِدَة (مَع تَشكيلها)
      3. بَعد نَزع بادِئَتَين (لِحالات «فَلَيَنفُذ»، «وَلِيُؤمِنوا»)
    """
    if not word:
        return False
    try:
        from i3rab_engine.layer1 import _looks_like_verb_by_surface
    except ImportError:
        return _is_verb_form_fallback(word)

    # 1. الكَلِمَة كَما هي
    is_v, _ = _looks_like_verb_by_surface(word)
    if is_v:
        return True

    # 2. نَزع بادِئَة واحِدَة (مَع تَشكيلها)
    w1 = _strip_first_prefix_keep_diac(word)
    if w1 != word:
        is_v, _ = _looks_like_verb_by_surface(w1)
        if is_v:
            return True

    # 3. نَزع بادِئَتَين (مَثَلًا «وَلِيُؤمِنوا»)
    w2 = _strip_first_prefix_keep_diac(w1)
    if w2 != w1:
        is_v, _ = _looks_like_verb_by_surface(w2)
        if is_v:
            return True

    # 4. fallback: لاحِقات الفِعل (تم، تما، نا، وا، ت) — بَعد نَزع البَوادِئ
    if _is_verb_form_fallback(word):
        return True
    if _is_verb_form_fallback(w1):
        return True

    # 5. فِعل ثُلاثيّ قَصير (ظَنَّ، رَدَّ) — يَنتَهي بِشَدَّة + فَتحَة
    if "ّ" in word and word.endswith("َ"):
        return True
    # «ظَنَّ» أَو «وَظَنَّ» تَنتَهي بِشَدَّة-فَتحَة-سُكون مُحتَمَل
    if len(word) >= 3 and any(c in word for c in "َُِ"):
        last_diac = ""
        for c in reversed(word):
            if c in "ًٌٍَُِّْ":
                last_diac = c
                break
        if last_diac == "َ":
            # تَحَقُّق إِضافيّ: لَيسَ بَعد ال التَّعريف وَ لَيسَ مَوزون اسم
            plain = _strip_diac_simple(word)
            if not plain.startswith("ال") and len(plain) <= 6:
                return True

    return False


def _is_verb_form_fallback(word: str) -> bool:
    """fallback لِفَحص فِعل الماضي (فَعَلَ، فَعِلَ، فَعُلَ) — يَتطَلَّب فَتحَة أَخيرَة."""
    if not word:
        return False
    plain = _strip_diac_simple(word)
    # نَفحَص هَل الكَلِمَة الأَصليَّة تَنتَهي بِفَتحَة + شَدَّة مُحتَمَلَة
    # (نُمَيِّز ظَنَّ، حَسِبَ، عَلِمَ، رَأَى) عَن الأَسماء
    last_visible = ""
    for c in reversed(word):
        if c not in "ًٌٍَُِّْـٰٓ":
            last_visible = c
            break
    if not last_visible:
        return False
    # ماضي يَنتَهي بِالـ fatḥa
    diacritics_str = "".join(c for c in word if c in "ًٌٍَُِّْـٰٓ")
    # نَتَفَحَّص هَل آخِر تَشكيل قَبل آخِر حَرف هي fatḥa أَو dammatan
    # أَو نَفحَص هَل النَّصّ يَحوي «َ» في النِّهايَة قَريبًا
    last_chars = word[-3:] if len(word) >= 3 else word
    if "َ" in last_chars and len(plain) >= 3 and plain[0] not in "اوي":
        return True
    # بَوادِئ المُضارِع بَعد نَزع البَوادِئ
    bare = plain
    for p in "وفلب":
        if bare.startswith(p) and len(bare) > 1:
            bare = bare[1:]
            break
    if bare and bare[0] in "يتنأ":
        return True
    # لاحِقات الماضي مَع الضَّمير
    for suf in ["تما", "تم", "تن", "نا", "وا"]:
        if plain.endswith(suf) and len(plain) > len(suf) + 1:
            return True
    if plain.endswith("ت") and len(plain) >= 4:
        return True
    return False


def lookup_construction_for_verb(lemma: str, root: str = "",
                                  require_verb_form: bool = True) -> Optional[dict]:
    """يَجِد التَّركيب المُناسِب لِفِعل.

    Strategy (Package A + verb filter):
      ① نُجَرِّب lemma مُباشَرَة
      ① نُجَرِّب صُوَر lemma بَعد نَزع البَوادِئ
      ② نُجَرِّب مُطابَقَة بِالجَذر
      + verb_filter: نَرفُض إِن كانَت الكَلِمَة لا تَبدو فِعلًا (لِتَجَنُّب
        false positives كَ «عِلْمَ» اسم vs «عَلِمَ» فِعل)

    Returns: dict مَع _match_info.
    """
    # ✓ verb filter قَبل أَيّ مُطابَقَة
    if require_verb_form and lemma and not _is_verb_form_quick(lemma):
        return None
    if not lemma and not root:
        return None
    kb = get_kb()

    # نَجمَع كُلّ صُوَر اللَّمَة المُحتَمَلَة
    lemma_forms = _strip_prefixes(lemma) if lemma else []
    target_root = _normalize_alef(_strip_diac_simple(root)).replace(" ", "") if root else ""

    for c in kb.all_constructions():
        triggers = c.get("triggers", {})
        kb_lemmas = triggers.get("lemma", [])
        if not kb_lemmas:
            continue

        # ① exact أَو prefix-stripped
        for form in lemma_forms:
            for kb_lemma in kb_lemmas:
                kb_plain = _normalize_alef(_strip_diac_simple(kb_lemma))
                if form == kb_plain:
                    cc = dict(c)
                    cc["_match_info"] = {
                        "extension_type": "verb_lemma" if form == lemma_forms[0] else "prefix_stripped",
                        "matched_lemma": kb_lemma,
                        "from_form": form,
                    }
                    return cc

        # ② root-based — يَطلُب جَذر صَريح مِن المُدخَل
        if target_root:
            for kb_lemma in kb_lemmas:
                kb_root_guess = _lemma_root(kb_lemma)
                if target_root == kb_root_guess or target_root.startswith(kb_root_guess):
                    cc = dict(c)
                    cc["_match_info"] = {
                        "extension_type": "root_inflection",
                        "matched_lemma": kb_lemma,
                        "root": target_root,
                    }
                    return cc

    return None


IYYA_SUFFIXES = {
    # suffix: (person, number, gender_grammatical)
    "ك":  ("2", "SG", "M"),
    "كَ": ("2", "SG", "M"),
    "كِ": ("2", "SG", "F"),
    "كما": ("2", "DU", "X"),
    "كم": ("2", "PL", "M"),
    "كن": ("2", "PL", "F"),
    "كنّ": ("2", "PL", "F"),
    "ه":  ("3", "SG", "M"),
    "هُ": ("3", "SG", "M"),
    "ها": ("3", "SG", "F"),
    "هما": ("3", "DU", "X"),
    "هم": ("3", "PL", "M"),
    "هن": ("3", "PL", "F"),
    "هنّ": ("3", "PL", "F"),
    "نا": ("1", "PL", "X"),
    "ي":  ("1", "SG", "X"),
    "يَ": ("1", "SG", "X"),
}


def _detect_iyya_suffix(word_after_prefix: str) -> Optional[dict]:
    """word_after_prefix بَعد نَزع «إِيَّا» — يُعَرِّف الضَّمير.

    يُفَضِّل المُطابَقَة المُشَكَّلَة (كَ vs كِ) قَبل المُجَرَّدَة.
    """
    if not word_after_prefix:
        return None
    # نُجَرِّب بِالتَّشكيل أَوَّلًا (حَسّاس)
    raw = word_after_prefix.strip()
    # تَطبيع أَلِف فَقَط، لا تَشكيل
    raw_norm = raw.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    for suffix in sorted(IYYA_SUFFIXES.keys(), key=lambda s: -len(s)):
        if raw_norm == suffix:
            person, number, gender = IYYA_SUFFIXES[suffix]
            return {"suffix": suffix, "person": person, "number": number,
                    "gender_grammatical": gender}
    # بَدون تَشكيل (fallback)
    diacritics = "ًٌٍَُِّْـٰٓ"
    plain = "".join(c for c in raw_norm if c not in diacritics)
    for suffix in sorted(IYYA_SUFFIXES.keys(), key=lambda s: -len(s)):
        suffix_plain = "".join(c for c in suffix if c not in diacritics)
        if plain == suffix_plain:
            person, number, gender = IYYA_SUFFIXES[suffix]
            return {"suffix": suffix, "person": person, "number": number,
                    "gender_grammatical": gender}
    return None


def lookup_construction_for_word(word: str) -> Optional[dict]:
    """يَجِد تَركيبًا مَبنيًّا عَلى word_prefix (إِيَّاكَ، إِيَّاهُم، إِيَّانا، …).

    شُروط الاكتِشاف:
      1. البادِئَة تُطابِق word_prefix (إيا/إِيّا)
      2. اللاحِقَة بَعد البادِئَة يَجِب أَن تَكون ضَميرًا صَحيحًا
      3. الكَلِمَة تَبدَأ بِـ «إ» (هَمزَة مَكسورَة) — لا «أ»
         يَرفُض «أَيَّام» (يَوم)، «أَيَّان» (مَتى)، «أَيَّامًا»
    """
    if not word:
        return None
    plain = _normalize_alef(_strip_diac_simple(word))

    # ✓ شَرط أَوَّليّ صارِم: يَجِب أَن تَبدَأ بِـ «إ» (هَمزَة مَكسورَة)
    # «إِيَّا» وَ «إِيَّاكَ» تَبدَأ بِـ «إ»
    # «أَيَّام» وَ «أَيَّان» تَبدَأ بِـ «أ» (مَرفوض)
    if not word.startswith("إ"):
        return None

    kb = get_kb()
    for c in kb.all_constructions():
        triggers = c.get("triggers", {})
        prefixes = triggers.get("word_prefix", [])
        for p in prefixes:
            p_plain = _normalize_alef(_strip_diac_simple(p))
            if not plain.startswith(p_plain):
                continue
            remainder = plain[len(p_plain):]
            # ✓ شَرط: لاحِقَة مَعروفَة (ضَمير صَحيح)
            pronoun_info = _detect_iyya_suffix(remainder)
            if pronoun_info is None:
                continue
            cc = dict(c)
            cc["_match_info"] = {
                "extension_type": "pronoun_suffix",
                "matched_prefix": p,
                "suffix_raw": remainder,
                "pronoun_features": pronoun_info,
            }
            return cc
    return None


def lookup_order_pattern_constructions(words: list[dict]) -> list[dict]:
    """يَجِد constructions بِناءً عَلى تَرتيب الكَلِمات (مَثَلًا تَقديم المَفعول).

    words: list of word dicts بِـ word + word_class أَو حالَة إِعراب
    """
    kb = get_kb()
    matches = []
    for c in kb.all_constructions():
        triggers = c.get("triggers", {})
        order = triggers.get("order_pattern", "")
        markers = triggers.get("marker_words", [])
        if not order and not markers:
            continue
        # نَفحَص هَل في الكَلِمات marker مُطابِق
        for w in words:
            token = w.get("word", "") or w.get("token", "")
            token_plain = _strip_diac_simple(token).replace("إ", "ا").replace("أ", "ا")
            for m in markers:
                m_plain = _strip_diac_simple(m).replace("إ", "ا").replace("أ", "ا")
                if token_plain.startswith(m_plain):
                    matches.append({
                        "construction": c,
                        "matched_token": token,
                        "matched_marker": m,
                    })
                    break
            else:
                continue
            break
    return matches


def get_modality_for_verb(lemma: str) -> Optional[str]:
    """يُرجِع modality لِفِعل في ZANN family."""
    c = lookup_construction_for_verb(lemma)
    if not c:
        return None
    mod_map = (c.get("semantic_output") or {}).get("modality_by_lemma", {})
    return mod_map.get(lemma)


def get_construction(construction_id: str) -> Optional[dict]:
    return get_kb().by_construction(construction_id)


def get_lam_lamma_semantics() -> Optional[dict]:
    return get_construction("LAM_VS_LAMMA")


def get_jawab_talab_test() -> Optional[dict]:
    return get_construction("JAWAB_AL_TALAB")


def get_arayta_construction() -> Optional[dict]:
    return get_construction("ARAYTAKUM_ISTIKHBAR")


def get_number_counted_construction() -> Optional[dict]:
    return get_construction("NUMBER_COUNTED")


def get_tadmeen_construction() -> Optional[dict]:
    return get_construction("TADMEEN")


def get_preposition_substitution_policy() -> Optional[dict]:
    return get_construction("PREPOSITION_SUBSTITUTION")


def get_stats() -> dict:
    return get_kb().stats()


# ─── self-test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    kb = get_kb()
    print(f"contract: {CONTRACT_NAME}")
    print(f"stats: {kb.stats()}")
    print()
    print("─── lookup ظَنّ ───")
    print(lookup_construction_for_verb("ظن"))
    print()
    print("─── modality حَسِب ───")
    print(get_modality_for_verb("حسب"))
    print()
    print("─── jawab talab ───")
    t = get_jawab_talab_test()
    if t:
        print(t.get("validation_test"))
