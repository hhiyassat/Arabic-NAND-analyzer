"""Layer 1 — WordClass detection.

Given a single token, classify it into one of:
  HARF, ISM_MABNI, ISM_MUARAB, FIIL, AALAM, JAMID, JALALAH, UNKNOWN

Detection order (most specific first):
  1. JALALAH       — direct lexical match
  2. closed_class  → HARF or ISM_MABNI (via i3rab labels)
  3. JAMID         → jamid_detector
  4. AALAM         → MASAQ NOUN_PROP (if available)
  5. open_class    → FIIL (verbal wazn) or ISM_MUARAB (otherwise)

Each decision carries a source_of_claim string.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
_CLEAN_CODE = _HERE.parent
sys.path.insert(0, str(_CLEAN_CODE))

from closed_class_detector import is_closed_class  # type: ignore
from jamid_detector import is_jamid  # type: ignore
from root_pipeline import RootPipeline  # type: ignore
from wazn_data import DIACRITICS  # type: ignore

from .refs import closed_class_kind, load_operators

_DIAC = set(DIACRITICS)


def _strip_diac(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIAC)


# Heuristic: verbal wazn prefix → verb aspect
# Imperfect: starts with يَ/تَ/أَ/نَ (vocalized) + has فْعَل/فْعُل/فْعِل interior
# Perfect:   starts with فَعَ/فَعِ/فَعُ patterns
# Imperative: starts with اف/ا (after hamzat wasl) — derived from فِعْل/فُعْل/فَعْل
def _vowel_after(wazn: str, ch: str) -> str:
    """Return the diacritic immediately AFTER the first occurrence of ``ch``
    in ``wazn``. Returns "" if not found."""
    i = wazn.find(ch)
    if i < 0 or i + 1 >= len(wazn):
        return ""
    nxt = wazn[i + 1]
    return nxt if nxt in {"َ", "ِ", "ُ", "ْ", "ّ"} else ""


# Verbal wazn SHAPES — by DIACRITIZED skeleton.
# (Read these carefully: position 2 = ف، position 4 = ع، position 6 = ل; the
# diacritic between letters tells past/imperfect/participle apart.)
#
# Past tense (ماضٍ) — recognized by the vowel pattern on the wazn body:
#   فَعَل / فَعِل / فَعُل → vowels: a-a, a-i, a-u
#   فَعَّل (form II)    → vowels: a-shadda-a
#   فَاعَل (form III)  → fatha on ع
#   أَفْعَل (form IV)   → A + sukun + a
#   تَفَعَّل (V), تَفَاعَل (VI), انْفَعَل (VII), افْتَعَل (VIII),
#   اسْتَفْعَل (X)
#
# Active participle فَاعِل — kasra on ع → NOMINAL (excluded).
# Passive participle مَفْعُول → starts with م → NOMINAL.

# Past-tense base wazns — loaded from canonical contract file.
# Per 14_Minimal_Complete_Theory.md, no hidden contracts.
try:
    from contracts_loader import load_verb_base_wazns
    _PV_BASE_DIAC = {
        w for w, m in load_verb_base_wazns().items()
        if m.get("aspect") == "PV"
    }
except ImportError:
    _PV_BASE_DIAC = set()

# Set of imperfect-verb base wazns (with prefix vowel)
_IV_PREFIXES = ("يَ", "تَ", "نَ", "أَ", "يُ", "تُ", "نُ", "أُ")

# Stripped past-tense bases — for suffix-extension fallback
_PV_BASE_PLAIN = {_strip_diac(w) for w in _PV_BASE_DIAC}

# Past tense suffixes
_PV_SUFFIXES_PLAIN = ("وا", "تما", "تم", "تن", "نا", "ت", "ن", "ا")


def _is_verbal_wazn(wazn: str, *, surface: str = "") -> tuple[bool, str]:
    """Classify a diacritized wazn as verbal. Returns (is_verb, aspect).

    DIACRITICS MATTER. فَاعِل (kasra on ع) = active participle (NOMINAL);
    فَاعَل (fatha on ع) = past tense form III (VERBAL).

    ``surface`` (optional): the SURFACE word — used to short-circuit when
    surface has unambiguously nominal markers (tanwin, ال + plural ون/ين/ات,
    ending ـة).
    """
    if not wazn:
        return False, ""
    plain = _strip_diac(wazn)
    if not plain:
        return False, ""

    # === Surface-level nominal short-circuit ===
    if surface:
        surf_plain = _strip_diac(surface)
        # Tanwin → nominal
        if any(c in surface for c in ("ٌ", "ٍ", "ً")):
            return False, ""
        # ال + plural ending → nominal
        if surf_plain.startswith("ال") and (
            surf_plain.endswith("ون") or surf_plain.endswith("ين")
            or surf_plain.endswith("ات")
        ):
            return False, ""
        # ـة → nominal
        if surf_plain.endswith("ة"):
            return False, ""

    # === Nominal early rejects (by diacritized signal) ===
    # Starts with مَ / مُ → almost always a noun
    # (مَفْعَل، مَفْعِل، مَفْعُول، مَفْعَلَة، مُفْعِل، مُفْعَل، مُفَاعِل، مُفَعَّل …)
    if wazn.startswith(("مَ", "مُ", "مِ")):
        return False, ""
    # Ends with ة → feminine singular noun
    if plain.endswith("ة"):
        return False, ""
    # فَاعِل with kasra on ع → active participle (nominal)
    if plain.startswith("فاعل") and _vowel_after(wazn, "ع") == "ِ":
        return False, ""
    # فَعِيل / فَعُول / فَعِيلَة / فَعْلَان (intensive/adjective noun shapes)
    if plain in {"فعيل", "فعول", "فعيلة", "فعلان", "فعيلين", "فعائل"}:
        return False, ""
    # Active participle of form IV: مُفْعِل (already caught by م prefix)
    # but defensive:
    if wazn.startswith("مُفْ"):
        return False, ""

    # === Imperfect (IV) — prefix-based ===
    if wazn.startswith(_IV_PREFIXES) and len(plain) >= 3:
        # Confirm the body matches a verb skeleton
        if all(c in plain for c in ("ف", "ع")) or "فل" in plain or "فال" in plain:
            return True, "IV"

    # === Past tense (PV) — direct diacritized match ===
    if wazn in _PV_BASE_DIAC:
        return True, "PV"

    # Diacritized fatha on ع (past tense indicator) for forms not in the
    # exact set — but only if it doesn't have nominal early-reject signals.
    if (
        plain.startswith(("فاعل", "افتعل", "انفعل", "تفعل", "تفاعل", "استفعل"))
        and _vowel_after(wazn, "ع") in {"َ", ""}  # fatha or no marker
    ):
        return True, "PV"

    # === Past + suffix endings (e.g., فَعَلُوا، فَالُوا، فَعَلْتُمْ) ===
    for sfx in sorted(_PV_SUFFIXES_PLAIN, key=len, reverse=True):
        if plain.endswith(sfx) and len(plain) > len(sfx) + 1:
            stem = plain[: -len(sfx)]
            if (
                stem in _PV_BASE_PLAIN
                or any(stem.endswith(b) for b in (
                    "فعل", "فاعل", "افتعل", "انفعل", "تفعل", "تفاعل",
                    "استفعل", "افعل",
                    # أجوف / ناقص
                    "فال", "فعى", "فعا",
                ))
            ):
                # Final نominal-shape gate: if stem itself looks like فَاعِل
                # (kasra on ع), the whole thing is a plural noun (e.g.,
                # فَاعِلُونَ → جمع اسم فاعل). Caller already filtered most
                # via _vowel_after; do a defensive check here too.
                if stem == "فاعل" and "ِ" in wazn[: wazn.find("ل")] :
                    return False, ""
                return True, "PV"

    return False, ""


def _verb_aspect_from_surface(token: str) -> str:
    """Refine aspect (PV / IV / CV) from the SURFACE word's first letter."""
    plain = _strip_diac(token)
    if not plain:
        return ""
    # Imperfect: starts with one of ي ت أ ن
    if plain[0] in {"ي", "ت", "أ", "ن", "إ", "ا"} and len(plain) >= 3:
        # Could be IV or imperative. Imperative usually starts with ا+فعل
        # with sukun on second letter. Imperfect has fatha/damma on first.
        # Vocalized clue: token starts with يَ/تَ/أَ/نَ (with fatha/damma)
        if len(token) >= 2:
            c2 = token[1]
            if c2 in {"َ", "ُ", "ْ"}:
                if plain[0] in {"ي", "ت", "ن"} or (plain[0] in {"أ"} and c2 != "ْ"):
                    return "IV"
        # Imperative shape: ا + sukun + ... (after hamzat wasl normalization)
        if plain[0] in {"ا", "إ", "أ"}:
            # Likely past (e.g., اسْتَخْرَجَ) or imperative — keep PV default
            return "PV"
    return "PV"


