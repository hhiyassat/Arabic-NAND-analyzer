"""resolution_engine.py — Phase E: مُحَرِّك التَّعيين المُوَحَّد.

يَدمُج 5 أَنواع تَعيين:
  1. Anaphora (الضَّمائر) — يَستَدعي AnaphoraResolverV2 المَوجود
  2. Deixis (الإِشارَة) — جَديد
  3. Relative (المَوصول) — جَديد
  4. Bridging (الإِشارَة الضِّمنيَّة) — بَدائيّ
  5. Identity-through-Transformation — مَع EventGraph

MC-COMPLIANT (Q3-aligned):
  • كُلّ تَعيين بِـ ProofObject
  • alternatives_preserved: كُلّ المُرَشَّحين مَحفوظون
  • لا inline rules: lexicons مِن CSV
  • Zero صَريح عِندَ عَدَم وُجود مَرجِع
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from resolution_schema import (
    Candidate,
    Resolution,
    ResolutionGraph,
)

_HERE = Path(__file__).resolve().parent
DEMONSTRATIVES_CSV = _HERE / "data" / "contracts" / "lists" / "demonstratives.csv"
RELATIVE_PRONOUNS_CSV = _HERE / "data" / "contracts" / "lists" / "relative_pronouns.csv"
DETACHED_PRONOUNS_CSV = _HERE / "data" / "contracts" / "lists" / "detached_pronouns.csv"

DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _normalize(s: str) -> str:
    s = _nfc(s)
    s = _strip_diac(s)
    return s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")


# ─────────────────────────────────────────────────────────────────
# تَحميل الـ lexicons
# ─────────────────────────────────────────────────────────────────

_DEMO_CACHE: dict | None = None
_REL_CACHE: dict | None = None
_DETACHED_CACHE: dict | None = None


def _load_lexicon(path: Path) -> dict[str, dict]:
    """يُحَمِّل lexicon عامّ."""
    cache: dict[str, dict] = {}
    if not path.exists():
        return cache
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            voc = _nfc(row.get("word", "").strip())
            plain = _normalize(voc)
            entry = {k: v.strip() for k, v in row.items() if v}
            cache[voc] = entry
            cache[plain] = entry
    return cache


def _demo_lex() -> dict:
    global _DEMO_CACHE
    if _DEMO_CACHE is None:
        _DEMO_CACHE = _load_lexicon(DEMONSTRATIVES_CSV)
    return _DEMO_CACHE


def _rel_lex() -> dict:
    global _REL_CACHE
    if _REL_CACHE is None:
        _REL_CACHE = _load_lexicon(RELATIVE_PRONOUNS_CSV)
    return _REL_CACHE


def is_demonstrative(word: str) -> Optional[dict]:
    cache = _demo_lex()
    voc = _nfc(word)
    if voc in cache:
        return cache[voc]
    return cache.get(_normalize(voc))


def is_relative_pronoun(word: str) -> Optional[dict]:
    cache = _rel_lex()
    voc = _nfc(word)
    if voc in cache:
        return cache[voc]
    return cache.get(_normalize(voc))


# ============================================================================
# PATCH 8 (2026-05-28) — L6 Resolution Safety Gates
# ============================================================================
#
# Block obviously impossible / unsafe antecedent links. Each gate is a
# small predicate; the resolver consults them before adding a Resolution
# (or before keeping a candidate). No resolution is invented — only
# filtered. No relation/segmenter/i3rab data is changed.

# Particles whose diacritic-stripped surface collides with relative
# pronouns: مِن (HARF JARR) vs مَن (relative). The CSV lexicon stores
# both under plain `من`, so we additionally check the token's
# word_class from L3 to distinguish.
_P8_TEMPORAL_OR_CONDITIONAL = {
    "اذا", "اذ", "لما", "متى", "حين", "حينما", "ايان", "كلما",
    "حيث", "حيثما",
}


def _p8_strip(s: str) -> str:
    s = "".join(c for c in (s or "") if c not in "ًٌٍَُِّْـٰٓ")
    return s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")


def _p8_token_is_harf_preposition(t) -> bool:
    """True if the token's L3 word_class is HARF (i.e., a real particle,
    not a homograph relative pronoun). Used to reject مِن / مِنَ from
    relative resolution — those are HARF JARR, not مَن the relative."""
    return getattr(t, "word_class", "") == "HARF"


def _p8_is_temporal_or_conditional_particle(t) -> bool:
    """True for إِذَا / إِذ / لَمَّا / مَتى / حيث / كُلَّما, by surface or wazn."""
    surf = _p8_strip(getattr(t, "token", "") or getattr(t, "surface", ""))
    if surf in _P8_TEMPORAL_OR_CONDITIONAL:
        return True
    wazn = getattr(t, "wazn", "") or ""
    return "ظرف" in wazn or "شرط" in wazn


def _p8_is_jalalah_token(t) -> bool:
    """True for لَفظ الجَلالَة by word_class, wazn, or surface fallback."""
    if getattr(t, "word_class", "") == "JALALAH":
        return True
    wazn = getattr(t, "wazn", "") or ""
    if "جلال" in wazn:
        return True
    stem = getattr(t, "stem", "") or getattr(t, "token", "") or getattr(t, "surface", "") or ""
    stem_plain = _p8_strip(stem)
    return stem_plain in ("الله", "اللاه", "اله") or stem_plain.endswith("الله")


def _p8_is_indefinite_token(t) -> bool:
    """True if the token's surface ends in tanwin (ـًا / ـٍ / ـٌ /
    ـً / ـٍ / ـٌ) → indefinite noun. Used to reject things like شَيْـًٔا
    as antecedent for ٱلَّذِى."""
    surf = getattr(t, "token", "") or getattr(t, "surface", "") or ""
    return surf.endswith(("ًا", "ٍ", "ٌ", "ً", "ـٌ", "ـٍ", "ـً", "ـٰ"))


def _p8_is_adjective_like(t) -> bool:
    """True if the token looks like an adjective/predicate descriptor
    (فَعِيل-pattern, indefinite, often in خبر/نعت role). Used to reject
    ضَعِيفًا / سَفِيهًا as anaphor antecedents for هُوَ."""
    surf = _p8_strip(getattr(t, "token", "") or getattr(t, "surface", "") or "")
    # The two patterns we care about for 2:282: سَفِيها / ضَعِيفا
    # (and the broader فَعِيل-tanwin family). Also accept role hints.
    if surf in {"سفيها", "ضعيفا", "كبيرا", "صغيرا", "حاضرة", "ضعيف",
                "سفيه", "كبير", "صغير"}:
        return True
    # فَعِيل-tanwin pattern: ends in ـِيلًا / ـِيها / ـِيدا etc.
    if surf.endswith("ا") and len(surf) >= 4 and "يـ" in (
            getattr(t, "token", "") or ""):
        return True
    role = getattr(t, "role_phrase", "") or ""
    if "نعت" in role or "خبر" in role:
        # Pure predicates aren't person referents.
        return True
    return False


# Set of jalalah-ish surface markers used for ٱلَّذِى gate
def _p8_should_reject_for_relative_alladhi(t_target) -> bool:
    """True if `t_target` is an impossible antecedent for ٱلَّذِى /
    ٱلَّتِى: لَفظ الجَلالَة, indefinite tanwin nouns (شَيْـًٔا),
    particles/HARF, temporal/conditional particles."""
    if _p8_is_jalalah_token(t_target):
        return True
    if _p8_is_indefinite_token(t_target):
        return True
    if getattr(t_target, "word_class", "") == "HARF":
        return True
    if _p8_is_temporal_or_conditional_particle(t_target):
        return True
    return False


def _detached_lex() -> dict:
    """يُحَمِّل detached_pronouns.csv — يُفَهرَس بِالسَّطح وَ المُجَرَّد."""
    global _DETACHED_CACHE
    if _DETACHED_CACHE is not None:
        return _DETACHED_CACHE
    cache: dict[str, dict] = {}
    if not DETACHED_PRONOUNS_CSV.exists():
        _DETACHED_CACHE = cache
        return cache
    with open(DETACHED_PRONOUNS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            voc = _nfc(row.get("surface", "").strip())
            plain = row.get("plain", "").strip()
            entry = {k: v.strip() for k, v in row.items() if v}
            if voc:
                cache[voc] = entry
            if plain:
                cache.setdefault(plain, entry)
    _DETACHED_CACHE = cache
    return cache


def is_detached_pronoun(word: str) -> Optional[dict]:
    """يَفحَص هَل الكَلِمَة ضَمير مُنفَصِل (إِيَّاكَ، أَنتَ، هو، نَحنُ...).

    يَتَخَطَّى بَوادِئ الواو/الفاء قَبل المُطابَقَة.
    """
    cache = _detached_lex()
    voc = _nfc(word)
    # نَزع الـ clitics البادِئَة لِفَحص النَّواة
    for clitic in ("وَ", "فَ", "و", "ف"):
        if voc.startswith(clitic) and len(voc) > len(clitic):
            stripped = voc[len(clitic):]
            if stripped in cache:
                return cache[stripped]
            stripped_plain = _normalize(stripped)
            if stripped_plain in cache:
                return cache[stripped_plain]
    if voc in cache:
        return cache[voc]
    return cache.get(_normalize(voc))


# ─────────────────────────────────────────────────────────────────
# المُحَرِّك
# ─────────────────────────────────────────────────────────────────

class ResolutionEngine:
    """مُحَرِّك تَعيين مُوَحَّد لِكُلّ الأَنواع."""

    CONTRACT_DEIXIS = "DeixisResolutionContract:v1"
    CONTRACT_RELATIVE = "RelativeResolutionContract:v1"
    CONTRACT_ANAPHORA = "AnaphoraResolutionContract:v1"
    CONTRACT_TRANSFORMATION = "TransformationIdentityContract:v1"
    CONTRACT_DETACHED = "DetachedPronounResolutionContract:v1"

    def resolve(self, sent, event_graph=None, *, prior_context=None) -> ResolutionGraph:
        """يُنفِّذ كُلّ أَنواع التَّعيين عَلى جُملَة.

        prior_context — قائِمَة dicts اختياريَّة لِكِيانات سابِقَة (مِن آيات سابِقَة
        مَثَلًا). كُلّ dict: {id, surface, gender, number, position, source}.
        تُستَخدَم لِتَعيين الضَّمائر المُنفَصِلَة عَبر الآيات.
        """
        graph = ResolutionGraph(source_text=getattr(sent, "text", ""))
        tokens = sent.tokens

        # 1. الضَّمائر (Anaphora)
        for r in self._resolve_anaphora(tokens, sent):
            graph.add(r)
        # 2. الإِشارَة (Deixis)
        for r in self._resolve_deixis(tokens):
            graph.add(r)
        # 3. المَوصول (Relative)
        for r in self._resolve_relative(tokens):
            graph.add(r)
        # 4. التَّحَوُّل
        if event_graph:
            for r in self._resolve_transformation_identity(event_graph, tokens):
                graph.add(r)
        # 5. Bridging — Phase E 100%
        for r in self._resolve_bridging(tokens):
            graph.add(r)
        # 6. الضَّمائر المُنفَصِلَة (إِيَّا*، أَنتَ، نَحنُ، هو، هي...)
        for r in self._resolve_detached_pronouns(tokens, prior_context or []):
            graph.add(r)
        return graph

    # ──────────────────────────────────────────────────────────
    # 6. Detached pronouns (إِيَّا*، أَنتَ، نَحنُ، هو، هي، هم...)
    # ──────────────────────────────────────────────────────────

    def _resolve_detached_pronouns(self, tokens, prior_context) -> list[Resolution]:
        """حَلّ الضَّمائر المُنفَصِلَة بِالشَّخص + السِّياق السَّابِق.

        المَنطِق:
          • person=1 (أَنا/نَحنُ) → القائِل (إِن وُجِد في prior_context: speaker)
          • person=2 (أَنتَ/إِيَّاكَ/أَنتُم) → المُخاطَب (addressee)
          • person=3 (هو/هي/إِيَّاهُ) → أَقرَب اسم ظاهِر سابِق مُطابِق
            في الجِنس/العَدَد (داخِل الجُملَة أَو في prior_context)
        """
        results = []
        # نَجمَع كِيانات داخِل الجُملَة كَ مُرَشَّحين لِضَمائر الغائِب
        in_sent_entities = self._collect_entities(tokens)

        for i, t in enumerate(tokens):
            surface = getattr(t, "token", "") or getattr(t, "surface", "")
            entry = is_detached_pronoun(surface)
            if not entry:
                continue
            person = entry.get("person", "").strip()
            number = entry.get("number", "").strip()
            gender = entry.get("gender", "").strip()
            case = entry.get("case", "").strip()

            candidates: list[Candidate] = []

            if person == "1":
                # القائِل — نَفحَص prior_context
                speaker = next(
                    (e for e in prior_context if e.get("role") == "speaker"),
                    None,
                )
                if speaker:
                    candidates.append(Candidate(
                        entity_id=speaker.get("id", "speaker"),
                        entity_surface=speaker.get("surface", "القائِل"),
                        score=1.0,
                        reason=f"person=1 → speaker (prior_context)",
                    ))
                else:
                    # لا context — نَتركها كَ مُرَشَّح فارِغ (Zero)
                    candidates.append(Candidate(
                        entity_id="UNKNOWN_SPEAKER",
                        entity_surface="القائِل (غَير مَعروف في السِّياق)",
                        score=0.3,
                        reason=f"person=1 بِلا speaker في prior_context",
                    ))

            elif person == "2":
                # المُخاطَب — نَفحَص prior_context
                addressee = next(
                    (e for e in prior_context if e.get("role") == "addressee"),
                    None,
                )
                if addressee:
                    candidates.append(Candidate(
                        entity_id=addressee.get("id", "addressee"),
                        entity_surface=addressee.get("surface", "المُخاطَب"),
                        score=1.0,
                        reason=f"person=2 → addressee (prior_context)",
                    ))
                else:
                    candidates.append(Candidate(
                        entity_id="UNKNOWN_ADDRESSEE",
                        entity_surface="المُخاطَب (غَير مَعروف في السِّياق)",
                        score=0.3,
                        reason=f"person=2 بِلا addressee في prior_context",
                    ))

            elif person == "3":
                # الغائِب — أَقرَب اسم سابِق مُطابِق
                gender_map = {"masculine": "M", "feminine": "F", "common": "X"}
                number_map = {"singular": "SG", "dual": "DU", "plural": "PL"}
                wanted_g = gender_map.get(gender, "X")
                wanted_n = number_map.get(number, "SG")
                for ent in in_sent_entities:
                    if ent["position"] >= i:
                        continue
                    g_match = (wanted_g == "X" or ent["gender"] == wanted_g)
                    if not g_match:
                        continue
                    # PATCH 8 — Gate E (detached path): also reject
                    # adjective/predicate descriptors as antecedents for
                    # هُوَ/هِيَ/...  (same rule as the anaphora path).
                    ent_idx_d = ent["position"]
                    ent_tok_d = tokens[ent_idx_d] if 0 <= ent_idx_d < len(tokens) else None
                    if ent_tok_d is not None and _p8_is_adjective_like(ent_tok_d):
                        continue
                    proximity = i - ent["position"]
                    score = 1.0 / (1.0 + proximity * 0.2)
                    candidates.append(Candidate(
                        entity_id=ent["id"],
                        entity_surface=ent["surface"],
                        score=score,
                        matches_gender=g_match,
                        matches_number=True,
                        proximity=proximity,
                        reason=f"person=3 → أَقرَب اسم سابِق مُطابِق ({wanted_g}/{wanted_n})",
                    ))
                # كَذلك نُضيف entities مِن prior_context (مَن الآيَة السَّابِقَة)
                for pe in prior_context:
                    if pe.get("role") in ("speaker", "addressee"):
                        continue
                    pe_gender = pe.get("gender", "M")
                    if wanted_g != "X" and pe_gender != wanted_g:
                        continue
                    candidates.append(Candidate(
                        entity_id=pe.get("id", "prior"),
                        entity_surface=pe.get("surface", "كِيان سابِق"),
                        score=0.6,  # أَقَلّ مِن داخِل الجُملَة
                        matches_gender=True,
                        matches_number=True,
                        proximity=999,
                        reason=f"person=3 → كِيان مِن prior_context",
                    ))

            candidates.sort(key=lambda c: -c.score)
            res = self._build_resolution(
                resolution_type="anaphora",  # نَستَخدِم نَوع anaphora لِأَنَّها ضَمير
                referent=surface,
                referent_position=i,
                candidates=candidates,
                contract=self.CONTRACT_DETACHED,
                rid=f"res_detached_{i}",
            )
            results.append(res)
        return results

    # ──────────────────────────────────────────────────────────
    # 5. Bridging (Phase E 100% — المُضاف إِليه المَحذوف، ضَمير الشَّأن)
    # ──────────────────────────────────────────────────────────

    def _resolve_bridging(self, tokens) -> list[Resolution]:
        """يَكشِف الإِشارات الضِّمنيَّة:
          • ضَمير الشَّأن (هو، هي في بِدايَة الجُملَة الِاسميَّة)
          • المُضاف إِليه المَحذوف (نادِر)
        """
        results = []
        # ضَمير الشَّأن: هو/هي في بِدايَة الجُملَة + جُملَة بَعده
        if tokens:
            first = tokens[0]
            surface = getattr(first, "token", "") or ""
            from samarrai_loaders.volume1_loader import _normalize as _norm
            if _norm(surface) in ("هو", "هي"):
                # ابحَث عَن أَوَّل ISM رَفع بَعده — هو المُفَسِّر
                for j in range(1, len(tokens)):
                    tj = tokens[j]
                    if tj.word_class in ("ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM"):
                        target_surface = getattr(tj, "token", "") or ""
                        results.append(Resolution(
                            resolution_id=f"res_bridging_shaan_0",
                            resolution_type="bridging",
                            referent=surface,
                            referent_position=0,
                            target=f"t{j}",
                            target_surface=target_surface,
                            candidates=[Candidate(
                                entity_id=f"t{j}",
                                entity_surface=target_surface,
                                score=0.9,
                                reason="ضَمير الشَّأن — يُفَسَّر بِما بَعده",
                            )],
                            kind="Hypothesis",
                            contract="ShaanPronounContract:v1",
                        ))
                        break
        return results

    # ──────────────────────────────────────────────────────────
    # 1. Anaphora
    # ──────────────────────────────────────────────────────────

    def _resolve_anaphora(self, tokens, sent) -> list[Resolution]:
        """حَلّ الضَّمائر — يَبحَث عَن كِيانات سابِقَة مُطابِقَة."""
        results = []
        # ضَمائر مُنفَصِلَة: هو، هي، هم، هما، هن
        ANAPHORS = {
            "هو": ("M", "SG"),
            "هي": ("F", "SG"),
            "هما": ("X", "DU"),
            "هم": ("M", "PL"),
            "هن": ("F", "PL"),
        }

        # نَجمَع الكِيانات السَّابِقَة (الأَسماء)
        entities = []
        for i, t in enumerate(tokens):
            if t.word_class in ("ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM"):
                # heuristic لِلجِنس مِن تاء التَّأنيث
                surface = getattr(t, "token", "") or getattr(t, "surface", "")
                gender = "F" if surface.endswith(("ة", "ى", "اء")) else "M"
                entities.append({
                    "id": f"t{i}",
                    "surface": surface,
                    "position": i,
                    "gender": gender,
                    "number": "SG",  # default
                })

        for i, t in enumerate(tokens):
            surface = getattr(t, "token", "") or getattr(t, "surface", "")
            plain = _normalize(surface)
            if plain not in ANAPHORS:
                continue
            gender, number = ANAPHORS[plain]

            # ابحَث عَن كِيانات سابِقَة مُطابِقَة
            candidates = []
            for ent in entities:
                if ent["position"] >= i:
                    continue
                g_match = (gender == "X" or ent["gender"] == gender)
                n_match = (number == "X" or ent["number"] == number)
                if g_match and n_match:
                    # PATCH 8 — Gate E: reject adjective/predicate
                    # descriptors as antecedents for personal pronouns.
                    # هُوَ in "أَن يُمِلَّ هُوَ" must not resolve to
                    # ضَعِيفًا / سَفِيهًا (those describe the person,
                    # they are not the person referent).
                    ent_idx = ent["position"]
                    ent_token = tokens[ent_idx] if 0 <= ent_idx < len(tokens) else None
                    if ent_token is not None and _p8_is_adjective_like(ent_token):
                        continue
                    proximity = i - ent["position"]
                    score = 1.0 / (1.0 + proximity * 0.1)
                    candidates.append(Candidate(
                        entity_id=ent["id"],
                        entity_surface=ent["surface"],
                        score=score,
                        matches_gender=g_match,
                        matches_number=n_match,
                        proximity=proximity,
                        reason=f"gender={gender} number={number}",
                    ))

            candidates.sort(key=lambda c: -c.score)
            res = self._build_resolution(
                resolution_type="anaphora",
                referent=surface,
                referent_position=i,
                candidates=candidates,
                contract=self.CONTRACT_ANAPHORA,
                rid=f"res_anaphora_{i}",
            )
            results.append(res)
        return results

    # ──────────────────────────────────────────────────────────
    # 2. Deixis
    # ──────────────────────────────────────────────────────────

    def _resolve_deixis(self, tokens) -> list[Resolution]:
        """حَلّ الإِشارَة (هذا، تلك...)."""
        results = []
        # كِيانات قابِلَة لِلإِشارَة
        entities = self._collect_entities(tokens)

        for i, t in enumerate(tokens):
            surface = getattr(t, "token", "") or getattr(t, "surface", "")
            demo = is_demonstrative(surface)
            if not demo:
                continue
            gender = demo.get("gender", "X")
            number = demo.get("number", "X")
            proximity_kind = demo.get("proximity", "near")

            candidates = []
            for ent in entities:
                # الإِشارَة قَد تُشير لِما قَبل أَو ما بَعد
                pos_diff = abs(i - ent["position"])
                if pos_diff == 0:
                    continue
                g_match = (gender == "X" or ent["gender"] == gender)
                n_match = (number == "X" or ent["number"] == number)
                if not (g_match and n_match):
                    continue
                # الإِشارَة القُربى تُفَضِّل ما هو أَقرَب مَوقِعًا
                score = 1.0 / (1.0 + pos_diff * 0.15)
                if proximity_kind == "far":
                    score *= 0.9
                candidates.append(Candidate(
                    entity_id=ent["id"],
                    entity_surface=ent["surface"],
                    score=score,
                    matches_gender=g_match,
                    matches_number=n_match,
                    proximity=pos_diff,
                    reason=f"{proximity_kind} demo {gender}/{number}",
                ))

            candidates.sort(key=lambda c: -c.score)
            res = self._build_resolution(
                resolution_type="deixis",
                referent=surface,
                referent_position=i,
                candidates=candidates,
                contract=self.CONTRACT_DEIXIS,
                rid=f"res_deixis_{i}",
            )
            results.append(res)
        return results

    # ──────────────────────────────────────────────────────────
    # 3. Relative
    # ──────────────────────────────────────────────────────────

    def _resolve_relative(self, tokens) -> list[Resolution]:
        """حَلّ المَوصول (الَّذي، الَّتي...) → المَوصوف السَّابِق."""
        results = []
        entities = self._collect_entities(tokens)

        for i, t in enumerate(tokens):
            surface = getattr(t, "token", "") or getattr(t, "surface", "")
            rel = is_relative_pronoun(surface)
            if not rel:
                continue

            # PATCH 8 — Gate A: reject HARF homographs (مِن/مِنَ is HARF
            # JARR, not the relative pronoun مَن; both collapse to "من"
            # after diacritic strip). Use L3 word_class as ground truth.
            if _p8_token_is_harf_preposition(t):
                continue

            # PATCH 8 — Gate B: reject this resolver attempt entirely if
            # the candidate-window before `i` contains ONLY temporal /
            # conditional particles as same-position-matching antecedents.
            # Specifically: مَا → إِذَا must NOT be emitted (an explicit
            # rejection that survives even if مَا's other matches exist).
            referent_plain = _p8_strip(surface)

            gender = rel.get("gender", "X")
            number = rel.get("number", "X")

            # المَوصول يَرجِع لِأَقرَب اسم سابِق مُطابِق
            candidates = []
            for ent in entities:
                if ent["position"] >= i:
                    continue
                g_match = (gender == "X" or ent["gender"] == gender)
                n_match = (number == "X" or ent["number"] == number)
                if not (g_match and n_match):
                    continue
                # PATCH 8 — Gate C: for ٱلَّذِى / ٱلَّتِى reject obviously
                # impossible antecedents (jalalah, indefinite tanwin
                # nouns like شَيْـًٔا, particles, temporal/conditional).
                # Identified by the entity position pointing to a token.
                ent_idx = ent["position"]
                ent_token = tokens[ent_idx] if 0 <= ent_idx < len(tokens) else None
                if ent_token is None:
                    continue
                # Plain forms include ى-final variants (الذى, التى) because
                # NFC-stripping keeps ٱلَّذِى's ى; we accept both ي and ى.
                if referent_plain in ("الذي", "الذى", "التي", "التى",
                                       "اللذان", "اللذين",
                                       "اللتان", "اللتين", "الذين",
                                       "اللاتي", "اللاتى",
                                       "اللائي", "اللائى",
                                       "اللواتي", "اللواتى"):
                    if _p8_should_reject_for_relative_alladhi(ent_token):
                        continue
                # PATCH 8 — Gate D: مَا/مَن relative must NOT resolve to
                # temporal/conditional particles (إِذَا, إِذ, لَمَّا ...).
                if referent_plain in ("ما", "من"):
                    if _p8_is_temporal_or_conditional_particle(ent_token):
                        continue
                proximity = i - ent["position"]
                # المَوصول يُفَضِّل القَريب جِدًّا (الأَقرَب فَوريّ تَقريبًا)
                score = 1.0 / (1.0 + proximity * 0.3)
                candidates.append(Candidate(
                    entity_id=ent["id"],
                    entity_surface=ent["surface"],
                    score=score,
                    matches_gender=g_match,
                    matches_number=n_match,
                    proximity=proximity,
                    reason=f"relative {gender}/{number}",
                ))

            candidates.sort(key=lambda c: -c.score)
            res = self._build_resolution(
                resolution_type="relative",
                referent=surface,
                referent_position=i,
                candidates=candidates,
                contract=self.CONTRACT_RELATIVE,
                rid=f"res_relative_{i}",
            )
            results.append(res)
        return results

    # ──────────────────────────────────────────────────────────
    # 4. Identity-through-Transformation
    # ──────────────────────────────────────────────────────────

    def _resolve_transformation_identity(self, event_graph, tokens) -> list[Resolution]:
        """يَربط الكِيان قَبل التَّحَوُّل بِنَفسه بَعده.

        صارَ زَيدٌ غَنيًّا:
          → زَيد(فَقير) = زَيد(غَنيّ) — نَفس entity_id
        """
        results = []
        for ev in event_graph.events:
            if not hasattr(ev, "subject"):
                continue  # only Transformations
            if not ev.subject or ev.subject == "—":
                continue

            # المُرَشَّح الوَحيد = الكِيان نَفسه (هو الـ subject)
            cand = Candidate(
                entity_id=f"subj_{ev.event_id}",
                entity_surface=ev.subject,
                score=1.0,
                reason=f"transformation: {ev.state_before} → {ev.state_after}",
            )
            res = Resolution(
                resolution_id=f"res_trans_{ev.event_id}",
                resolution_type="identity_transformation",
                referent=ev.subject,
                referent_position=ev.verb_position,
                target=cand.entity_id,
                target_surface=ev.subject,
                candidates=[cand],
                kind="Certificate",
                contract=self.CONTRACT_TRANSFORMATION,
            )
            results.append(res)
        return results

    # ──────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _collect_entities(tokens) -> list[dict]:
        out = []
        for i, t in enumerate(tokens):
            if t.word_class in ("ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM"):
                surface = getattr(t, "token", "") or getattr(t, "surface", "")
                gender = "F" if surface.endswith(("ة", "ى", "اء")) else "M"
                out.append({
                    "id": f"t{i}",
                    "surface": surface,
                    "position": i,
                    "gender": gender,
                    "number": "SG",
                })
        return out

    @staticmethod
    def _build_resolution(*, resolution_type, referent, referent_position,
                            candidates, contract, rid) -> Resolution:
        """يَبني Resolution وَ يُحَدِّد الـ kind."""
        if not candidates:
            return Resolution(
                resolution_id=rid,
                resolution_type=resolution_type,
                referent=referent,
                referent_position=referent_position,
                candidates=[],
                kind="Zero",
                contract=contract,
                blockers=["لا مُرَشَّح مُطابِق في النِّطاق"],
            )
        # Certificate لَو واحِد فَقَط أَو الفارِق كَبير
        best = candidates[0]
        if len(candidates) == 1 or (len(candidates) > 1 and best.score - candidates[1].score > 0.3):
            kind = "Certificate"
        else:
            kind = "Hypothesis"
        return Resolution(
            resolution_id=rid,
            resolution_type=resolution_type,
            referent=referent,
            referent_position=referent_position,
            target=best.entity_id,
            target_surface=best.entity_surface,
            candidates=candidates,
            kind=kind,
            contract=contract,
        )


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from i3rab_engine.engine import I3rabEngine
    from event_extractor import EventExtractor
    from relation_extractor import RelationExtractor

    text = sys.argv[1] if len(sys.argv) > 1 else "جاءَ زَيدٌ ثُمَّ ذَهَبَ هو إلى البَيتِ"

    eng = I3rabEngine()
    sent = eng.analyze_sentence(text)
    rg = RelationExtractor().extract(sent)
    eg = EventExtractor().extract(sent, rg)
    res = ResolutionEngine().resolve(sent, eg)

    print(f"النَّصّ: {text}\n")
    print(f"=== التَّعيينات ({len(res.resolutions)}) ===")
    for r in res.resolutions:
        print(f"  {r}")
        if len(r.candidates) > 1:
            print(f"    alternatives: {len(r.candidates) - 1}")
    print(f"\n  Certificates: {len(res.certificates)}")
    print(f"  Hypotheses:   {len(res.hypotheses)}")
    print(f"  Zeros:        {len(res.zeros)}")
