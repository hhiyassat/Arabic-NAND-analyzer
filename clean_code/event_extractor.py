"""event_extractor.py — Phase D: استِخراج Events وَ Transformations مِن RelationGraph.

MC-COMPLIANT:
  • قاعِدَة الأَفعال التَّحَوُّليَّة في `transformation_verbs.csv` — لا inline
  • كُلّ Event/Transformation يَحوي ProofObject metadata
  • النِّيَّة: لا تَفسير، لا حُكم — استِخراج بُنيَويّ فَقَط

يَأخُذ:
  • SentenceI3rab مِن i3rab_engine
  • RelationGraph مِن relation_extractor (اختياريّ — يُعَزِّز الدِّقَّة)

يُرجِع:
  • EventGraph مَع كُلّ الأَحداث + التَّحَوُّلات
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from event_schema import Event, EventGraph, Transformation

_HERE = Path(__file__).resolve().parent
TRANSFORMATION_VERBS_CSV = _HERE / "data" / "contracts" / "lists" / "transformation_verbs.csv"
TIME_ADVERBS_CSV = _HERE / "data" / "contracts" / "lists" / "time_adverbs.csv"

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
# تَحميل الأَفعال التَّحَوُّليَّة (MC: مِن CSV)
# ─────────────────────────────────────────────────────────────────

_TRANSFORMATION_CACHE: dict | None = None


def _load_transformation_verbs() -> dict[str, dict]:
    """يُحَمِّل verbs lexicon بِـ index: verb_plain → entry."""
    global _TRANSFORMATION_CACHE
    if _TRANSFORMATION_CACHE is not None:
        return _TRANSFORMATION_CACHE
    cache: dict[str, dict] = {}
    if not TRANSFORMATION_VERBS_CSV.exists():
        raise RuntimeError(
            f"Zero: لَم نَجِد {TRANSFORMATION_VERBS_CSV}. MC: لا inline fallback."
        )
    with open(TRANSFORMATION_VERBS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            voc = _nfc(row.get("verb_lemma", "").strip())
            plain = _normalize(voc)
            entry = {
                "verb_lemma": voc,
                "verb_plain": plain,
                "root": row.get("root", "").strip(),
                "transformation_kind": row.get("transformation_kind", "general").strip(),
                "state_before": row.get("state_before", "—").strip(),
                "state_after": row.get("state_after", "—").strip(),
                "description": row.get("description", "").strip(),
            }
            cache[voc] = entry
            cache[plain] = entry
    _TRANSFORMATION_CACHE = cache
    return cache


def is_transformation_verb(verb: str) -> Optional[dict]:
    """يَفحَص هَل الفِعل تَحَوُّليّ + يُرجِع entry لَو نَعَم."""
    cache = _load_transformation_verbs()
    voc = _nfc(verb)
    if voc in cache:
        return cache[voc]
    plain = _normalize(voc)
    return cache.get(plain)


# ─────────────────────────────────────────────────────────────────
# Time adverbs lexicon
# ─────────────────────────────────────────────────────────────────

_TIME_CACHE: dict | None = None


def _load_time_adverbs() -> dict[str, dict]:
    global _TIME_CACHE
    if _TIME_CACHE is not None:
        return _TIME_CACHE
    cache: dict[str, dict] = {}
    if not TIME_ADVERBS_CSV.exists():
        _TIME_CACHE = cache
        return cache
    with open(TIME_ADVERBS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            voc = _nfc(row.get("word", "").strip())
            plain = _normalize(voc)
            entry = {
                "word": voc,
                "category": row.get("time_category", "").strip(),
                "value": row.get("time_value", "").strip(),
                "description": row.get("description", "").strip(),
            }
            cache[voc] = entry
            cache[plain] = entry
    _TIME_CACHE = cache
    return cache


def is_time_adverb(word: str) -> Optional[dict]:
    cache = _load_time_adverbs()
    voc = _nfc(word)
    if voc in cache:
        return cache[voc]
    plain = _normalize(voc)
    return cache.get(plain)


# ─────────────────────────────────────────────────────────────────
# PATCH 5 (2026-05-27) — TimeScopeGate + CommandLamEventMood helpers
# ─────────────────────────────────────────────────────────────────

# Quranic / standard pause marks that bound a clause for time-scope
# purposes. A time-adverb cannot project its time_value across one of
# these markers. NFC-normalized.
_CLAUSE_BREAK_CHARS = {
    "ۖ", "ۗ", "ۘ", "ۙ", "ۚ", "ۛ",  # ۖ ۗ ۘ ۙ ۚ ۛ
    "ۜ", "۝", "۞",                                  # ۜ ۝ ۞
    "،", "؛", ".", "؟", "!",
}


def _is_clause_break(token_surface: str) -> bool:
    """True if the token is purely punctuation/pause that ends a clause."""
    if not token_surface:
        return False
    s = _nfc(token_surface).strip()
    if not s:
        return False
    return all(ch in _CLAUSE_BREAK_CHARS for ch in s)


def _build_pause_before(sent_text: str, tokens) -> set[int]:
    """Return a set of token indices `i` such that a clause-break
    pause-mark appears in `sent_text` immediately before tokens[i].

    Needed because the i3rab tokenizer drops pause marks before they
    reach `sent.tokens`, so we recover that information by walking
    `sent.text` whitespace-split pieces and aligning them to tokens.
    """
    pause_before: set[int] = set()
    if not sent_text or not tokens:
        return pause_before
    pieces = _nfc(sent_text).split()
    # Token surfaces (NFC-normalized) in order
    token_surfaces = [
        _nfc(getattr(t, "token", "") or getattr(t, "surface", "")) for t in tokens
    ]
    ti = 0  # cursor into tokens
    seen_pause = False
    for piece in pieces:
        # Pure pause/punctuation piece? mark next token as pause-preceded
        if all(ch in _CLAUSE_BREAK_CHARS for ch in piece) and piece:
            seen_pause = True
            continue
        # Otherwise this piece should match the next token surface. If
        # alignment drifts (the tokenizer may merge/split differently)
        # we just continue; mis-alignment only weakens the gate, never
        # over-filters time_values.
        if ti < len(token_surfaces) and piece == token_surfaces[ti]:
            if seen_pause:
                pause_before.add(ti)
                seen_pause = False
            ti += 1
        else:
            # Try to advance ti past any tokens that don't match (rare).
            # If we skip tokens here, we lose pause info for them — but
            # the conservative outcome (no time_value) is fine.
            if ti < len(token_surfaces):
                ti += 1
    return pause_before


def _find_scoped_time_value(tokens, verb_idx: int,
                             pause_before: set[int]) -> Optional[str]:
    """PATCH 5 — TimeScopeGate.

    Walk left from `verb_idx` looking for a time-adverb. Stop when we
    cross a pause-mark boundary (any index k where k ∈ pause_before
    while we're scanning back from verb_idx to k). If a time-adverb
    is found within the unbroken left-window, return its time_value;
    otherwise None.

    This replaces the previous global `sentence_time_value` default
    (which attached the same time_value to every event in the verse,
    including past events outside the إذا scope).
    """
    for j in range(verb_idx, 0, -1):
        # Crossing into token j means stepping from j to j-1; if j is
        # marked as preceded by a pause, the scope ends here.
        if j in pause_before:
            return None
        tj = tokens[j - 1]
        tw = getattr(tj, "token", "") or getattr(tj, "surface", "")
        if _is_clause_break(tw):
            return None
        entry = is_time_adverb(tw)
        if entry:
            return entry.get("value") or None
    return None


def _detect_command_lam_mood(token) -> tuple[str, str]:
    """PATCH 5 — CommandLamEventMood.

    If the verb token carries LAM_AL_AMR in its production-path prefix
    tags, return (mood, speech_act) = ("jussive_command", "command").
    Otherwise return ("", "").

    The prefix tags are set by the segmenter (PATCH 1) — this function
    only READS them; no segmentation change.
    """
    prefixes = getattr(token, "prefixes", None) or []
    # Token may carry parallel prefix_tags via i3rab pipeline; fall back
    # to inferring from prefix forms if tags missing.
    prefix_tags = getattr(token, "prefix_tags", None) or []
    if "LAM_AL_AMR" in prefix_tags:
        return "jussive_command", "command"
    # Fallback: re-segment via production segmenter on the surface form
    # (used when the i3rab token doesn't carry prefix_tags explicitly).
    surface = getattr(token, "token", "") or getattr(token, "surface", "")
    if surface:
        try:
            from segmenter import segment as _segment  # type: ignore
            seg = _segment(surface, normalize_input=True)
            if "LAM_AL_AMR" in (seg.prefix_tags or []):
                return "jussive_command", "command"
        except Exception:
            pass
    return "", ""


# ─────────────────────────────────────────────────────────────────
# Tense detection (مِن صيغَة الفِعل)
# ─────────────────────────────────────────────────────────────────

def detect_tense(token) -> str:
    """يَكشِف الزَّمَن مِن نَوع الفِعل في الـ token (rule-based).

    تَرتيب الأَدِلَّة (أَقواها أَوَّلًا):
      1. lexicon: explicit_verbs_lexicon.csv → aspect (PV/IV/CV)
      2. morph_tag: PV / IV / IMPERF_PREF / CV
      3. role_phrase: ماض / مضارع / أمر
      4. surface heuristics (مَع شُروط دَقيقَة لا تَخلِط
         بَين ماضي + أَ-بادِئة وَ مُضارِع 1st sg):
           • نِهايَة ـوا → past plural
           • نِهايَة ـنَا/ـنا → past 1st pl
           • نِهايَة ـتُ/ـتَ/ـتِ/ـتُمْ/ـتُمَا/ـتُنَّ → past addressee/speaker
           • نِهايَة ـتْ بِسُكون → past 3rd sg fem
           • بادِئة ٱسـ/ٱفـ/اسـ + سُكون → command (imperative form VIII/I)
           • بادِئة يَ/تَ/نَ + سُكون عَلى الفاء → present
           • بادِئة أَ + سُكون عَلى الفاء → present 1st sg أَفْعَل
             لَكِن نِهايَة ـَ صَريحَة → past Form IV (أَرْسَلَ)
    """
    word_class = getattr(token, "word_class", "")
    tag = getattr(token, "morph_tag", "") or ""
    surface = getattr(token, "token", "") or getattr(token, "surface", "")
    role = getattr(token, "role_phrase", "") or ""

    # 1. lexicon lookup (الأَقوى — مَصدَر صَريح في CSV)
    try:
        from explicit_verbs_contract import get_verb_info  # type: ignore
        info = get_verb_info(surface) if surface else None
        if info:
            aspect = (info.get("aspect") or "").strip()
            if aspect == "PV":
                return "past"
            if aspect == "IV":
                return "present"
            if aspect == "CV":
                return "command"
    except Exception:
        pass

    # 2. morph_tag (صَريح إِن وُجِد)
    if tag == "PV" or "ماض" in role:
        return "past"
    if tag in ("IV", "IMPERF_PREF") or "مضارع" in role:
        return "present"
    if tag == "CV" or "أمر" in role:
        return "command"

    # 3. surface heuristics — لا نَستَخدِمها إِلّا لِـ FIIL
    if word_class != "FIIL":
        return "unknown"
    s = surface
    plain = "".join(c for c in s if c not in DIACRITICS)
    # تَطبيع آ/ٱ/أ/إ → ا لِمُطابَقَة لاحِقَة ـنا حَتَّى لَو كُتِبَت ـنآ
    plain = plain.replace("آ", "ا").replace("ٱ", "ا")

    # 3.a نِهايَة ـوا → past plural (أَكَلُوا، ٱتَّخَذُوا، كَذَّبُوا)
    if plain.endswith("وا"):
        return "past"
    # 3.b ـنا → past 1st pl (أَخَذْنَا، أَرْسَلْنَا، خَلَقْنَا، بَعَثْنَا)
    if plain.endswith("نا"):
        return "past"
    # 3.c ـتُ/ـتَ/ـتِ/ـتُمْ/ـتُنَّ/ـتُمَا → past speaker/addressee
    for sfx in ("تم","تما","تن","ت"):
        if plain.endswith(sfx):
            # تَأَكَّد أَنّ التاء بِسُكون أَو حَرَكَة لا مُضارَعَة (لَيست تَ-بادِئة)
            if not s.startswith(("تَ","تُ","تِ")):
                return "past"
            # حَتَّى لَو بَدَأ بِـ تَ/تُ/تِ، إِذا انتَهى بِـ ـتُمْ/ـتُمَا → past
            if plain.endswith(("تم","تما")):
                return "past"
    # 3.d بادِئة ٱ هَمزَة وَصل + سُكون → command (form VIII / I imperative)
    if s.startswith(("ٱ","ا")) and len(s) >= 3 and s[2] == "ْ":
        return "command"

    # 3.e بادِئة يَ/تَ/نَ + سُكون عَلى الفاء → present (مُضارِع)
    # مَثَل: يَكْتُبُ، تَنزِلُ، نَعْبُدُ
    if s.startswith(("يَ","يُ","تَ","تُ","نَ","نُ")):
        # نِهايَة ـوا فُحِصَت أَعلاه؛ هُنا نَحن مَع مُفرَد/جَمع غَير ـوا
        return "present"

    # 3.f بادِئة أَ + سُكون عَلى الفاء — يَحتاج تَمييز:
    #   ماضٍ Form IV (أَرْسَلَ): يَنتَهي بِفَتحَة عَلى آخِر حَرف
    #   مُضارِع 1st sg أَفْعَل: يَنتَهي بِضَمَّة/سُكون
    if s.startswith(("أَ","أُ")) and "ْ" in s[:5]:
        # نِهايَة بِفَتحَة عَلى آخِر حَرف → ماضٍ
        if s.rstrip("ٰۚۖ").endswith("َ"):
            return "past"
        # نِهايَة بِضَمَّة → مُضارِع 1st sg
        if s.rstrip("ٰۚۖ").endswith("ُ"):
            return "present"
        return "unknown"
    return "unknown"


# ─────────────────────────────────────────────────────────────────
# المُستَخرِج
# ─────────────────────────────────────────────────────────────────

class EventExtractor:
    """يَستَخرِج Events وَ Transformations مِن جُملَة مُعرَبَة."""

    CONTRACT = "EventExtractor:v1"

    def extract(self, sent, relation_graph=None) -> EventGraph:
        """يَستَخرِج EventGraph مِن SentenceI3rab + RelationGraph اختياريّ.

        Detection strategy (MC):
          1. أَيّ token مَع word_class = FIIL → Event
          2. أَيّ token الـ surface فيه في transformation_verbs.csv → Transformation
             (يَتَجاوَز خَطَأ i3rab في تَصنيف صارَ/أَصبَحَ كَ HARF)
        """
        graph = EventGraph(source_text=getattr(sent, "text", ""))
        tokens = sent.tokens

        # PATCH 5 (2026-05-27) — TimeScopeGate.
        # The previous behavior found the FIRST time-adverb in the verse
        # and attached its time_value to EVERY event (sentence-global).
        # That made past events like تَدَايَنتُم / عَلَّمَهُ / دُعُوا /
        # تَبَايَعْتُمْ all surface as time=when_future just because the
        # verse opens with إِذَا. PATCH 5 replaces the global default
        # with a per-verb scope lookup (see _find_scoped_time_value).
        # The i3rab tokenizer drops Quranic pause marks (ۚ ۖ ۗ ...)
        # before they reach sent.tokens, so we recover their positions
        # by re-aligning sent.text against tokens.
        pause_before = _build_pause_before(getattr(sent, "text", ""), tokens)

        # 1. ابحَث عَن كُلّ الأَفعال (FIIL أَو in transformation lexicon)
        for i, t in enumerate(tokens):
            verb_surface_check = getattr(t, "token", "") or getattr(t, "surface", "")
            # تَخَطّي ظُروف الزَّمان (لَيسَت أَفعالًا)
            if is_time_adverb(verb_surface_check):
                continue
            trans_check = is_transformation_verb(verb_surface_check)

            # نَقبَل: word_class=FIIL أَو الـ surface في الـ lexicon (لِتَجاوُز خَطَأ الـ engine)
            if t.word_class != "FIIL" and not trans_check:
                continue

            # 2. اجمَع الـ frame مِن العَلاقات (إِن وُجِدَت)
            agent = patient = patient2 = instrument = location = manner = time_val = None
            if relation_graph:
                for r in relation_graph.relations:
                    if r.target_id == f"t{i}":
                        if r.name == "agent_of":
                            agent = self._token_text(tokens, r.source_id)
                        elif r.name == "patient_of":
                            patient = self._token_text(tokens, r.source_id)
                        elif r.name == "patient2_of":
                            patient2 = self._token_text(tokens, r.source_id)
                        elif r.name == "in_location":
                            location = self._token_text(tokens, r.source_id)
                        elif r.name == "with_instrument" or r.name == "by_means_of":
                            instrument = self._token_text(tokens, r.source_id)
                        elif r.name == "at_time" or r.name == "during_time":
                            time_val = self._token_text(tokens, r.source_id)

            # NOTE MC FIX 2026-05-24 (per user critique): VSO fallback REMOVED.
            # كانَ يُلصِق أَوَّل اسمَين بَعد الفِعل كَ agent/patient حَتَّى
            # لَو لَم تَكُن العَلاقَة مَوجودَة. النَّتيجَة: «Event[ءمن]
            # agent=بِدَيْنٍ» وَ مَا شابَه. الآن: إِن لَم تُعطنا
            # RelationGraph الـ agent/patient، نَترُكهما None وَ الحَدَث
            # يَبقَى Hypothesis بِبَلاغ blockers صَريح.

            verb_text = getattr(t, "token", "") or getattr(t, "surface", "")
            event_type = (t.root or "—") if t.root else verb_text

            # 3. هَل هذا فِعل تَحَوُّليّ؟
            trans_entry = is_transformation_verb(verb_text)

            # 4. كَشف الزَّمَن مِن صيغَة الفِعل
            tense = detect_tense(t)

            # PATCH 5 — TimeScopeGate per-verb. Find the nearest
            # preceding time-adverb in the same clause (no pause-mark
            # between it and the verb). Past events do NOT inherit
            # when_future from a future-conditional adverb unless they
            # are inside that adverb's scope.
            scoped_time = _find_scoped_time_value(tokens, i, pause_before)

            # PATCH 5 — CommandLamEventMood. LAM_AL_AMR prefix → mark
            # mood + speech_act so downstream readers can distinguish
            # jussive command (وَلْيَكْتُب) from indicative present
            # (يَكْتُبُ).
            mood_value, speech_act_value = _detect_command_lam_mood(t)

            # 5. تَوَقُّع الـ frame مِن verb_frames_loader
            frame_roles: list = []
            try:
                from verb_frames_loader import get_frame
                vf = get_frame(verb_text)
                if vf:
                    frame_roles = [r for r, _ in vf.most_common_roles(top_n=5)]
            except Exception:
                pass

            base_kwargs = dict(
                event_id=f"ev{len(graph.events)}",
                type=event_type,
                verb_surface=verb_text,
                verb_position=i,
                agent=agent,
                patient=patient,
                patient2=patient2,
                instrument=instrument,
                time=time_val or scoped_time,
                location=location,
                manner=manner,
                tense=tense,
                mood=mood_value,
                speech_act=speech_act_value,
                time_value=scoped_time,
                frame_observed=frame_roles,
                source_of_claim=f"verb_position:{i} + word_class:{t.word_class}",
            )

            if trans_entry:
                # تَحَوُّل! نَبحَث عَن state_after في الخَبَر اللاحِق
                state_after = trans_entry["state_after"]
                # لَو state_after في الـ lexicon == "—"، نُحاوِل اشتِقاقه مِن الجُملَة
                if state_after == "—":
                    state_after = self._extract_complement(tokens, i)

                subject = agent or patient or "—"
                trans = Transformation(
                    **base_kwargs,
                    contract="TransformationContract:v1",
                    kind="Certificate" if state_after != "—" else "Hypothesis",
                    subject=subject,
                    state_before=trans_entry["state_before"],
                    state_after=state_after,
                    transformation_kind=trans_entry["transformation_kind"],
                    blockers=[] if state_after != "—" else ["state_after مَجهول — يَحتاج سِياق"],
                )
                graph.add_event(trans)
            else:
                event = Event(**base_kwargs)
                graph.add_event(event)

        return graph

    @staticmethod
    def _token_text(tokens, tid: str) -> str:
        """يَستَخرِج نَصّ الـ token مِن id like 't3'."""
        if not tid.startswith("t"):
            return ""
        try:
            idx = int(tid[1:])
            if 0 <= idx < len(tokens):
                t = tokens[idx]
                return getattr(t, "token", "") or getattr(t, "surface", "")
        except (ValueError, IndexError):
            pass
        return ""

    @staticmethod
    def _extract_complement(tokens, verb_idx: int) -> str:
        """يَبحَث عَن الخَبَر بَعد الفِعل التَّحَوُّليّ.

        Strategy: state_after = آخِر اسم بَعد الفِعل، باستثناء:
          • ظُروف الزَّمان (أَمسِ، اليَومَ، غَدًا)
          • ظُروف المَكان (هُنا، هُناكَ)
        """
        last_noun = "—"
        for j in range(verb_idx + 1, len(tokens)):
            t = tokens[j]
            tw = getattr(t, "token", "") or getattr(t, "surface", "")
            if is_time_adverb(tw):
                continue
            if t.word_class in ("ISM_MUARAB", "JAMID", "AALAM"):
                last_noun = tw
        return last_noun


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from i3rab_engine.engine import I3rabEngine
    from relation_extractor import RelationExtractor

    text = sys.argv[1] if len(sys.argv) > 1 else "صارَ الفَقيرُ غَنيًّا"
    eng = I3rabEngine()
    sent = eng.analyze_sentence(text)
    rg = RelationExtractor().extract(sent)
    eg = EventExtractor().extract(sent, rg)

    print(f"النَّصّ: {text}\n")
    print(eg)