def _looks_like_verb_by_surface(token: str) -> tuple[bool, str]:
    """Use the SURFACE diacritization to detect a verb.

    Hard exclusions (clearly NOMINAL):
      - Token ends with tanwin (ٌ ٍ ً) — only nouns take tanwin
      - Token ends with ـِينَ، ـُونَ، ـَاتُ/ـَاتِ/ـَاتٍ — plural noun markers
      - Token has ال definite article — only nouns

    Markers:
      - Surface starts with يَ/يُ/تَ/تُ/نَ/نُ/أَ/أُ → IV
      - Surface starts with همزة وصل + sukun + verb-shape: اسْتَ، اِفْ
      - Surface ends with verb suffixes ـوا، ـت + diacritic مفعل

    Returns (is_verb, aspect).
    """
    if not token:
        return False, ""
    plain = _strip_diac(token)
    if len(plain) < 2:
        return False, ""

    # === Hard nominal exclusions ===
    # Tanwin → nominal
    if any(c in token for c in ("ٌ", "ٍ", "ً")):
        return False, ""
    # Definite article → nominal
    if plain.startswith("ال") and len(plain) > 2:
        return False, ""
    # Plural noun markers — but only if not preceded by IV prefix
    if plain.endswith("ون") or plain.endswith("ين"):
        # If word starts with imperfect prefix, ون/ين could be أفعال خمسة;
        # otherwise it's جمع مذكر سالم.
        if plain[0] not in {"ي", "ت", "ن", "أ"}:
            return False, ""
    if plain.endswith("ات") and not plain[0] in {"ي", "ت", "ن", "أ"}:
        return False, ""

    # === IV (imperfect) ===
    # NOTE MC FIX 2026-05-24: an IV verb needs prefix + 3-letter-root = ≥4
    # letters total. 3-letter words starting with يَ are NOUNS (يَوْم، يَدّ،
    # يَمين، نَوْم، تَمْر...), never present-tense verbs.
    if len(token) >= 2 and plain[0] in {"ي", "ت", "ن", "أ"}:
        c2 = token[1] if len(token) > 1 else ""
        if c2 in {"َ", "ُ"}:
            if len(plain) < 4:
                # too short to be an IV verb (يَ + ≥3-letter root)
                return False, ""
            # NOTE MC FIX 2026-05-24 (reverted/refined): اسم التَّفضيل أَفْعَلُ
            # يُشبِه الفِعل المُضارِع المُتَكَلِّم أَفْعَلُ. لا يُمكِن التَّمييز
            # دون سِياق. سَنَترُك التَّصنيف لِـ FIIL (الأَكثَر شُيوعًا في الكَلام
            # السَّرديّ)، وَ نَعتَمِد عَلى verbal_wazn_contract في CSV (NV_014)
            # لِالتِقاط الحالات الواضِحَة (تَنوين، أَلِف مَقصورَة).
            return True, "IV"

    # === PV with همزة وصل ===
    if plain.startswith("است") and len(plain) >= 6:
        return True, "PV"
    if plain.startswith("ا") and len(plain) >= 4 and plain[1] in {"ن", "ف"}:
        return True, "PV"

    # === PV by suffix (e.g., كَتَبُوا → ends in وا) ===
    for sfx in ("وا", "تما", "تم", "تن", "نا"):
        if plain.endswith(sfx) and len(plain) >= len(sfx) + 3:
            return True, "PV"

    # === PV simple — surface like كَتَبَ:
    #     EXACTLY 3 letters + final fatha as case marker + middle vowel ===
    if len(plain) == 3 and len(token) >= 6:
        # Need: ـَ at end + a vowel on letter[1] (not sukun)
        last = token[-1]
        if last == "َ":
            # Check that middle has a vowel (not sukun, not tanwin)
            # Token format like "كَتَبَ" = ك+َ+ت+َ+ب+َ (6 chars)
            # vs noun like "رَيْبَ"  = ر+َ+ي+ْ+ب+َ (6 chars) — sukun on 2nd letter
            # Find middle vowel: between the 2nd and 3rd actual letter
            # Iterate to find diacritic between letters
            letter_positions = [i for i, c in enumerate(token) if c not in _DIAC]
            if len(letter_positions) >= 3:
                # Check vowel right after the FIRST letter (between 1st & 2nd)
                first_letter_idx = letter_positions[0]
                second_letter_idx = letter_positions[1]
                first_diac = token[first_letter_idx + 1] if first_letter_idx + 1 < second_letter_idx else ""
                # Check vowel right after the SECOND letter (between 2nd & 3rd)
                third_letter_idx = letter_positions[2]
                second_diac = token[second_letter_idx + 1] if second_letter_idx + 1 < third_letter_idx else ""
                # Both must be a vowel (not sukun) — past tense pattern
                if first_diac in {"َ", "ُ", "ِ"} and second_diac in {"َ", "ُ", "ِ"}:
                    return True, "PV"

    return False, ""


