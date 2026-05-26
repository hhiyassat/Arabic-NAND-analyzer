"""linguistic_source_registry.py — تَحميل مُوَحَّد لِمَصادِر new_arabic_analyzer/data.

(Phase 2 مِن خُطَّة المُستَخدِم 2026-05-26)

الهَدَف:
  • قِراءَة 29 ملَفّ JSON في 02_mabniyat
  • تَحويلها إلى registry مُوَحَّد بِالحُقول الَّتي حَدَّدَها المُستَخدِم:
      source_id, source_type, priority, certainty,
      requires_context, candidate_outputs, blockers
  • لا تَغيير runtime — هَذا مُجَرَّد loader.

التَّعارُض = Hypothesis لا Certificate:
  لَو نَفس الـsurface ظَهَر في أَكثَر مِن ملَفّ بِـcandidates مُختَلِفَة،
  نَحتَفِظ بِكُلّها وَ نُعطي certainty = Hypothesis مَع requires_context.

API:
  load_registry() → dict[str, list[Entry]]
    key = surface (with tashkīl) أَو plain (stripped)
    value = list of Entry (قَد يَكون أَكثَر مِن واحِد لو مُلتَبِس)

  resolve(surface, *, strict=True) → list[Entry]
    يُرجِع كُلّ المُرَشَّحات لِسَطح مُعَيَّن
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

ROOT = Path("/sessions/nice-epic-cannon/mnt/new_arabic_analyzer/data")
MABNIYAT = ROOT / "02_mabniyat"
OUT_DIR = Path(__file__).resolve().parent / "data"
OUT_DIR.mkdir(exist_ok=True)
OUT_REGISTRY = OUT_DIR / "linguistic_source_registry.json"

_DIACRITICS = set("ًٌٍَُِّْٰـ")
_SUBLETTERS = set("ٰۭٓۚۖۗۘۙۛۜ۝ۥۦ۠")


def strip_diac(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIACRITICS)


def strip_all(s: str) -> str:
    return "".join(c for c in (s or "")
                   if c not in _DIACRITICS and c not in _SUBLETTERS)


def normalize(s: str) -> str:
    return (s or "").replace("ٱ","ا").replace("آ","ا").replace("إ","ا") \
                    .replace("أ","ا").replace("ٰ","ا")


# ─────────────────────────────────────────────────────────────
# Entry schema (per user spec)
# ─────────────────────────────────────────────────────────────

@dataclass
class Entry:
    source_id: str
    source_type: str
    surface: str
    surface_plain: str
    surface_normalized: str
    candidate_classes: list[str]
    category: str
    priority: int
    certainty: str
    requires_context: bool
    blockers: list[str]
    metadata: dict
    # Phase 2.5 addition: candidates as found in THIS source (before cross-merge)
    original_candidates: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────
# Per-file extractors
# ─────────────────────────────────────────────────────────────

def _load_json(name: str) -> list[dict]:
    p = MABNIYAT / name
    if not p.is_file():
        return []
    with p.open(encoding="utf-8") as f:
        d = json.load(f)
    return d.get("data", d) if isinstance(d, dict) else d


def _make_entry(source_file: str, row_id, surface: str, candidates: list[str],
                category: str, source_type: str = "closed_class",
                priority: int = 5, requires_context: bool = False,
                metadata: dict | None = None) -> Entry:
    return Entry(
        source_id=f"{source_file}#{row_id}",
        source_type=source_type,
        surface=surface,
        surface_plain=strip_diac(surface),
        surface_normalized=strip_all(normalize(surface)),
        candidate_classes=list(candidates),
        category=category,
        priority=priority,
        certainty="Hypothesis" if requires_context or len(candidates) > 1 else "Certificate",
        requires_context=requires_context,
        blockers=[],
        metadata=metadata or {},
        original_candidates=list(candidates),  # snapshot قَبل أَيّ merge
    )


def extract_demonstratives() -> list[Entry]:
    """02_mabniyat/demonstrative_pronouns.json → 53 entries"""
    f = "02_mabniyat/demonstrative_pronouns.json"
    out = []
    for row in _load_json("demonstrative_pronouns.json"):
        surf = (row.get("name") or "").strip()
        if not surf: continue
        out.append(_make_entry(
            f, row["id"], surf, ["ISM_MABNI"], "demonstrative",
            priority=8,  # closed-class, exact match
            metadata={"gender": row.get("gender"), "number": row.get("number_classification"),
                     "distance": row.get("distance")},
        ))
    return out


def extract_relatives() -> list[Entry]:
    """02_mabniyat/relative_pronouns.json → 48 entries"""
    f = "02_mabniyat/relative_pronouns.json"
    out = []
    for row in _load_json("relative_pronouns.json"):
        surf = (row.get("name") or "").strip()
        if not surf: continue
        # مَن/ما/أَيّ مُلتَبِسَة بِين اسم مَوصول وَ أَدوات أُخرى
        candidates = ["ISM_MAWSOOL"]
        plain = strip_diac(surf)
        ambig = plain in ("من", "ما", "أي", "أيا")
        if ambig:
            candidates = ["ISM_MAWSOOL", "ISM_MABNI"]  # might be interrog/conditional too
        out.append(_make_entry(
            f, row["id"], surf, candidates, "relative",
            priority=8 if not ambig else 6,
            requires_context=ambig,
            metadata={"gender": row.get("gender"), "number": row.get("number")},
        ))
    return out


def extract_pronouns_classification() -> list[Entry]:
    """02_mabniyat/pronouns_classification.json → 43 entries"""
    f = "02_mabniyat/pronouns_classification.json"
    out = []
    for row in _load_json("pronouns_classification.json"):
        surf = (row.get("pronoun_form") or row.get("pronoun") or "").strip()
        if not surf: continue
        out.append(_make_entry(
            f, row["id"], surf, ["ISM_MABNI"], "pronoun",
            priority=9,  # ضَمائر = حَسم تامّ
            metadata={"category": row.get("category"), "meaning": row.get("meaning")},
        ))
    return out


def extract_built_in_adverbs() -> list[Entry]:
    """02_mabniyat/built_in_adverbs.json → 21 entries (حَيْثُ، إِذْ…)"""
    f = "02_mabniyat/built_in_adverbs.json"
    out = []
    for row in _load_json("built_in_adverbs.json"):
        surf = (row.get("adverb") or "").strip()
        if not surf: continue
        out.append(_make_entry(
            f, row["id"], surf, ["ISM_MABNI"], "built_in_adverb",
            priority=8,
            metadata={"adverb_type": row.get("adverb_type")},
        ))
    return out


def extract_interrogative_tools() -> list[Entry]:
    """02_mabniyat/interrogative_tools_categories.json → 17 entries
       + interrogative_letters_tools.json → 6 entries"""
    out = []
    # categories (الأَكثَر — أَدوات الِاستِفهام كاسم: أَين كَيف مَتى…)
    f1 = "02_mabniyat/interrogative_tools_categories.json"
    for row in _load_json("interrogative_tools_categories.json"):
        surf = (row.get("tool") or "").strip()
        if not surf: continue
        type_ = (row.get("type") or "").strip()
        candidates = ["ISM_MABNI"] if "اسم" in type_ else ["HARF"]
        # مَن/ما هُنا مُلتَبِسَة
        if strip_diac(surf) in ("من","ما"):
            candidates = ["ISM_MABNI","HARF","ISM_MAWSOOL"]
        out.append(_make_entry(
            f1, row["id"], surf, candidates, "interrogative",
            priority=8 if len(candidates)==1 else 6,
            requires_context=(len(candidates)>1),
            metadata={"subject": row.get("subject"), "type": type_},
        ))
    # letters (هَل، أَ، etc. — حُروف استِفهام)
    f2 = "02_mabniyat/interrogative_letters_tools.json"
    for row in _load_json("interrogative_letters_tools.json"):
        surf = (row.get("tool") or "").strip()
        if not surf: continue
        type_ = (row.get("type") or "").strip()
        candidates = ["HARF"] if "حرف" in type_ else ["ISM_MABNI"]
        out.append(_make_entry(
            f2, row["id"], surf, candidates, "interrogative",
            priority=8,
            metadata={"question_about": row.get("question_about"), "type": type_},
        ))
    return out


def extract_conditional_tools() -> list[Entry]:
    """02_mabniyat/conditional_letters_tools.json → 21 entries"""
    f = "02_mabniyat/conditional_letters_tools.json"
    out = []
    for row in _load_json("conditional_letters_tools.json"):
        surf = (row.get("particle") or "").strip()
        if not surf: continue
        gf = (row.get("grammatical_function") or "")
        # أَدوات شَرط جازِمَة قَد تَكون اسمًا (مَن) أَو حَرفًا (إِنْ)
        candidates = ["HARF"] if "حرف" in gf else ["ISM_MABNI"]
        if strip_diac(surf) in ("من","ما","ايا","اينما","حيثما"):
            candidates = ["ISM_MABNI","HARF"]
        out.append(_make_entry(
            f, row["id"], surf, candidates, "conditional",
            priority=8 if len(candidates)==1 else 6,
            requires_context=(len(candidates)>1),
            metadata={"function": gf},
        ))
    return out


def extract_coordinating_conjunctions() -> list[Entry]:
    """02_mabniyat/coordinating_conjunctions.json → 23"""
    f = "02_mabniyat/coordinating_conjunctions.json"
    out = []
    for row in _load_json("coordinating_conjunctions.json"):
        surf = (row.get("letter") or "").strip()
        if not surf: continue
        out.append(_make_entry(
            f, row["id"], surf, ["HARF"], "conjunction",
            priority=9,  # حَرف عَطف صَريح
            metadata={"usages": row.get("usages")},
        ))
    return out


def extract_jazm_tools() -> list[Entry]:
    """02_mabniyat/jazm_tools.json → 20 (لَمْ، لَا، إِنْ…)"""
    f = "02_mabniyat/jazm_tools.json"
    out = []
    for row in _load_json("jazm_tools.json"):
        surf = (row.get("tool") or "").strip()
        if not surf: continue
        cat = (row.get("category") or "")
        # مَن/ما/مَهما قَد تَكون اسم شَرط
        if strip_diac(surf) in ("من","ما","مهما","حيثما"):
            cands = ["ISM_MABNI","HARF"]
            ctx = True
        else:
            cands = ["HARF"]
            ctx = False
        out.append(_make_entry(
            f, row["id"], surf, cands, "jazm",
            priority=8 if not ctx else 6,
            requires_context=ctx,
            metadata={"category": cat, "applies_on": row.get("applies_on")},
        ))
    return out


def extract_naseb_tools() -> list[Entry]:
    """02_mabniyat/present_naseb_tools.json → 10"""
    f = "02_mabniyat/present_naseb_tools.json"
    out = []
    for row in _load_json("present_naseb_tools.json"):
        surf = (row.get("tool") or "").strip()
        if not surf: continue
        # أَن مُلتَبِسَة (مَصدَريَّة vs مُفَسِّرَة vs زائِدَة)
        ctx = strip_diac(surf) in ("ان","انما","لن","لكن")
        out.append(_make_entry(
            f, row["id"], surf, ["HARF"], "naseb",
            priority=8 if not ctx else 7,
            requires_context=ctx,
            metadata={"meaning_usage": row.get("meaning_usage")},
        ))
    return out


def extract_prepositions() -> list[Entry]:
    """02_mabniyat/preposition_meanings.json → 56"""
    f = "02_mabniyat/preposition_meanings.json"
    out = []
    seen = set()  # نَفس الحَرف قَد يَتَكَرَّر بِمَعانٍ مُختَلِفَة
    for row in _load_json("preposition_meanings.json"):
        surf = (row.get("preposition") or "").strip()
        if not surf: continue
        key = (surf, row.get("meaning",""))
        if surf in seen: continue  # نَأخُذ أَوَّل مَعنى فَقَط — الباقي meta
        seen.add(surf)
        out.append(_make_entry(
            f, row["id"], surf, ["HARF"], "preposition",
            priority=9,  # حَرف جَرّ صَريح
            metadata={"meaning": row.get("meaning")},
        ))
    return out


def extract_vocative_particles() -> list[Entry]:
    """02_mabniyat/vocative_particles.json → 9"""
    f = "02_mabniyat/vocative_particles.json"
    out = []
    for row in _load_json("vocative_particles.json"):
        surf = (row.get("particle") or "").strip()
        if not surf: continue
        out.append(_make_entry(
            f, row["id"], surf, ["HARF"], "vocative",
            priority=9, metadata={"usage": row.get("usage")},
        ))
    return out


def extract_letters_answers() -> list[Entry]:
    """02_mabniyat/letters_answers.json → 10 (نَعَمْ، لا، بَلى…)"""
    f = "02_mabniyat/letters_answers.json"
    out = []
    for row in _load_json("letters_answers.json"):
        surf = (row.get("particle") or "").strip()
        if not surf: continue
        out.append(_make_entry(
            f, row["id"], surf, ["HARF"], "answer_particle",
            priority=8, metadata={"definition": row.get("definition")},
        ))
    return out


def extract_copulative_particles() -> list[Entry]:
    """02_mabniyat/copulative_particle.json → 7 (إِنَّ، أَنَّ…)"""
    f = "02_mabniyat/copulative_particle.json"
    out = []
    for row in _load_json("copulative_particle.json"):
        surf = (row.get("copulative_particle") or "").strip()
        if not surf: continue
        out.append(_make_entry(
            f, row["id"], surf, ["HARF"], "copulative",
            priority=8, metadata={"indication": row.get("indication")},
        ))
    return out


def extract_functional_substitutes() -> list[Entry]:
    """02_mabniyat/functional_indeclinable_substitutes.json → 7"""
    f = "02_mabniyat/functional_indeclinable_substitutes.json"
    out = []
    for row in _load_json("functional_indeclinable_substitutes.json"):
        surf = (row.get("noun") or row.get("name") or row.get("tool") or "").strip()
        if not surf:
            # try first non-id field
            for k, v in row.items():
                if k in ("id","al_bab_althani_id","category_id"): continue
                if isinstance(v, str) and len(v.strip()) <= 30:
                    surf = v.strip(); break
        if not surf: continue
        out.append(_make_entry(
            f, row["id"], surf, ["ISM_MABNI"], "functional_substitute",
            priority=7, metadata={k:v for k,v in row.items() if k != "id"},
        ))
    return out


def extract_kinaya() -> list[Entry]:
    """02_mabniyat/kinaya_names.json → 9 (كَمْ، كَأَيِّن…)"""
    f = "02_mabniyat/kinaya_names.json"
    out = []
    for row in _load_json("kinaya_names.json"):
        surf = (row.get("name") or "").strip()
        if not surf: continue
        out.append(_make_entry(
            f, row["id"], surf, ["ISM_MABNI"], "kinaya",
            priority=7, requires_context=True,  # سياقيَّة
            metadata={"type": row.get("type"), "usage": row.get("meaning_usage")},
        ))
    return out


def extract_verb_names() -> list[Entry]:
    """02_mabniyat/verb_name.json → 57 (أَسماء أَفعال: هَيْهات، صَهْ، آمين…)"""
    f = "02_mabniyat/verb_name.json"
    out = []
    for row in _load_json("verb_name.json"):
        surf = (row.get("name") or "").strip()
        if not surf: continue
        # اسم فِعل = وَظيفته فِعل لَكِن صَرفه اسم → نَضَع candidate FIIL
        out.append(_make_entry(
            f, row["id"], surf, ["FIIL", "ISM_MABNI"], "verb_name",
            priority=7, requires_context=False,
            metadata={"tense": row.get("tense"), "meaning": row.get("meaning")},
        ))
    return out


# ─────────────────────────────────────────────────────────────
# Build full registry
# ─────────────────────────────────────────────────────────────

def build_registry() -> dict:
    """يَبني الـregistry كامِلًا — مَع Phase 2.5 certainty fix.

    قاعِدَة Certificate الصارِمَة (تَوصيَة المُستَخدِم 2026-05-26):
      Certificate يَنفُذ فَقَط إذا:
        len(candidate_classes) == 1
        AND لا يوجَد conflict عَبر sources
        AND requires_context == False
        AND priority >= 8

      priority وَحدها لا تَطغى عَلى class conflict.

    Returns dict مَع 4 indexes + conflict_map.
    """
    extractors = [
        extract_demonstratives, extract_relatives,
        extract_pronouns_classification, extract_built_in_adverbs,
        extract_interrogative_tools, extract_conditional_tools,
        extract_coordinating_conjunctions, extract_jazm_tools,
        extract_naseb_tools, extract_prepositions,
        extract_vocative_particles, extract_letters_answers,
        extract_copulative_particles, extract_functional_substitutes,
        extract_kinaya, extract_verb_names,
    ]
    entries = []
    for ex in extractors:
        try:
            entries.extend(ex())
        except Exception as e:
            print(f"  WARN: {ex.__name__} failed: {e}")

    # First pass: index by surface variants
    by_surface = {}; by_plain = {}; by_normalized = {}
    for e in entries:
        by_surface.setdefault(e.surface, []).append(e)
        if e.surface_plain:
            by_plain.setdefault(e.surface_plain, []).append(e)
        if e.surface_normalized:
            by_normalized.setdefault(e.surface_normalized, []).append(e)

    # === Phase 2.5: Global conflict detection ===
    # نَجمَع كُلّ الـcandidate_classes لِكُلّ plain surface عَبر كُلّ المَلَفّات
    conflict_map = {}  # plain_surface → set of candidate classes
    for plain, es in by_plain.items():
        all_cands = set()
        for e in es:
            all_cands.update(e.candidate_classes)
        conflict_map[plain] = all_cands

    # === Phase 2.5: تَطبيق قاعِدَة Certificate الصارِمَة ===
    # Semantic ordering لِلـcandidates المُلتَبِسَة:
    #   أَسماء الاستِفهام/الإِشارَة/المَوصول أَسماء لُغَويًّا غالِبًا، لِذا
    #   ISM_MABNI/ISM_MAWSOOL يَأتي قَبل HARF.
    SEMANTIC_PRIORITY = {
        "ISM_MAWSOOL": 6,
        "ISM_MABNI": 5,
        "FIIL": 4,
        "ISM_MUARAB": 3,
        "JAMID": 2,
        "HARF": 1,
    }
    def _sort_candidates(cands):
        return sorted(cands, key=lambda c: -SEMANTIC_PRIORITY.get(c, 0))

    for e in entries:
        all_cands_for_plain = conflict_map.get(e.surface_plain, set(e.candidate_classes))
        if len(all_cands_for_plain) > 1:
            # تَعارُض — أَدرِج كُلّ candidates مَع semantic ordering، أَجبِر Hypothesis
            e.candidate_classes = _sort_candidates(all_cands_for_plain)
            e.certainty = "Hypothesis"
            e.requires_context = True
            e.blockers.append(f"cross_source_conflict:{len(all_cands_for_plain)}_classes")
        elif e.requires_context or len(e.candidate_classes) > 1:
            e.candidate_classes = _sort_candidates(e.candidate_classes)
            e.certainty = "Hypothesis"
        elif e.priority < 8:
            e.certainty = "Hypothesis"
            e.blockers.append(f"priority_below_threshold:{e.priority}")
        else:
            e.certainty = "Certificate"

    return {
        "entries": entries,
        "by_surface": by_surface,
        "by_plain": by_plain,
        "by_normalized": by_normalized,
        "conflict_map": conflict_map,
    }


def resolve(surface: str, registry: dict | None = None) -> list[Entry]:
    """يُرجِع كُلّ المُرَشَّحات لِسَطح مُعَيَّن (مَرتَّبَة حَسَب priority desc)."""
    if registry is None:
        registry = build_registry()
    if not surface:
        return []
    matches = []
    if surface in registry["by_surface"]:
        matches.extend(registry["by_surface"][surface])
    plain = strip_diac(surface)
    if plain and plain in registry["by_plain"]:
        for e in registry["by_plain"][plain]:
            if e not in matches:
                matches.append(e)
    norm = strip_all(normalize(surface))
    if norm and norm in registry["by_normalized"]:
        for e in registry["by_normalized"][norm]:
            if e not in matches:
                matches.append(e)
    return sorted(matches, key=lambda e: -e.priority)


# ─────────────────────────────────────────────────────────────
# Phase 2.5: Compound lookup (لِمَاذَا = لِ + مَا + ذَا)
# ─────────────────────────────────────────────────────────────

# بادِئات قابِلَة لِلتَّقطيع (حُروف جَرّ/عَطف/نَصب…)
_STRIPPABLE_PREFIXES = ["لِ","ل","بِ","ب","فَ","ف","وَ","و","كَ","ك","سَ","س"]


def resolve_compound(surface: str, registry: dict | None = None) -> dict | None:
    """يَبحَث عَن surface كَ compound بِبادِئات قابِلَة لِلِاستِخراج.

    مَثَل: لِمَاذَا → لِ + ماذا
          فَكَيفَ  → فَ + كيف
          وَمَن    → وَ + مَن

    يُرجِع:
      {
        "segments": [{"surface":"لِ","entry":<Entry>}, {"surface":"مَاذَا","entry":<Entry>}],
        "head": <Entry of last segment>,  # هو الحامِل لِلصَّنف
        "is_compound": True,
      }
      أَو None إِن لَم يُمكِن التَّحليل.
    """
    if registry is None:
        registry = build_registry()
    if not surface or len(surface) < 3:
        return None
    # 1. جَرِّب prefix-stripping (مَرَّة واحِدَة فَقَط لأَنّ غالِبيَّة الأَدوات MoNo-prefix)
    for pfx in _STRIPPABLE_PREFIXES:
        if surface.startswith(pfx) and len(surface) > len(pfx) + 1:
            rest = surface[len(pfx):]
            rest_norm = strip_all(normalize(rest))
            # ابحَث rest في registry
            rest_matches = resolve(rest, registry)
            if not rest_matches:
                continue
            # ابحَث pfx ذاته (إِن كان حَرف جَرّ)
            pfx_matches = resolve(pfx, registry)
            if not pfx_matches:
                # قَد لا يَكون pfx في registry (مَثَل ل-التَّعليل)
                pass
            return {
                "segments": [
                    {"surface": pfx, "entry": pfx_matches[0] if pfx_matches else None},
                    {"surface": rest, "entry": rest_matches[0]},
                ],
                "head": rest_matches[0],
                "is_compound": True,
            }
    # 2. جَرِّب 2-prefix combos (فَلِمَ، وَلِمَ)
    for pfx1 in ("فَ","وَ","ف","و"):
        if surface.startswith(pfx1):
            for pfx2 in ("لِ","بِ","ل","ب","كَ","ك"):
                combo = pfx1 + pfx2
                if surface.startswith(combo) and len(surface) > len(combo) + 1:
                    rest = surface[len(combo):]
                    rest_matches = resolve(rest, registry)
                    if rest_matches:
                        return {
                            "segments": [
                                {"surface": pfx1, "entry": None},
                                {"surface": pfx2, "entry": None},
                                {"surface": rest, "entry": rest_matches[0]},
                            ],
                            "head": rest_matches[0],
                            "is_compound": True,
                        }
    return None


def resolve_strict(surface: str, registry: dict | None = None) -> dict:
    """resolve كامِل بِالبَوّابات (Certificate صارِم).

    يُرجِع:
      {
        "surface": "...",
        "found": bool,
        "candidates": [str],     # word_class candidates
        "certainty": "Certificate" | "Hypothesis" | "Zero",
        "requires_context": bool,
        "source": "registry:..." | "compound:..." | "no_match",
        "matched_entries": [Entry],
        "blockers": [str],
      }
    """
    if registry is None:
        registry = build_registry()
    out = {
        "surface": surface, "found": False,
        "candidates": [], "certainty": "Zero",
        "requires_context": False, "source": "no_match",
        "matched_entries": [], "blockers": [],
    }
    if not surface:
        return out

    # Phase 2.5.1: exact-tashkīl match يَستَخدِم original_candidates
    # (لا cross-source merge، لأَنّ التَّشكيل يُمَيِّز مِنْ مِن مَنْ)
    if surface in registry["by_surface"]:
        es = registry["by_surface"][surface]
        # اِجمَع original_candidates مِن كُلّ entries لِنَفس الـsurface
        orig_cands = set()
        for e in es:
            orig_cands.update(e.original_candidates)
        # رَتِّب semantic
        SEMANTIC = {"ISM_MAWSOOL":6,"ISM_MABNI":5,"FIIL":4,"ISM_MUARAB":3,"JAMID":2,"HARF":1}
        sorted_cands = sorted(orig_cands, key=lambda c: -SEMANTIC.get(c,0))
        top_e = sorted(es, key=lambda e: -e.priority)[0]
        out["found"] = True
        out["candidates"] = sorted_cands
        # exact + single class + priority>=8 → Certificate (تَجاوُز cross-source conflict)
        if len(orig_cands) == 1 and top_e.priority >= 8 and not top_e.requires_context:
            out["certainty"] = "Certificate"
        else:
            out["certainty"] = "Hypothesis"
        out["requires_context"] = top_e.requires_context or len(orig_cands) > 1
        out["source"] = f"exact:{top_e.source_id}"
        out["matched_entries"] = es
        out["blockers"] = list(top_e.blockers)
        return out

    # plain/normalized lookup مَع shadda parity check
    # هَمَّ (شَدَّة) ≠ هم (بِلا شَدَّة) — يَجِب أَن لا يَتَطابَقا
    input_shadda_count = surface.count("ّ")
    matches = resolve(surface, registry)
    # تَصفيَة: احذِف matches الَّتي تَختَلِف في شَدَّة عَن الـinput
    matches = [e for e in matches if e.surface.count("ّ") == input_shadda_count]
    if matches:
        top = matches[0]
        all_cands = set()
        for e in matches:
            all_cands.update(e.candidate_classes)
        out["found"] = True
        out["candidates"] = list(top.candidate_classes)
        out["matched_entries"] = matches
        out["source"] = f"plain:{top.source_id}"
        if len(all_cands) == 1 and not top.requires_context:
            out["certainty"] = "Certificate"
            out["requires_context"] = False
            out["blockers"] = list(top.blockers)
        else:
            out["certainty"] = "Hypothesis"
            out["requires_context"] = True
            out["blockers"] = list(top.blockers) + ["plain_match_ambiguous"]
        return out

    # Compound lookup
    comp = resolve_compound(surface, registry)
    if comp:
        head = comp["head"]
        out["found"] = True
        out["candidates"] = head.candidate_classes
        # compound: head يُحَدِّد الصَّنف لَكِنّ التَّحليل مُرَكَّب → ضَع certainty أَخفَض
        out["certainty"] = "Hypothesis" if head.certainty == "Certificate" else head.certainty
        out["requires_context"] = head.requires_context
        out["source"] = f"compound:{'+'.join(s['surface'] for s in comp['segments'])}"
        out["matched_entries"] = [head]
        out["blockers"] = ["compound_token"] + list(head.blockers)
        return out

    return out


def conflict_audit(registry: dict) -> list[dict]:
    """يَفحَص الـsurfaces الَّتي لَها candidates مُتَناقِضَة عَبر ملَفّات."""
    conflicts = []
    for surf, entries in registry["by_plain"].items():
        if len(entries) <= 1: continue
        all_candidates = set()
        for e in entries:
            all_candidates.update(e.candidate_classes)
        if len(all_candidates) > 1:
            conflicts.append({
                "plain_surface": surf,
                "sources": [e.source_id for e in entries],
                "candidates_union": sorted(all_candidates),
                "n_sources": len(entries),
            })
    return sorted(conflicts, key=lambda c: -c["n_sources"])


def save_registry(out_path: Path = OUT_REGISTRY):
    reg = build_registry()
    # Save flat entries to JSON
    serializable = {
        "n_entries": len(reg["entries"]),
        "n_unique_surfaces": len(reg["by_surface"]),
        "n_unique_plain": len(reg["by_plain"]),
        "entries": [asdict(e) for e in reg["entries"]],
    }
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    return reg


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Building registry from 02_mabniyat…\n")
    reg = save_registry()
    print(f"\n✓ Saved {OUT_REGISTRY}")
    print(f"  entries:          {len(reg['entries'])}")
    print(f"  unique surfaces:  {len(reg['by_surface'])}")
    print(f"  unique plain:     {len(reg['by_plain'])}")
    print()

    # Category distribution
    from collections import Counter
    cats = Counter(e.category for e in reg["entries"])
    print("By category:")
    for c, n in cats.most_common():
        print(f"  {c:<22s} {n}")
    print()

    # Conflict audit
    conflicts = conflict_audit(reg)
    print(f"Cross-source conflicts: {len(conflicts)}")
    for c in conflicts[:15]:
        print(f"  {c['plain_surface']:<15s}  candidates={c['candidates_union']}  "
              f"n_sources={c['n_sources']}")
    print()

    # Test lookups
    print("Sample resolutions:")
    for tok in ["هَذَا","الَّذِي","حَيْثُ","أَيْنَ","كَيْفَ","مَتَى",
                "لِمَاذَا","مَنْ","مَا","إِنَّ","يَا","نَعَمْ","لَمْ",
                "وَ","فِي","هُوَ","هَيْهَاتَ"]:
        es = resolve(tok, reg)
        if es:
            top = es[0]
            cands = top.candidate_classes
            ctx = " [needs_context]" if top.requires_context else ""
            print(f"  {tok:<14s} → {cands}{ctx} (priority={top.priority}, cert={top.certainty})")
        else:
            print(f"  {tok:<14s} → no match")