class WordClassClassifier:
    """Classify a token into a WordClass with source_of_claim."""

    def __init__(self, *, masaq_aalam: Optional[set[str]] = None):
        self._pipe = RootPipeline()
        self._masaq_aalam = masaq_aalam or set()
        load_operators()
        # VerbalWaznContract — replaces inline _is_verbal_wazn
        try:
            from verbal_wazn_contract import VerbalWaznContract  # type: ignore
            self._verbal_wazn = VerbalWaznContract()
        except ImportError:
            self._verbal_wazn = None

    def classify_with_context(self, token: str,
                              prev_tokens: Optional[list] = None,
                              next_tokens: Optional[list] = None) -> dict:
        """Phase 4 context-aware classification (flag-controlled).

        نَفس classify(token) ثُمَّ يُطَبِّق Phase 4 resolver إذا flag ON.
        flag OFF → byte-identical لِـ classify(token).
        """
        result = self.classify(token)
        try:
            from arabic_analyzer.contextual_resolver.integration import maybe_apply_resolver
            result = maybe_apply_resolver(
                result, token,
                prev_tokens=prev_tokens,
                next_tokens=next_tokens,
            )
        except ImportError:
            pass
        return result

    def classify(self, token: str) -> dict:
        """PATCH 11 wrapper. Calls `_classify_raw` (the original logic
        unchanged) then applies narrow per-surface overrides for 3 known
        2:282 misclassifications:
          • عِندَ        → force class=ISM_MUARAB (locative ظَرف, not HARF)
          • أَلَّا       → fix wazn=`حرف نصب + لا` (was: حرف تحضيض)
          • وَأَشْهِدُوٓا → force verb_aspect=CV (was: IV; CSV has CV per MASAQ
                          but exact-surface miss because of ٓ pause-mark)
        إِذَا's role is fixed in layer3.py (the L1 class is already correct
        via PATCH 3E)."""
        result = self._classify_raw(token)
        return self._p11_post_classify(token, result)

    def _p11_post_classify(self, token: str, result: dict) -> dict:
        """Apply PATCH 11 narrow overrides. Reads only the existing
        result dict + the input surface; no segmenter/MTL changes."""
        if not token:
            return result
        import unicodedata as _ud
        nfc = _ud.normalize("NFC", token)
        # Strip diacritics + small alif maddah / sukun / pause marks
        # so surface-variant matching survives MASAQ orthography.
        _EXTRA_MARKS = "ًٌٍَُِّْـٰٓۚۖۗۘۙۛۜ۟۠ۢۤۥۦ"
        stripped = "".join(c for c in nfc if c not in _EXTRA_MARKS)
        norm = (stripped
                .replace("ٱ", "ا").replace("أ", "ا")
                .replace("إ", "ا").replace("آ", "ا"))

        # Override 1: عِندَ is a locative functional noun (ظَرف مَكان),
        # NOT a حَرف. closed_function_word_gate tags it as HARF for
        # "relation routing", but L3 then renders it as `class=HARF |
        # role=حرف` which is linguistically wrong (and L4/L5/L8 lose
        # the locative signal). Override to ISM_MUARAB so PATCH 4.5's
        # _is_functional_locative_noun gate assigns role=ظرف مكان.
        if norm == "عند" and result.get("word_class") == "HARF":
            result["word_class"] = "ISM_MUARAB"
            result.setdefault("proof_blockers", []).append(
                "patch11:inda_locative_noun_override_harf_to_ism"
            )

        # Override 2: أَلَّا wazn. The CSV row tags wazn=حرف تحضيض from
        # MASAQ, which is wrong in the 2:282 contexts where أَلَّا is
        # the assimilation أَن (HARF_NASB) + لا (NAFI). The L1
        # segmenter already peels it correctly (PATCH 3D); the wazn
        # label should reflect that.
        if norm == "الا" and (result.get("wazn") or "") == "حرف تحضيض":
            result["wazn"] = "حرف نصب + لا"
            result.setdefault("proof_blockers", []).append(
                "patch11:alla_wazn_is_subjunc_la_not_tahdid"
            )

        # Override 3: وَأَشْهِدُوٓا / فَأَشْهِدُوٓا — CV imperative.
        # MASAQ lists these as aspect=CV (verbs of command), but the
        # exact-surface lookup misses because the verse spelling has
        # the small alif maddah ٓ that the CSV row lacks. Without MTL
        # certifying, verb_form_contract falls back to surface
        # heuristics and labels them IV (mudāriʿ) because they start
        # with أَ + sukun. Force CV when surface is one of these.
        if norm in ("واشهدوا", "فاشهدوا") and result.get("verb_aspect") in ("IV", ""):
            result["verb_aspect"] = "CV"
            result.setdefault("proof_blockers", []).append(
                "patch11:wa_ashhidu_is_imperative_cv_per_masaq"
            )

        return result

    def _classify_raw(self, token: str) -> dict:
        """Classify a token into a WordClass with proof-theoretic metadata.

        Returns dict with:
          word_class, source, closed_class_kind, verb_aspect, root, wazn,
          operator_i3rab,
          proof_kind        ∈ {Certificate, Hypothesis, Zero}
          proof_contract    — name of the contract that produced the decision
          proof_blockers    — list of reasons preventing Certificate
          proof_alternatives — competing candidates considered
        """
        result = {
            "word_class": "UNKNOWN",
            "source": "",
            "closed_class_kind": "",
            "verb_aspect": "",
            "root": "",
            "wazn": "",
            "operator_i3rab": "",
            "proof_kind": "Zero",
            "proof_contract": "",
            "proof_blockers": [],
            "proof_alternatives": [],
        }
        # ═════════════════════════════════════════════════════════════
        # === STEP -1: LinguisticSourceRegistry — قَبل segmentation
        # ═════════════════════════════════════════════════════════════
        # تَوصيَة المُستَخدِم 2026-05-26 (Phase 3):
        #   registry مَبني مِن 02_mabniyat (320 entry).
        #   closed-form exact match يَمنَع segmentation وَ يُحَدِّد الصَّنف.
        #   ambiguous → Hypothesis مَع candidates، لا حَسم Certificate.
        try:
            from linguistic_source_registry import resolve_strict as _lsr_resolve
            _lsr = _lsr_resolve(token)
            if _lsr.get("found"):
                # Certificate: candidate واحِد + لا تَعارُض + لا requires_context
                if _lsr["certainty"] == "Certificate":
                    result["word_class"] = _lsr["candidates"][0]
                    result["source"] = f"registry:{_lsr['source']}"
                    result["proof_kind"] = "Certificate"
                    result["proof_contract"] = "LinguisticSourceRegistry:Phase3"
                    result["registry_candidates"] = _lsr["candidates"]
                    return result
                # Hypothesis policy:
                #   • exact-tashkīl match → نَستَخدِم أَوَّل candidate (semantic priority)
                #     كَ Hypothesis، لِأَنّ التَّشكيل يُمَيِّز المَعنى.
                #   • plain match فَقَط → نَترُك heuristics تَحسِم
                result["registry_candidates"] = _lsr["candidates"]
                result["registry_certainty"] = _lsr["certainty"]
                result["registry_source"] = _lsr["source"]
                result["registry_blockers"] = _lsr["blockers"]
                result["registry_requires_context"] = _lsr["requires_context"]
                if _lsr["source"].startswith("exact:") and _lsr["candidates"]:
                    # exact-tashkīl + ambiguous = Hypothesis بِأَوَّل candidate
                    result["word_class"] = _lsr["candidates"][0]
                    result["source"] = f"registry-exact-hypothesis:{_lsr['source']}"
                    result["proof_kind"] = "Hypothesis"
                    result["proof_contract"] = "LinguisticSourceRegistry:Phase3:exact-ambig"
                    result["proof_alternatives"] = _lsr["candidates"][1:]
                    result["proof_blockers"] = _lsr["blockers"]
                    return result
                # plain ambiguity → نُكمِل إِلى heuristics
        except ImportError:
            pass

        # ═════════════════════════════════════════════════════════════
        # === STEP 0: MasterTokenLookup — قَبل كُلّ شَيء (MASAQ-backed)
        # ═════════════════════════════════════════════════════════════
        # تَوصيَة المُستَخدِم 2026-05-25 (الحَلّ الشامِل):
        #   95%+ مِن tokens القُرآن يَجِب أَن تُصَنَّف مِن master_token_table
        #   (مَصدَر MASAQ) قَبل أَيّ heuristic. الـheuristics لِلـOOV فَقَط.
        try:
            from master_token_lookup import lookup as _mtl_lookup
            _ml = _mtl_lookup(token)
            if _ml and _ml.get("word_class") and _ml["word_class"] != "UNKNOWN":
                # PATCH 3E (2026-05-26) — FunctionalNounIdafaContract.
                # MASAQ is internally inconsistent for ظُروف + pronoun
                # forms: it tags بَيْنَكُمْ as word_class=HARF but role=
                # ADV_PLCE (adverb-of-place — a NOUN function). Treating
                # word_class as HARF makes L3 say class=HARF which is
                # linguistically false (ظَرف is an ism, not a particle).
                # When MASAQ says HARF + locative-noun role, override
                # word_class to ISM_MUARAB. Keep MASAQ's role/case for
                # downstream layers.
                _LOCATIVE_NOUN_ROLES = {
                    "ADV_PLCE",      # adverb of place (ظَرف مَكان)
                    "ADV_TIME",      # adverb of time (ظَرف زَمان)
                }
                _ml_word_class = _ml["word_class"]
                _ml_role = _ml.get("role", "")
                if _ml_word_class == "HARF" and _ml_role in _LOCATIVE_NOUN_ROLES:
                    _ml_word_class = "ISM_MUARAB"
                    result.setdefault("proof_blockers", []).append(
                        f"masaq_harf_overridden_to_ism: role={_ml_role} "
                        f"(ظَرف is a noun, not a particle)"
                    )
                result["word_class"] = _ml_word_class
                result["source"] = _ml["source"]
                if _ml.get("root"):
                    result["root"] = _ml["root"]
                if _ml.get("wazn"):
                    result["wazn"] = _ml["wazn"]
                if _ml.get("aspect"):
                    result["verb_aspect"] = _ml["aspect"]
                result["proof_kind"] = "Certificate"
                result["proof_contract"] = "MasterTokenLookup:MASAQ"
                result["masaq_tag"] = _ml.get("masaq_tag", "")
                result["case"] = _ml.get("case", "")
                result["role"] = _ml.get("role", "")
                return result
        except ImportError:
            pass

        if not token or not token.strip():
            result["word_class"] = "UNKNOWN"
            result["source"] = "empty"
            result["proof_kind"] = "Zero"
            result["proof_contract"] = "empty_input"
            result["proof_blockers"] = ["no_input"]
            return result

        plain = _strip_diac(token)

        # === 0. [HIGHEST] ClosedFunctionWordGate — تَوصيَة المُستَخدِم 2026-05-25 ===
        # "الأَدوات وَ التَّراكيب المُغلَقَة تُحسَم قَبل أَيّ مُحاوَلَة فِعليَّة."
        # يَمنَع مِمَّن، إِلَّآ، فَإِنَّهُ، أَلَّا… مِن تَوليد أَفعال وَهميَّة.
        try:
            from closed_function_word_gate import check_closed_function_word
            _fn = check_closed_function_word(token)
            if _fn.is_function:
                # Map category to correct word_class
                cat = _fn.category or "FUNCTIONAL"
                if cat == "DETACHED_PRON":
                    # ضَمائر مُنفَصِلَة — ISM_MABNI لا HARF
                    result["word_class"] = "ISM_MABNI"
                elif cat in ("LOCATIVE", "LOCATIVE_PRON"):
                    # ظَرف — ISM_MABNI (يَعمَل عَمَل المَفعول فيه)
                    result["word_class"] = "HARF"  # tagged HARF for relation routing
                else:
                    result["word_class"] = "HARF"
                result["closed_class_kind"] = cat
                result["source"] = f"closed_function_word:{cat}"
                result["proof_kind"] = "Certificate"
                result["proof_contract"] = "ClosedFunctionWordGate:v1"
                return result
        except ImportError:
            pass

        # === 1. SINGULAR TERM (لَفظ مُنفَرِد) — data-driven detector ===
        # كُلّ القَواعد في data/contracts/lists/singular_terms*.csv.
        from singular_term_detector import get_singular_term_detector
        _st = get_singular_term_detector().detect(token)
        if _st.is_singular_term:
            result["word_class"] = "SINGULAR_TERM"
            result["source"] = f"singular_term_detector + {_st.source_of_claim}"
            result["root"] = "—"
            result["is_singular_term"] = True
            result["divine_name"] = True
            result["proof_kind"] = "Certificate"
            result["proof_contract"] = "singular_term_lookup"
            return result

        # === 1.35 TanwinHardBlock (يَسبِق explicit_verbs_lexicon) ===
        # تَوصيَة المُستَخدِم 2026-05-25 (الجَلسَة 6):
        #   تَنوين = اسم قَطعًا. لا يَجوز أَن يَتَطابَق كِتَٰبٌ مَع كَتَبَ
        #   عَبر bare matching.
        if any(c in token for c in ("ٌ", "ٍ", "ً")):
            # تَأَكَّد لَيس closed function word (rare but possible)
            result["word_class"] = "ISM_MUARAB"
            result["source"] = "tanwin-hard-block:nominal"
            result["proof_kind"] = "Certificate"
            result["proof_contract"] = "TanwinHardBlock:v1"
            return result

        # === 1.4 ExplicitVerbsLexicon — قَبل VerbFormContract ===
        # MC FIX 2026-05-25 (تَوصيَة المُستَخدِم): مُعجَم صَريح لِأَفعال
        # مُعتَلَّة/مُضَعَّفَة/قَصيرَة لا تَكشِفها العُقود الصَّرفيَّة.
        try:
            from explicit_verbs_contract import is_explicit_verb, get_verb_info
            if is_explicit_verb(token):
                info = get_verb_info(token) or {}
                result["word_class"] = "FIIL"
                result["verb_aspect"] = info.get("aspect", "")
                result["lemma"] = info.get("lemma", "")
                result["source"] = f"explicit_verbs_lexicon:{info.get('aspect','')}"
                result["proof_kind"] = "Certificate"
                result["proof_contract"] = "ExplicitVerbsContract:v1"
                return result
        except ImportError:
            pass

        # === 1.45 NonVerbOverrideGate (HARD GATE before VerbFormContract) ===
        # MC FIX 2026-05-25 (الجَلسَة 6 — تَوصيَة المُستَخدِم):
        #   كِتَٰبٌ، أَمْوَٰلَكُمْ، يَعْقُوبَ، غَيْرَ يَجِب أَن تَنحَجِب قَبل
        #   VerbFormContract، لا بَعده. التَّنوين/الجَمع/العَلَم/الوَظيفيّ
        #   bdgers قَويَّة.
        try:
            from non_verb_override_gate import check_non_verb_override
            _ovr_early = check_non_verb_override(token, body=token, conj="")
            if _ovr_early.blocked:
                # تَأَكَّد أَنّه لَيس في explicit_verbs_lexicon أَوَّلًا
                _is_explicit_verb_check = False
                try:
                    from explicit_verbs_contract import is_explicit_verb as _is_ev
                    _is_explicit_verb_check = _is_ev(token)
                except Exception:
                    pass
                if not _is_explicit_verb_check:
                    klass = _ovr_early.override_class or "ISM_MUARAB"
                    result["word_class"] = klass
                    result["source"] = f"non_verb_override_gate:{_ovr_early.reason[:40]}"
                    result["proof_kind"] = "Certificate"
                    result["proof_contract"] = "NonVerbOverrideGate:hard-pre-verb-form"
                    return result
        except ImportError:
            pass

        # === 1.5 VerbFormContract — يَسبِق closed_class ===
        # MC FIX 2026-05-25 (per user critique): قَبل الاعتِماد عَلى jsonl labels
        # (التي تُسَمّي الفِعل المُسبَق بِـ ف/و كَ «HARF»)، نُجَرِّب عَقد فِعل
        # مُستَقِلّ. لَو أَعطى Certificate → نَأخُذ FIIL مُباشَرَة. هَذا يُصَحِّح
        # فَلَيْسَ، فَاكْتُبُوهُ، وَلْيَكْتُبْ، وَٱتَّقُوا، وَكَانَ.
        try:
            from verb_form_contract import evaluate_verb_form
            _vv = evaluate_verb_form(token)
            if _vv.kind == "Certificate":
                result["word_class"] = "FIIL"
                result["verb_aspect"] = _vv.aspect
                result["source"] = f"verb_form_contract:{_vv.aspect}"
                result["proof_kind"] = "Certificate"
                result["proof_contract"] = "VerbFormContract:v1"
                # تَمرير الميزات الإِضافيَّة
                if _vv.lemma:
                    result["lemma"] = _vv.lemma
                if _vv.mood:
                    result["verb_mood"] = _vv.mood
                if _vv.person:
                    result["verb_person"] = _vv.person
                if _vv.number:
                    result["verb_number"] = _vv.number
                if _vv.gender:
                    result["verb_gender"] = _vv.gender
                return result
        except ImportError:
            pass

        # === 2. closed_class → HARF or ISM_MABNI ===
        if is_closed_class(token):
            kind = closed_class_kind(token)
            result["closed_class_kind"] = kind
            # Operator lookup (also gives the default i3rab phrase)
            ops = load_operators()
            op_row = ops.get(token) or ops.get(plain) or {}
            result["operator_i3rab"] = op_row.get("i3rab", "")

            if kind == "OVERRIDE_AS_VERB":
                # Word has FIIL label → it's a verb with attached pronoun
                # (e.g., اهْدِنَا = اهد + نا). Skip closed-class, fall through.
                # Record this as a blocker for the eventual classification.
                result["proof_blockers"].append(
                    "closed_class_lookup_overridden_by_FIIL_label"
                )
            elif kind.startswith("HARF"):
                result["word_class"] = "HARF"
                result["source"] = f"closed_class:{kind}"
                # Specific HARF kind from labels → Certificate
                result["proof_kind"] = "Certificate"
                result["proof_contract"] = f"closed_class_detector:{kind}"
                return result
            elif kind in {"ISM_MAWSOOL", "ISM_ISHARA",
                          "ISM_SHART", "ISM_ISTIFHAM",
                          "DAMEER", "MAWSOOL",
                          "ZARF_ZAMAN_MABNI", "ZARF_MAKAN_MABNI"}:
                result["word_class"] = "ISM_MABNI"
                result["source"] = f"closed_class:{kind}"
                result["proof_kind"] = "Certificate"
                result["proof_contract"] = f"closed_class_detector:{kind}"
                return result
            elif kind == "ISM_MABNI_GENERIC":
                # MABNI without specific kind — Hypothesis
                result["word_class"] = "ISM_MABNI"
                result["source"] = f"closed_class:{kind}"
                result["proof_kind"] = "Hypothesis"
                result["proof_contract"] = "closed_class_detector:MABNI_fallback"
                result["proof_blockers"].append(
                    "no_specific_ism_mabni_kind_label"
                )
                return result
            elif kind == "":
                # is_closed_class said yes, but we have NO specific kind.
                # Could be a noun mistakenly in the set (e.g., رَبِّ).
                # Fall through to open-class detection.
                result["proof_blockers"].append(
                    "closed_class_set_match_but_no_specific_kind"
                )
            else:
                result["word_class"] = "HARF"
                result["source"] = f"closed_class:{kind}"
                result["proof_kind"] = "Hypothesis"
                result["proof_contract"] = f"closed_class_detector:{kind}"
                return result

        # === 3. JAMID — مع فحص الجذر الفعلي (delegated to root_pipeline) ===
        # NOUN_CONCRETE في MASAQ يَشمل الجامد الحقيقي (الأرض) والمُشتقّ
        # المحسوس (كتاب). نُؤجِّل القرار إلى root_pipeline الذي يَفحص
        # الجذر الفعلي وَيُعيد open_class لو كان مشتقًّا.
        if is_jamid(token):
            ana = self._pipe.analyze(token)
            if ana.status == "open_class":
                # المُحاذي وَجَد جذرًا له فعل حيّ — اسم معرب مشتق
                result["word_class"] = "ISM_MUARAB"
                result["root"] = ana.root
                result["wazn"] = ana.wazn
                result["source"] = (
                    f"open_class+wazn_on_concrete_noun:{ana.wazn}"
                )
                result["proof_kind"] = "Hypothesis"
                result["proof_contract"] = (
                    f"wazn_aligner_on_concrete_noun:{ana.wazn}"
                )
                return result
            # وإلا — جامد حقيقي
            result["word_class"] = "JAMID"
            result["source"] = "jamid_detector"
            result["proof_kind"] = "Certificate"
            result["proof_contract"] = "jamid_detector_no_verbal_root"
            return result

        # === 4. AALAM (proper noun) — MASAQ NOUN_PROP lookup → Certificate ===
        if plain in self._masaq_aalam:
            result["word_class"] = "AALAM"
            result["source"] = "masaq_noun_prop"
            result["proof_kind"] = "Certificate"
            result["proof_contract"] = "masaq_noun_prop_lookup"
            return result

        # === 4.5. Closed-class set match but no specific kind ===
        # is_closed_class said yes, fall-through didn't catch it.
        if is_closed_class(token):
            # MC FIX 2026-05-24 (per user critique): قَبل التَّصنيف الِافتِراضيّ
            # كَ HARF، تَحَقَّق إِن كانَ مَوصولًا أَو إِشارَة (هذه أَسماء لا حُروف).
            try:
                from resolution_engine import is_relative_pronoun, is_demonstrative
                if is_relative_pronoun(token):
                    result["word_class"] = "ISM_MAWSOOL"
                    result["source"] = "relative_pronouns_csv"
                    result["proof_kind"] = "Certificate"
                    result["proof_contract"] = "relative_pronouns_lookup"
                    return result
                if is_demonstrative(token):
                    result["word_class"] = "ISM_ISHARA"
                    result["source"] = "demonstratives_csv"
                    result["proof_kind"] = "Certificate"
                    result["proof_contract"] = "demonstratives_lookup"
                    return result
            except Exception:
                pass
            # default: HARF (Hypothesis)
            result["word_class"] = "HARF"
            result["source"] = "closed_class_set_no_kind"
            result["proof_kind"] = "Hypothesis"
            result["proof_contract"] = "closed_class_set_no_specific_kind"
            result["proof_blockers"].append(
                "in_closed_class_set_but_no_label_subtype"
            )
            return result

        # === 5. Open-class via root_pipeline (Hypothesis — heuristic) ===
        analysis = self._pipe.analyze(token)
        result["root"] = analysis.root
        result["wazn"] = analysis.wazn

        if analysis.status == "open_class":
            # نَستعمل VerbalWaznContract لو متاح، وإلا fallback للـ inline
            if self._verbal_wazn is not None:
                is_verb, asp = self._verbal_wazn.is_verbal(
                    analysis.wazn, surface=token
                )
            else:
                is_verb, asp = _is_verbal_wazn(analysis.wazn, surface=token)
            # MC FIX 2026-05-25 (per user critique): NonVerbOverrideGate
            # يَمنَع تَصعيد كَلِمَة إلى FIIL لَو كانَت تَحوي قَرائن اسميَّة
            # قَويَّة (ال، تاء مَربوطَة، ـان مُثَنَّى، ـى مَقصورَة، أَفْعَلُ تَفضيل).
            if is_verb:
                try:
                    from non_verb_override_gate import check_non_verb_override
                    _ovr = check_non_verb_override(token, body=token, conj="")
                    if _ovr.blocked:
                        is_verb = False
                        result["proof_blockers"].append(
                            f"NonVerbOverrideGate downgraded wazn-FIIL → nominal: {_ovr.reason}"
                        )
                except ImportError:
                    pass
            # MC FIX 2026-05-25: ObjectPronounVsPossessivePronounGate
            # يَفصِل: ضَمير مَفعول → اسمَح بِالفِعل / ضَمير مِلكيَّة → امنَع
            if is_verb:
                try:
                    from object_pronoun_vs_possessive_gate import classify_attached_pronoun
                    _cls_o = classify_attached_pronoun(token)
                    if _cls_o.is_possessive:
                        is_verb = False
                        result["proof_blockers"].append(
                            f"PossessivePronoun gate downgraded wazn-FIIL → nominal: {_cls_o.reason}"
                        )
                except ImportError:
                    pass
            if is_verb:
                result["word_class"] = "FIIL"
                surf_asp = _verb_aspect_from_surface(token)
                result["verb_aspect"] = surf_asp or asp
                result["source"] = f"open_class+verbal_wazn:{analysis.wazn}"
                result["proof_kind"] = "Hypothesis"
                result["proof_contract"] = f"wazn_aligner_verbal:{analysis.wazn}"
                result["proof_alternatives"].append(
                    {"word_class": "ISM_MUARAB", "reason": "wazn_might_be_active_participle"}
                )
                return result
            # Fallback: wazn says nominal, but surface might be a verb
            surf_is_verb, surf_asp = _looks_like_verb_by_surface(token)
            # MC FIX 2026-05-25: NonVerbOverrideGate أَيضًا هُنا
            if surf_is_verb:
                try:
                    from non_verb_override_gate import check_non_verb_override
                    _ovr2 = check_non_verb_override(token, body=token, conj="")
                    if _ovr2.blocked:
                        surf_is_verb = False
                        result["proof_blockers"].append(
                            f"NonVerbOverrideGate downgraded surface-FIIL → nominal: {_ovr2.reason}"
                        )
                except ImportError:
                    pass
            # MC FIX 2026-05-25: ObjectPronounVsPossessivePronounGate
            if surf_is_verb:
                try:
                    from object_pronoun_vs_possessive_gate import classify_attached_pronoun
                    _cls_s = classify_attached_pronoun(token)
                    if _cls_s.is_possessive:
                        surf_is_verb = False
                        result["proof_blockers"].append(
                            f"PossessivePronoun gate downgraded surface-FIIL → nominal: {_cls_s.reason}"
                        )
                except ImportError:
                    pass
            if surf_is_verb:
                if not analysis.wazn.startswith(("مَ", "مُ", "مِ")):
                    result["word_class"] = "FIIL"
                    result["verb_aspect"] = surf_asp
                    result["source"] = (
                        f"open_class+surface_verb_heuristic"
                        f" (wazn={analysis.wazn})"
                    )
                    result["proof_kind"] = "Hypothesis"
                    result["proof_contract"] = "surface_verb_heuristic"
                    result["proof_blockers"].append(
                        f"wazn_classified_as_nominal_but_surface_looks_verbal:{analysis.wazn}"
                    )
                    result["proof_alternatives"].append(
                        {"word_class": "ISM_MUARAB", "reason": f"wazn_says_nominal:{analysis.wazn}"}
                    )
                    return result
            result["word_class"] = "ISM_MUARAB"
            result["source"] = f"open_class+nominal_wazn:{analysis.wazn}"
            result["proof_kind"] = "Hypothesis"
            result["proof_contract"] = f"wazn_aligner_nominal:{analysis.wazn}"
            return result

        if analysis.status == "no_match":
            # HARD GATE 2026-05-24 (per user critique): تَنوين عَلى السَّطح
            # = اسم قَطعًا. لا يُمكِن تَصنيف surface ينتهي بِتَنوين كَ FIIL
            # حَتَّى لَو بَدَأ بِـ يَ/تَ/أَ/نَ.
            has_tanwin = any(c in token for c in ("ٌ", "ٍ", "ً"))
            # MC FIX 2026-05-25: NonVerbOverrideGate أَيضًا هُنا
            blocked_by_gate = False
            try:
                from non_verb_override_gate import check_non_verb_override
                _ovr3 = check_non_verb_override(token, body=token, conj="")
                if _ovr3.blocked:
                    blocked_by_gate = True
                    result["proof_blockers"].append(
                        f"NonVerbOverrideGate downgraded no_match-FIIL → nominal: {_ovr3.reason}"
                    )
            except ImportError:
                pass
            # Surface-level heuristic: starts with يَ/تَ/أَ/نَ → likely verb
            if (plain and plain[0] in {"ي", "ت", "أ", "ن"}
                and not has_tanwin and not blocked_by_gate):
                result["word_class"] = "FIIL"
                result["verb_aspect"] = "IV"
                result["source"] = "surface_heuristic:imperfect_prefix"
                result["proof_kind"] = "Hypothesis"
                result["proof_contract"] = "surface_heuristic:imperfect_prefix"
                result["proof_blockers"].append("no_wazn_matched_using_surface_prefix")
                return result
            result["word_class"] = "ISM_MUARAB"
            result["source"] = "no_match_default_ism"
            result["proof_kind"] = "Hypothesis"
            result["proof_contract"] = "no_match_default_ism"
            result["proof_blockers"].append("no_wazn_matched_default_to_ism")
            return result

        # Fallback: nothing recognized → Zero (NOT a guess)
        result["word_class"] = "UNKNOWN"
        result["source"] = f"unhandled_status:{analysis.status}"
        result["proof_kind"] = "Zero"
        result["proof_contract"] = "no_classifier_matched"
        result["proof_blockers"].append(f"unhandled_pipeline_status:{analysis.status}")
        return result


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    clf = WordClassClassifier()
    tests = [
        ("اللَّهِ", "JALALAH"),
        ("اللَّهُمَّ", "JALALAH"),
        ("فِي", "HARF"),
        ("عَلَى", "HARF"),
        ("الَّذِينَ", "ISM_MABNI"),
        ("هَذَا", "ISM_MABNI"),
        ("هُوَ", "ISM_MABNI"),
        ("السَّمَاوَاتِ", "JAMID"),
        ("الْأَرْضِ", "JAMID"),
        ("كَتَبَ", "FIIL"),
        ("يَكْتُبُ", "FIIL"),
        ("آمَنُوا", "FIIL"),
        ("قَالُوا", "FIIL"),
        ("كَاتِبٌ", "ISM_MUARAB"),
        ("مَكْتُوب", "ISM_MUARAB"),
    ]
    print(f"{'token':<20} {'expected':<14} {'got':<14} {'source':<40}")
    print("-" * 95)
    for tok, exp in tests:
        r = clf.classify(tok)
        mark = "✓" if r["word_class"] == exp else "✗"
        print(f"{mark} {tok:<18} {exp:<14} {r['word_class']:<14} {r['source']}")
