# BUGS FROM 2:282 AUDIT — DETAILED SPEC

> **Date:** 2026-05-26
> **Source artifact:** `out_2_282_phase4_off.txt` (829 lines, full pipeline trace of Quran 2:282 with the contextual-resolver flag OFF).
> **Phase:** 0 — documentation only. No code is modified by this file.
> **Branch:** `phase4-certificate-reevaluation`.
> **Repo state at audit time:** working tree has uncommitted experimental work from a prior session under standalone `*_SPEC.md` / `*_RULE_LOCK.md` files in `clean_code/`. Those experiments overlap with several families below; this spec is written from a fresh-eyes baseline against `git HEAD` (`b599cd4`), not from those drafts. Where overlap exists, the "Current status in working tree" line calls it out so PHASE 1+ can decide whether to reuse, supersede, or rewrite.

## Reading order

- Sections A–H are diagnostic. Each numbered bug family contains:
  - **Symptom from 2:282** — verbatim line(s) from `out_2_282_phase4_off.txt`.
  - **Locus** — file + function/section where the bug originates (verified by `git grep` / direct read).
  - **Root cause** — single-sentence explanation grounded in the read code, not in memory.
  - **Expected behavior** — what a correct contract should produce.
  - **Contract name** — the canonical name for the eventual fix.
  - **Current status in working tree** — `none` / `draft in clean_code/<name>_SPEC.md` / `partial`.
- Section I is the proposed phasing.
- Section J is the acceptance checklist.

The phasing in §I matches the seven phases declared by the governance prompt (PHASE 1A through PHASE 7) plus a metrics phase (PHASE 8). PHASE 0 closes after this document is committed.

---

## A. L1/L2 — Segmentation & Morphology bugs

### A1. ClosedFormSegmentationLock

**Symptom from 2:282 (lines 38, 51, 81, 87, 91):**
```
ٱلَّذِى              ← prefixes=الَّ(DET) | stem=ذِى     | suffixes=—
ٱلَّذِى              ← prefixes=الَّ(DET) | stem=ذِى     | suffixes=—
ٱلشُّهَدَآءِ         ← prefixes=ال(DET)   | stem=شُهَدَءَاءِ | suffixes=—
ٱلْأُخْرَىٰ          ← prefixes=الْ(DET)   | stem=أُخْرَىٰ | suffixes=—
ٱلشُّهَدَآءُ         ← prefixes=ال(DET)   | stem=شُهَدَءَاءُ | suffixes=—
```

**Locus:** `clean_code/segmenter.py` — the `_PREFIX_RULES` loop fires `_rule_article` (the `ال` definite-article peeler) before checking whether the full surface is itself a closed-class lexeme. `_CLOSED_CLASS_LEXEMES` (line 127) lists most relatives, but only with `ا` (bare alef) variants — e.g. `"الذي"` is present, but the `ٱلَّذِى` with alif wasla `ٱ` (U+0671) and Yaa Maksura `ى` is not normalized into the same key before lookup.

**Root cause:** the closed-class lookup is keyed on a plain-text form that does not normalize alef wasla and `ى` ⇄ `ي` consistently. As a result `ٱلَّذِى` falls through to the article peeler and emerges as `ال + ذِى`, which is morphologically false (the article cannot peel from a relative pronoun).

**Expected behavior:** if the full surface — after a deterministic normalization that folds `ٱ→ا`, `ى→ي`, and strips harakat for the lookup key — matches a registered closed-form (relative pronoun, demonstrative, vocative, etc.), return a single-segment result with `prefixes=[]`, `stem=<original surface>`, `suffixes=[]`, plus metadata `locked=True`, `source=closed_form|relative_pronoun|demonstrative_compound`.

**Contract name:** `ClosedFormSegmentationLock:v1`.

**Applies to (test list):** `ٱلَّذِى`, `ٱلَّذِينَ`, `ٱلَّتِي`, `ٱلَّذَانِ`, `ٱلَّذَيْنِ`, `أُولَٰئِكَ`, `هَٰذَا`, `هَؤُلَاءِ`, `ذَٰلِكُمْ`.

**Current status in working tree:** **partial draft.** `clean_code/DEMONSTRATIVE_COMPOUNDS_ATOMIC_SPEC.md` + CSV cover the demonstrative-with-addressee compounds. They do **not** cover `ٱلَّذِى / ٱلَّذِينَ / ٱلَّتِي` (alef-wasla + alef-maksura relatives) — the article peeler still fires for those. The draft also did not introduce a `locked=True` flag.

---

### A2. LamAlAmrSegmentationContract

**Symptom from 2:282 (lines 22, 36, 37, 41, 63):**
```
وَلْيَكْتُب          ← prefixes=— | stem=وَلْيَكْتُب          | suffixes=—
فَلْيَكْتُبْ         ← prefixes=— | stem=فَلْيَكْتُبْ         | suffixes=—
وَلْيُمْلِلِ         ← prefixes=— | stem=وَلْيُمْلِلِ         | suffixes=—
وَلْيَتَّقِ          ← prefixes=— | stem=وَلْيَتَّقِ          | suffixes=—
فَلْيُمْلِلْ         ← prefixes=— | stem=فَلْيُمْلِلْ         | suffixes=—
```

**Locus:** `clean_code/segmenter.py`. There is a conjunction-peel rule (`_rule_conjunction` for `وَ` / `فَ`), an imperfect-prefix rule (`_rule_iv_prefix` for `يَ / تَ / نَ / أَ`), and a `_rule_future_particle` (for `سَ`). There is **no** rule for the jussive command particle `لِ` / `لْ` (lām al-amr) that appears after وَ / فَ in `وَلْيَكْتُبْ`-style forms.

**Root cause:** the conjunction peel handles `و / ف`, but the resulting body still starts with `لْ + يَكْتُبْ`. No rule recognizes the `لْ` as a jussive marker, so the entire body remains as the stem. Downstream, L3 sees `وَلْيَكْتُبْ` as an unsegmented stem and the wazn aligner fails (it produces empty root/wazn — visible in the L3 lines for these same surfaces: `root=— | wazn=—`).

**Expected behavior:** a new segmentation rule peels CONJ (`و|ف`) + LAM_AMR (`لْ` / `لِ`) + IMPERFECT_VERB. The resulting `SegmentationResult` carries metadata `lam_al_amr=True`, `mood=jussive`, `speech_act=command_or_request`, and L3 / L5 propagate the mood/voice tags.

**Contract name:** `LamAlAmrSegmentationContract:v1`.

**Applies to (test list):** `وَلْيَكْتُب`, `فَلْيَكْتُبْ`, `وَلْيُمْلِلِ`, `فَلْيُمْلِلْ`, `وَلْيَتَّقِ`. Negative test: `لَيلًا`, `لِسانٌ` — both start with لَ/لِ but are not jussive constructions.

**Current status in working tree:** **none.** No SPEC/RULE_LOCK file in the repo addresses lām al-amr segmentation.

---

### A3. PastSuffixBeforeImperfectPrefixContract

**Symptom from 2:282 (line 15):**
```
تَدَايَنتُم          ← prefixes=تَ(IMPERF_PREF) | stem=دَا | suffixes=يَن(NSUFF)+تُم(VSUFF)
```

**Locus:** `clean_code/segmenter.py` — `_rule_iv_prefix` peels initial `تَ` as imperfect prefix unconditionally. The suffix `تُم` (the strongest past-tense 2-pl suffix in Arabic) is detected separately but does not block the prefix rule.

**Root cause:** rule ordering. The imperfect-prefix peel fires before the suffix detector that would have identified `تُم` as a past-tense terminator. The result is structurally impossible: a single verb cannot have both an imperfect prefix and a perfect-tense suffix.

**Expected behavior:** if the surface ends in a certified past-tense subject suffix (`تُ / تَ / تِ / تُمْ / تُمَا / تُمْ / تُنَّ / نَا / وا`), suppress the imperfect-prefix peel of `تَ`. Verb stays unsegmented at its head; only the past-suffix is peeled. L3 will then see a Form VI past verb (تَفاعَلَ) with root `دين` and aspect `PV` (perfective).

**Contract name:** `PastSuffixBeforeImperfectPrefixContract:v1`.

**Applies to:** `تَدَايَنتُم`, `تَبَايَعْتُمْ`, `تَأَخَّذْتُم`, plus any `تَفاعَلَ` / `تَفَعَّلَ` / `تَفَعَّلْنَ` form with تُم/تُنَّ/نَا suffix. Negative test: real imperfect verbs (`تَكْتُبُ`, `تَدْرُسُ`) must still get `تَ(IMPERF_PREF)`.

**Current status in working tree:** **none.** `IV_PREFIX_ROOT_EXTRACTION_SPEC.md` in working tree adds ت / ي / ن / أ as valid imperfect prefixes for root extraction, but that is the **opposite** problem (acceptance, not rejection). PHASE 1C is independent of that draft.

---

### A9. HamzaTanwinNormalizationBug

**Symptom from 2:282 (line 47):**
```
شَيْـًٔا             ← prefixes=— | stem=شَئًْا | suffixes=—
```

The stem displays the tanwin `ً` (U+064B) **before** the sukun `ْ` (U+0652), but in canonical Quranic Uthmani the order is `ٔ + ْ + ا + ً`. The displayed `ئًْا` puts harakat in non-canonical order.

**Locus:** `clean_code/normalizer.py` and/or `segmenter.py`. The verse contains the special hamza-on-alef sequence written as `شَيْـًٔا` (kashida + hamza-below-yaa + tanwin + alef). Normalization should re-order combining marks to NFC canonical, but the displayed stem suggests the canonicalization is incomplete for this 5-codepoint hamza sequence.

**Root cause (to verify in PHASE 3):** suspected that NFC re-ordering is applied per-character without re-checking neighbors after tatweel removal. The hamza marker (`ٔ`) and the following sukun/tanwin land in the wrong slot.

**Expected behavior:** stem displays as `شَيْئًا` or the canonical NFC equivalent. Tanwin always trails the carrier letter, sukun never trails a non-letter.

**Contract name:** `HamzaTanwinNormalizationBug:v1` (the user prompt names it as a bug; the fix can be named `HamzaTanwinOrderContract:v1`).

**Applies to:** `شَيْـًٔا`, `جُزْءًا`, `يَعْبَؤُا`, etc. — any token with kashida + hamza + tanwin combination.

**Current status in working tree:** **none.** The `SEGMENTER_DISPLAY_STEM_SPEC.md` draft only handles `آ` ⇄ `ءَا` recomposition. It does not touch tanwin/sukun ordering.

---

## B. L3 — WordClass / Role / Root / Wazn bugs

### B4. FunctionalNounIdafaContract

**Symptom from 2:282 (lines 23, 122, 259):**
```
بَّيْنَكُمْ          ← prefixes=بَّيْنَ(PREP) | stem=كُمْ | suffixes=—
بَيْنَكُمْ           ← prefixes=بَيْنَ(PREP) | stem=كُمْ | suffixes=—
...
بَيْنَكُمْ           → class=HARF | role=حرف | wazn=ضمير متصل
```

**Locus:** `segmenter.py` has a multi-letter-prep rule that treats `بَيْنَ` as a PREP prefix. The L1 closed-class detector then labels the surface as HARF, propagating into L3.

**Root cause:** `بين` is in `_CLOSED_CLASS_LEXEMES` (line 145 of segmenter.py: `..."بين", "تحت", "فوق", "أمام", "خلف", "وراء", "قبل", "بعد", "عند", "لدى"...`), but `_CLOSED_CLASS_LEXEMES` does not distinguish **ظَرْف** (adverbial noun in iḍāfah) from **حرف جر** (true preposition). The downstream class lookup defaults the entire family to HARF.

**Expected behavior:** `بَيْنَ + كُمْ` is recognized as `ظَرْف` (locative noun) + possessive pronoun in iḍāfah construction. WordClass = `ISM` (not HARF). Role = `ظَرف مَكان` or `مضاف`. The إعراب should be `منصوب على الظَّرفيَّة` or contextually `مَجرور بِحَذف حرف الجَر`.

**Contract name:** `FunctionalNounIdafaContract:v1`.

**Applies to:** `بَيْنَ + كم/كما/كن/هم/هن/هما`, `عِنْدَ + Xسُهم`, `قَبْلَ + كم`, `بَعْدَ + كم`, `تَحْتَ + كم`, `فَوْقَ + كم`, `أَمَامَ + كم`, etc. Negative test: real prepositions (`في`, `إلى`, `على`, `من`, `بِ`, `لِ`) must still be HARF.

**Current status in working tree:** **none.** The classification of بَيْنَ as PREP is correctly noted in the prior `out_2_282` report but no fix exists.

---

### B5. FalseLamPrefixInLexicalStem

**Symptom from 2:282 (line 64):**
```
وَلِيُّهُۥ            ← prefixes=وَ(CONJ)+لِ(PREP) | stem=يُّهُۥ | suffixes=—
```

**Locus:** `segmenter.py` `_rule_prep_clitic`. The rule sees `وَ + لِ + يُّهُ` and peels both `وَ` (CONJ) and `لِ` (PREP). But the correct split is `وَ + وَلِيّ + هُ` (CONJ + lexical noun وَلِيّ + possessive pronoun هُ).

**Root cause:** the prep-clitic rule has no morphological gating. It peels `لِ` whenever it sees لِ followed by a body, without checking whether what remains is a viable stem. Here, peeling `لِ` leaves `يُّهُ` — which has shadda on a non-initial letter and is not a valid Arabic stem.

**Expected behavior:** before peeling `لِ`, the rule must verify the residual body would be a viable open-class stem (no orphan shadda at position 0, length ≥ 2, etc.). If invalid, do not peel — the `لِ` is lexical, not a preposition.

**Contract name:** `FalseLamPrefixInLexicalStem:v1` (or `LamPrefixViabilityCheck:v1`).

**Applies to:** `وَلِيّ`, `لِسان`, `لِبَاس`, `لَيْل`, `لِين`, `لَأَلَأ`. Negative test: `لِزَيدٍ`, `لِكِتَابٍ`, `لِلَّهِ` must keep `لِ` as PREP.

**Current status in working tree:** **none.**

---

### B6. AllaCompoundContract

**Symptom from 2:282 (lines 113, 126, 251, 263):**
```
أَلَّا               ← prefixes=أن(PREP) | stem=لا | suffixes=—
أَلَّا               ← prefixes=أن(PREP) | stem=لا | suffixes=—
أَلَّا               → class=HARF | role=حرف | wazn=حرف تحضيض
أَلَّا               → class=HARF | role=حرف | wazn=حرف تحضيض
```

**Locus:** `segmenter.py` line 1670 (assimilation rule) — splits `أَلَّا` as `أن + لا` and **tags the `أن` as PREP**. L3 then attaches the wazn `حرف تحضيض` (incitement particle), which is the meaning of أَلَا (no shadda), not أَلَّا (with shadda).

**Root cause:** two layered bugs:
1. The assimilation tag for the peeled `أن` is `PREP` — that is wrong. `أن` is `HARF_NASB` (subjunctive particle), not a preposition.
2. The KB/L3 layer maps `أَلَّا` (shadda) to the `حرف تحضيض` meaning of `أَلَا` (no shadda) because the underlying lookup is plain-fallback.

**Expected behavior:** in the context of 2:282 (`أَلَّا تَرتَابوا`, `أَلَّا تَكْتُبوها`), `أَلَّا = أَنْ + لَا`. The `أن` tag should be `HARF_NASB`. The `لا` tag should be `HARF_NAFY`. The composite meaning is "that … not" (negation of the subjunctive), not تحضيض.

**Contract name:** `AllaCompoundContract:v1` (segmentation tagging) + `HamzaParticleIdentityGate:v1` (KB.SAM side — see C14).

**Applies to:** every `أَلَّا` in the Quran (frequent). Negative tests: `أَلا` (no shadda, real تحضيض), `إِلَّا` (exception particle — see C14).

**Current status in working tree:** **none.**

---

### B7. MinManCompoundContract

**Symptom from 2:282 (line 78):**
```
مِمَّن               ← prefixes=من(PREP) | stem=من | suffixes=—
```

The audit assigns the whole token to HARF, with both prefix and stem rendered as `من` (after diacritic strip), losing the inner/outer distinction.

**Locus:** `segmenter.py` — there is no specific rule for the assimilated `مِن + مَن` → `مِمَّن` pattern. The current handling treats it as a single HARF compound.

**Root cause:** the inner `مَن` is one of Arabic's ambiguous particles (relative / conditional / interrogative depending on context), and the outer `مِن` is unambiguously a preposition. Conflating both into a single `مِن` (HARF) discards the inner role and prevents downstream resolvers from acting on the inner `مَن`.

**Expected behavior:** split as `مِن (HARF_JARR, certain)` + `مَن (ISM_MAWSOOL or contextual ambiguous, Hypothesis)`. The inner `مَن`'s role is then handed to L6 / L7 for context resolution (relative / conditional / interrogative).

**Contract name:** `MinManCompoundContract:v1`.

**Applies to:** `مِمَّن`, `عَمَّن`, `لَمَّن`, `بِمَن`, `كَمَن`. Also the negated form `مِمَّا = مِن + ما`.

**Current status in working tree:** **none.** `closed_function_words.csv` row 42 has `مِمَّن,PREP_COMPOUND,"من + من"` but the description is ambiguous and the resolver does not split internally.

---

### B8. DualVerbSuffixContract

**Symptom from 2:282 (line 74):**
```
يَكُونَا             ← prefixes=يَ(IMPERF_PREF) | stem=كُو | suffixes=نَا(POSS_PRON)
```

**Locus:** `segmenter.py` — `_rule_pronoun_suffix` peels `نَا` as a possessive pronoun. But `يَكُونَا` is the dual imperfect of كان: stem = كون, with an `ا` suffix marking dual subject (هما). The `نَ` before the `ا` is the dual marker in jussive context, not a `نا` (we) pronoun.

**Root cause:** the suffix detector is too eager. It sees `...نَا` at end of word and infers POSS_PRON, without checking the surrounding context (the verb being dual imperfect, the preceding `لَّمْ` in 2:282 forcing jussive, etc.).

**Expected behavior:** when the residual stem after `نَا` peeling is structurally implausible (e.g. `كُو` — incomplete trilateral root), and the surface matches a dual imperfect / jussive pattern (`يَفْعَلَا`, `تَفْعَلَا`), keep the verb whole and tag the `ا` as `DUAL_MARKER`, not POSS_PRON.

**Contract name:** `DualVerbSuffixContract:v1`.

**Applies to:** `يَكُونَا`, `تَكُونَا`, `يَفْعَلَا`, `يَعْلَمَا`, `يَخْشَيَا`. Negative: `أَخَذْنَا`, `كَتَبْنَا`, `أَكَلْنَا` must keep `نَا` as past-1pl suffix.

**Current status in working tree:** **none.**

---

### B10. DualCaseResolver

**Symptom from 2:282 (lines 210, 216):**
```
شَهِيدَيْنِ          → class=ISM_MUARAB | role=اسم مجرور
رَجُلَيْنِ           → class=ISM_MUARAB | role=اسم مجرور
```

Both `شَهِيدَيْنِ` (in `وَٱسْتَشْهِدُوا شَهِيدَيْنِ`) and `رَجُلَيْنِ` (in `لَّمْ يَكُونَا رَجُلَيْنِ`) carry the dual يْنِ ending. They are tagged `مجرور` because the `ي` is treated as a genitive marker.

**Locus:** `i3rab_engine/layer2.py` — case detection from final-diacritic. The dual يْنِ pattern is ambiguous: it marks مجرور when the dual is genitive, but **مَنصوب** when accusative (the dual نَصب uses ي instead of ا).

**Root cause:** L2 reads the final kasra under nūn and infers genitive without considering syntactic role:
- `شَهِيدَيْنِ` after the transitive imperative `وَٱسْتَشْهِدُوا` should be **مفعول به منصوب** (the ي is the accusative dual marker).
- `رَجُلَيْنِ` as predicate of `لَّمْ يَكُونَا` should be **خبر يَكُون منصوب**.

**Expected behavior:** the L2/L3 contract for dual يْنِ surfaces consults the upstream verb (if FIIL + transitive → دfعول به منصوب; if FIIL + verb-of-كان family → خبر منصوب; if preceded by HARF_JARR → مجرور).

**Contract name:** `DualCaseResolver:v1`.

**Applies to:** all dual nouns ending in يْنِ / اِنِ. Negative: `بِشَهيدَينِ` (after HARF_JARR) stays مجرور.

**Current status in working tree:** **none.**

---

### B11. ComparativeAdjectiveContract

**Symptom from 2:282 (lines 245, 248, 250):**
```
أَقْسَطُ             → class=ISM_MUARAB | role=فاعل مرفوع | root=قسط | wazn=فعل
وَأَقْوَمُ           → class=ISM_MUARAB | role=اسم مرفوع | root=قوم | wazn=فعل
وَأَدْنَىٰٓ          → class=ISM_MUARAB | role=اسم        | root=—   | wazn=—
```

**Locus:** L3 (`layer3.py` role rules) plus the root-aligner (`root_by_alignment.py`). Comparatives on the pattern أَفْعَل (`أَقْسَط`, `أَقْوَم`, `أَدْنى`, `أَكبَر`, `أَطوَل`) are tagged as generic مرفوع nouns with wazn=`فعل` (uninformative).

**Root cause:** there is no explicit ISM_TAFDIL (comparative/superlative) subclass. The aligner finds a generic 3-letter root and stops, never recognizing the أَفْعَل comparative template.

**Expected behavior:** L3 emits `subclass=ISM_TAFDIL` and `wazn=أَفْعَل`. The role in 2:282 (`ذَٰلِكُمْ أَقْسَطُ … وَأَقْوَمُ … وَأَدْنى أَلَّا تَرتابوا`) is **خبر مرفوع** (predicate of demonstrative ذَٰلِكُمْ), with `وَأَقْوَمُ` and `وَأَدْنى` as coordinated خبرَيْن.

**Contract name:** `ComparativeAdjectiveContract:v1`.

**Applies to:** any token matching أَفْعَل / فُعْلى comparative templates. Negative: regular nouns on فَعْل / فُعْل / فِعْل templates.

**Current status in working tree:** **none.**

---

### B12. PassiveVerbContract

**Symptom from 2:282 (lines 234, 269):**
```
دُعُوا               → class=FIIL | role=فعل ماضٍ | root=دعع | wazn=فعل
يُضَآرَّ              → class=FIIL | role=فعل مضارع | root=— | wazn=—
```

Both are passives — `دُعوا` (they were called), `يُضَارَّ` (let no one be harmed). Neither carries `voice=passive` metadata; the L5 event extractor then fabricates an agent (line 626: `agent_of: ٱلشُّهَدَآءُ → يَأْبَ` near these) because nothing tells it the verb is passive.

**Locus:** `i3rab_engine/layer1.py` — verb-form contract does not flag passive voice. The damma-fatha-sukun pattern (`دُعِيَ` / `يُضَارَّ`) is a known passive marker but no rule detects it.

**Expected behavior:** L1 / L3 produce `voice=passive` for surfaces matching:
- Past passive `فُعِلَ` family (damma on first, kasra on second).
- Imperfect passive `يُفعَل` family (damma on yaa-prefix, fatha on third).
L5 then does **not** emit `agent_of` for passive verbs unless an explicit agent phrase exists (see family E18 below).

**Contract name:** `PassiveVerbContract:v1`.

**Applies to:** `دُعوا`, `يُضَارَّ`, `قُتِلَ`, `يُقْتَلُ`, `أُنزِلَ`, `يُنزَلُ`. Negative: active verbs `قَتَلَ`, `يَقْتُلُ`.

**Current status in working tree:** **none.**

---

## C. KB.SAM — overmatching bugs

### C13. OperatorMeaningRequiresCertifiedOperator + KBMeaningSurfaceOvermatchBlocker

**Symptom from 2:282 (lines 313, 319-321, 333-335, 382, 410-414):**
```
«وَلْيَكْتُب»:
    ? [ج3] الواو لِلقَسَم — تُجَرّ ما بَعدَها لِلقَسَم
    ? [ج103] واو رُبَّ — لِلتَّقليل،
    ? [ج4] واو القَسَم — حَرف جَرّ لِلقَسَم — أَكثَر حُروف القَسَم استِ
«كَاتِبٌ»:
    ? [ج1] كاف المُخاطَب لِلنَّصب وَ الجَرّ
    ? [ج3] الكاف لِلتَّشبيه — وَ هو الأَصل
    ? [ج3] الكاف لِلتَّعليل — قَرينَة سياقيَّة
«سَفِيهًا»:
    ? [ج4] السين — حَرف تَنفيس قَريب — يَدُلّ على المُستَقبَل القَريب
«وَٱسْتَشْهِدُوا۟»:
    ? [ج3] الواو لِلقَسَم — تُجَرّ ما بَعدَها لِلقَسَم
```

`كَاتِبٌ` retrieves meanings of the operator `كَاف` (الكاف لِلتَّشبيه); `سَفِيهًا` retrieves meanings of the operator `السِّين` (حرف تَنفيس); every token starting with `و` retrieves واو القَسَم / واو رُبَّ.

**Locus:** `clean_code/samarrai_analyzer.py` `analyze()` function (line 409). It calls `_try_strip_prefix(tok)` which returns candidates `(token, "full")`, `(prefix, "prefix")`, `(stripped, "stripped")`. The `"prefix"` candidate treats the bare leading letter as a standalone operator and looks it up in the four `samarrai_loaders` volumes, picking up واو القسم / كاف تشبيه / سين تنفيس regardless of whether the surface actually starts with a certified operator.

**Root cause:** `_try_strip_prefix` does not consult any "is-this-token-actually-an-operator?" gate. The very first letter is always treated as a potential operator candidate. This is the systemic root of the noise visible across all 2:282 KB.SAM entries.

**Expected behavior:** before retrieving meanings for `prefix`-stripped candidates, verify that the prefix is a **certified operator** in this context — i.e. that L1 / closed-class detection has flagged the leading letter as a real operator, not just a lexical letter. If not certified, the prefix-stripped candidate is dropped.

**Contract names:** `OperatorMeaningRequiresCertifiedOperator:v1` (gate) + `KBMeaningSurfaceOvermatchBlocker:v1` (the systemic filter at retrieval time).

**Applies to:** every token whose KB.SAM section currently contains operator-meaning rows for `و / ك / س / ل / ب / ف / ت` when those letters are not certified operators by L1.

**Current status in working tree:** **none.** Phase 4 work in working tree is about Layer 1 / `contextual_resolver` only; KB.SAM was not touched.

---

### C14. HamzaParticleIdentityGate

**Symptom from 2:282 (lines 337-338, 372-373):**
```
«أَن»:
    ✓ [ج4] إِن الشَّرطيَّة — حَرف جَزم لِفِعلَين (شَرط + جَواب) — أَصل 
    ✓ [ج4] إِنَّ في جَواب القَسَم — تَوكيد الجَواب
«فَإِن»:
    ? [ج4] فاء رابِطَة لِجَواب الشَّرط — تَلزَم إذا كانَ الجَواب جُملَة
    ? [ج4] إِن الشَّرطيَّة — حَرف جَزم لِفِعلَين (شَرط + جَواب) — أَصل 
    ? [ج4] إِنَّ في جَواب القَسَم — تَوكيد الجَواب
```

`أَنْ` (subjunctive particle) retrieves meanings of `إِنْ` (conditional) and `إِنَّ` (emphatic). These four particles share a plain form (`ان`) after diacritic strip and are distinguished only by harakat + shadda.

**Locus:** `samarrai_analyzer.lookup_word_all_volumes` and the underlying volume loaders. The lookup uses `match_type=exact_vocalized` first but falls back to plain match when the exact form is not found — and `إِن / إِنَّ / أَن / أَنَّ` are entered with `exact_vocalized` only for the canonical form, so any near-form falls through to plain match and pulls in all four.

**Root cause:** plain-fallback collapses 4 distinct particles to 1 key.

**Expected behavior:** the gate `HamzaParticleIdentityGate` enforces:
- `أَنْ` (fatha on hamza, sukun on noon) ⇒ subjunctive particle only.
- `أَنَّ` (fatha + shadda on noon) ⇒ emphatic ann.
- `إِنْ` (kasra on hamza, sukun on noon) ⇒ conditional particle.
- `إِنَّ` (kasra + shadda on noon) ⇒ emphatic inna.
- `أَلَّا` (fatha + shadda on lam) ⇒ أن + لا (per B6).
- `إِلَّا` (kasra + shadda on lam) ⇒ exception particle (لَيسَ لا الناهية).

No plain fallback across these six surfaces.

**Contract name:** `HamzaParticleIdentityGate:v1`.

**Current status in working tree:** **none.**

---

## D. L4 — Relation bugs

### D15. PossessorContract v2

**Symptom from 2:282 (lines 596, 614, 633, 651):**
```
? possessor_of       : بِٱلْعَدْلِ → كَاتِبٌ
? possessor_of       : بِٱلْعَدْلِ → وَلِيُّهُ
? possessor_of       : لِلشَّهَٰدَةِ → وَأَقْوَمُ
? possessor_of       : بِكُلِّ → وَٱللَّهُ
```

None of these are possessor relations:
- `بِٱلْعَدْلِ` is an adverbial phrase (with justice), not possessed by كاتب.
- `لِلشَّهَٰدَةِ` is the dative/benefactive of أَقْوَم (more upright **for** testimony), not possessed by أقوم.
- `بِكُلِّ` is part of `بِكُلِّ شَيْءٍ عَلِيمٌ` — an adverbial of عَلِيمٌ, not possessed.

**Locus:** `clean_code/relation_extractor.py`. The current possessor rule fires whenever a HARF_JARR phrase appears anywhere near a noun, without checking whether the structure is an actual iḍāfah.

**Root cause:** over-broad heuristic. Possession (إضافَة) in Arabic is marked structurally: noun + noun in genitive, or noun + possessive pronoun suffix, or explicit ownership lām in ownership context. PP-on-noun is **modifier/circumstantial**, not possession.

**Expected behavior:** `possessor_of` is emitted only for:
1. **Real iḍāfah** — two consecutive nouns, second is genitive, no PREP between them.
2. **Possessive pronoun suffix** — token surface ends in `ه / ها / هم / هن / كم / كن / ك / ي / نا` and the head is a noun.
3. **Ownership lām with ownership context** — `لِزَيدٍ كِتابٌ` style, with explicit ownership.

PPs from `بِ`, `لِ` (non-ownership), `كَ`, `عَنْ`, `إِلى`, etc. do **not** emit `possessor_of`.

**Contract name:** `PossessorContract:v2`.

**Current status in working tree:** **none.**

---

### D16. RelationDeduplicationGate

**Symptom from 2:282 (lines 609, 654, 619, 655, 640, 656):**
```
? ism_of_kana        : ٱلْحَقُّ → كَانَ              (line 609)
...
? ism_of_kana        : ٱلْحَقُّ → كَانَ              (line 654, duplicate)
? ism_of_kana        : فَرَجُلٌ → يَكُونَا           (line 619)
? ism_of_kana        : فَرَجُلٌ → يَكُونَا           (line 655, duplicate)
? ism_of_laysa       : جُنَاحٌ → فَلَيْسَ            (line 640)
? ism_of_laysa       : جُنَاحٌ → فَلَيْسَ            (line 656, duplicate)
```

**Locus:** `relation_extractor.py` — relation post-processing. The same relation is added twice from two different rules (the direct ism-of-kana detector and a fallback path).

**Root cause:** no dedup gate on `(relation_name, source_id, target_id, kind)`.

**Expected behavior:** before adding a relation to `RelationGraph.relations`, check the (name, source, target, kind) signature against existing relations. Skip if already present.

**Contract name:** `RelationDeduplicationGate:v1`.

**Current status in working tree:** **none.**

---

### D17. SubjectControlContract

**Symptom from 2:282 (line 658):**
```
? agent_of           : ⊕هُوَ → يَكْتُبَ
```

In the clause `وَلَا يَأْبَ كَاتِبٌ أَن يَكْتُبَ كَمَا عَلَّمَهُ ٱللَّهُ`, the subject of `يَكْتُبَ` is controlled by the matrix subject `كَاتِبٌ` (the writer himself writes), not a free implicit `هُوَ`.

**Locus:** L5 / L6 (implicit-subject generator in event / relation extractors). The system inserts an `⊕هُوَ` placeholder whenever a verb lacks an overt subject, without checking for a control relationship from a higher clause.

**Root cause:** no control-clause analysis.

**Expected behavior:** when a subordinate verb is the complement of a matrix verb (e.g. `يَأْبى أَن يَكتُبَ` — refuse to write), the subordinate subject is **shared** with the matrix subject. Emit `agent_of: كاتب → يكتب` and suppress the `⊕هُوَ` placeholder.

**Contract name:** `SubjectControlContract:v1`.

**Current status in working tree:** **none.**

---

## E. L5 — Event bugs

### E18. PassiveVerbNoAgentContract

**Symptom from 2:282 (lines 740-746):**
```
? Event[أبب]
    agent=ٱلشُّهَدَآءُ
    tense=present
    ...
? Event[دعع]
    tense=past
    ...
```

`Event[أبب]` actually corresponds to `يَأْبَ ٱلشُّهَدَآءُ` (the witnesses shall not refuse) — this one is active and the agent is correct. But `Event[دعع]` corresponds to `إِذَا مَا دُعُوا` (when they are called) — **passive**, and no agent should be fabricated.

**Locus:** `event_extractor.py`. The event extractor reads `agent_of` from `relation_graph` and copies it into the event. It does not check `voice=passive`.

**Root cause:** depends on B12 — without a passive marker upstream, the event extractor cannot know to suppress the agent. Even when B12 is fixed, the event extractor needs its own check.

**Expected behavior:** if `voice=passive` is set on the verb token, suppress `agent_of` extraction for that event. If a `بِواسِطَة X` agent phrase exists, mark it as `agent_of` Hypothesis with the `passive_explicit_agent` source.

**Contract name:** `PassiveVerbNoAgentContract:v1`.

**Current status in working tree:** **none.**

---

### E19. TemporalScopeContract

**Symptom from 2:282 — every event in lines 674-788 has `time=when_future`:**
```
? Event[امن] tense=past time=when_future          (line 674-676)
? Event[علم] tense=past time=when_future          (line 693-695)
? Event[فَلَيْسَ] tense=past time=when_future    (line 763-765)
? Event[تَبَايَعْتُمْ] tense=past time=when_future (line 772-774)
```

35 events, all carrying `when_future`. This is structurally false — past events do not happen in the future.

**Locus:** `event_extractor.py` lines ~250-260: `sentence_time_value` is computed once per sentence from the first time-adverb found (`إِذَا` → `when_future`). Then every event in the sentence inherits this time.

**Root cause:** the temporal scope of `إِذَا` is **the conditional clause** (the protasis + apodosis), not the entire verse. A verse like 2:282 chains multiple conditionals + parenthetical comments; the global `when_future` overreaches.

**Expected behavior:** scope `إِذَا`'s temporal value to its clause (segmented via L2 / clause boundary detector). Past-tense events outside the apodosis keep `time=None` or `past`. Past events inside the protasis (`إِذَا تَدَايَنتُم` — when you contract a debt) are themselves the protasis-action and should be tagged `tense=past` + `time=conditional_antecedent`, not `when_future`.

A simpler first-pass rule (already partially implemented as a draft in working tree under `EVENT_TIME_TENSE_GATE_SPEC.md`): a tense/time compatibility matrix that rejects past+when_future. The full `TemporalScopeContract` extends this with clause-scoping.

**Contract name:** `TemporalScopeContract:v1`. (PHASE 5 should include both the simple tense/time gate AND the clause-scoping.)

**Current status in working tree:** **partial draft.** `EVENT_TIME_TENSE_GATE_SPEC.md` + CSV cover the tense compatibility check. They do **not** cover clause-scoping. PHASE 5 will need to extend.

---

### E20. EventNamingNormalizationContract

**Symptom from 2:282 (multiple lines in 674-788):**
```
? Event[امن]              (root-based, good)
? Event[علم]              (root-based, good)
? Event[فَٱكْتُبُوهُ]      (surface-based, with prefix)
? Event[وَلْيَكْتُب]      (surface-based, with conjunction + lam-amr)
? Event[فَلَيْسَ]         (surface-based, with prefix)
? Event[وَأَشْهِدُوٓا]     (surface-based)
? Event[تَبَايَعْتُمْ]    (surface-based)
? Event[يُضَآرَّ]         (surface-based)
? Event[وَٱتَّقُوا]       (surface-based)
```

Some events are named by root (`علم`, `امن` — correct), others by surface form including prefixes (`فَٱكْتُبُوهُ` — wrong).

**Locus:** `event_extractor.py` lines ~296-297:
```python
verb_text = getattr(t, "token", "") or getattr(t, "surface", "")
event_type = (t.root or "—") if t.root else verb_text
```

When `t.root` is empty (because L2 wazn alignment failed for that token), `event_type` falls back to the full surface. This happens for every verb whose segmentation/alignment failed — typically the lām al-amr forms (`وَلْيَكْتُب` etc.).

**Root cause:** A2 + A3 propagate here. When L1/L2 fail upstream, L5 falls back to surface as the event ID — losing the canonical root and making event aggregation impossible (`Event[علم]` and `Event[وَيُعَلِّمُكُمُ]` would never aggregate even though they share root علم).

**Expected behavior:** the `Event` schema separates three fields:
- `surface` — the full surface form (e.g. `وَلْيَكْتُب`).
- `lemma` / `root` — the canonical root (e.g. `كتب`).
- `normalized_event_type` — the canonical event identifier used for aggregation (e.g. `EVENT:كتب`).
When `t.root` is empty, the event extractor uses Hypothesis with `event_type=UNKNOWN` and a blocker `upstream_root_extraction_failed`, rather than silently using the surface.

**Contract name:** `EventNamingNormalizationContract:v1`.

**Current status in working tree:** **none.** Event schema already has `verb_surface` and `type` as separate fields, but `type` is misused as both lemma and surface fallback.

---

## F. L6 — Resolution bugs

### F21. RelativePronounInternalClauseContract

**Symptom from 2:282 (lines 794-795):**
```
? relative          : ٱلَّذِى → ٱللَّهُ (+7 alts)
? relative          : ٱلَّذِى → شَيْـًٔا (+11 alts)
```

In `ٱلَّذِى عَلَيْهِ ٱلْحَقُّ` (the one against whom is the debt), `ٱلَّذِى` introduces a relative clause; its antecedent is **the debtor** (an implicit entity in the surrounding context — the contracting party), not any random preceding noun.

**Locus:** `resolution_engine.py` `_resolve_relative` — the current rule picks the nearest preceding noun matching gender/number. For `ٱلَّذِى` (masc-sg) in 2:282, this finds `ٱللَّهُ` (preceded earlier in `عَلَّمَهُ ٱللَّهُ`) or `شَيْـًٔا` (later). Both wrong.

**Root cause:** the resolver searches for an antecedent **outside** the relative clause, even when the clause itself contains the descriptive content of the antecedent. The structure `ٱلَّذِى عَلَيْهِ ٱلْحَقُّ` is itself the descriptor; the antecedent is an implicit "the one" (= the debtor, contextually).

**Expected behavior:** when a relative pronoun introduces a **content-bearing** صلة (relative clause), the system should:
1. Build the internal clause structure (PP + main NP).
2. Set the antecedent as `IMPLICIT_REFERENT` with a description derived from the clause content.
3. Defer concrete resolution to discourse-level context (the larger verse / paragraph), not to nearby random nouns.

**Contract name:** `RelativePronounInternalClauseContract:v1`.

**Current status in working tree:** **partial.** `L6_RELATIVE_WORDCLASS_GATE_SPEC.md` draft filters out `مِن / مِنَ / مَا` from the relative resolver (false-positive HARFs). It does **not** address the antecedent-selection bug for genuine relatives like ٱلَّذِى.

---

### F22. VocativeRelativeAttachmentContract

**Symptom from 2:282 (line 793):**
```
✗ relative          : ٱلَّذِينَ → بِلا مَرجِع
```

In `يَٰٓأَيُّهَا ٱلَّذِينَ ءَامَنُوٓا۟`, `ٱلَّذِينَ` is not a true relative clause — it is **vocatively attached** to `يَا أَيُّها` (a vocative construction). The `ٱلَّذِينَ` is in apposition to `أَيُّها`, naming the addressees. Marking it `بِلا مَرجِع` (no antecedent) is misleading.

**Locus:** `resolution_engine.py` — the resolver has no special-case for vocative attachment.

**Expected behavior:** when `ٱلَّذِينَ` follows a vocative construction (`يَا أَيُّها`), attach it to the vocative as the addressee identifier. Emit `vocative_attachment: ٱلَّذِينَ → يَا أَيُّها` (or equivalent). The antecedent is the discourse audience.

**Contract name:** `VocativeRelativeAttachmentContract:v1`.

**Current status in working tree:** **none.**

---

### F23. PronounAntecedentRoleFilter

**Symptom from 2:282 (line 792):**
```
? anaphora          : هُوَ → ضَعِيفًا (+14 alts)
```

In `أَوْ لَا يَسْتَطِيعُ أَن يُمِلَّ هُوَ`, the explicit detached pronoun `هُوَ` emphasizes the subject of `يُمِلَّ`. That subject is `ٱلَّذِى عَلَيْهِ ٱلْحَقُّ` (the debtor) — not the adjective `ضَعِيفًا` that occurs nearby as a خبر.

**Locus:** `resolution_engine.py` `_resolve_anaphora` — the resolver ranks candidate antecedents by proximity / gender / number, but does not filter by **syntactic role**. `ضَعِيفًا` (an adjective in خبر position) should never be a legitimate antecedent for a personal pronoun: only entity-bearing roles (subject, object, مبتدأ) can host anaphora.

**Expected behavior:** filter candidate antecedents by role. Acceptable host roles: مبتدأ, فاعل, مفعول به, اسم كان, خبر كان (if it is itself a referring noun, not an attribute). Reject: نَعت (modifier), حال (circumstantial), خبر that is an adjective phrase.

**Contract name:** `PronounAntecedentRoleFilter:v1`.

**Current status in working tree:** **none.**

---

## G. L7 — Graph sanity bugs

### G24a (the "consistency lie")

**Symptom from 2:282 (line 807):**
```
مُتَّسِق: نَعَم ✓
```

despite (1) 6 constitutional violations on the Jalalah, (2) 7 of 7 wrong L6 resolutions, (3) 35 events with broken time tags, (4) duplicate L4 relations.

**Locus:** `meaning_assembler.py` — the consistency check counts only schema-level invariants (no node referenced twice, no edge with missing endpoints), not semantic invariants.

**Expected behavior:** introduce semantic sanity metrics (deferred to PHASE 8 per the governance prompt — see I below). For PHASE 0, document only that the current `مُتَّسِق=نَعَم` is misleading and that the assembler should expose `semantic_sanity_score`, `qa_answer_type_error_count`, `relation_type_error_count`.

**Contract name:** `GraphSemanticSanityMetrics:v1` (PHASE 8).

**Current status in working tree:** **none.**

---

## H. L8 — Q/A answer type bugs

### H24. QAAnswerTypeGate

**Symptom from 2:282 (lines 813-824):**
```
✅ ماذا حَدَث؟
    ? [Hypothesis] ٱللَّهَ / شَيْـًٔا / إِحْدَىٰهُمَا / صَغِيرًا / كَبِيرًا
✅ أَين حَدَث؟
    ? [Hypothesis] أَجَلٍ / رِّجَالِكُمْ / أَجَلِهِ
✅ متى حَدَث؟
    ? [Hypothesis] when_future / tense:command / tense:past / tense:present
✅ ما تَسَلسُل الأَحداث؟
    ? [Hypothesis] ٱللَّهَ / شَيْـًٔا / إِحْدَىٰهُمَا / صَغِيرًا / كَبِيرًا
✅ إلى ماذا تَحَوَّلَ شَيء؟
    ? [Hypothesis] ٱللَّهَ / شَيْـًٔا / إِحْدَىٰهُمَا / صَغِيرًا / كَبِيرًا
```

- **ماذا حَدَث؟** returns patient nouns (objects), not events. The question asks about events.
- **أَين حَدَث؟** returns `أَجَلٍ` (a time term meaning "specified period") and `رِجَالِكُمْ` (men, not a place) and `أَجَلِهِ` (its term, also time). Zero locations.
- **متى حَدَث؟** returns meta-labels (`tense:past`, `tense:present`) rather than temporal anchors (`إِذَا تَدَايَنتُم`).
- **ما تَسَلسُل الأَحداث؟** returns the same list as "ماذا حَدَث" — sequencing was never computed.
- **إلى ماذا تَحَوَّلَ شَيء؟** also returns the same list — no transformation analysis ran.

**Locus:** `reasoning_engine.py`. Each Q/A function returns a flat list of patients/objects without consulting the correct relation/event subgraph for the question type.

**Expected behavior — per-question routing:**

| Question | Correct source |
|----------|----------------|
| مَن الفاعِل؟ | `relation_graph.relations` filtered by `name == "agent_of"` |
| ماذا حَدَث؟ | `event_graph.events` (list of Event objects, formatted as `Event[lemma]`) |
| أَين حَدَث؟ | `relation_graph` filtered by `name ∈ {in_location, on_surface, direction_to, from_source}` AND target word_class is location-bearing |
| متى حَدَث؟ | `relation_graph` filtered by `name ∈ {at_time, during_time}` + `event.time` when set + `event.time_value` (the temporal-anchor word, e.g. `إِذَا`) |
| ما تَسَلسُل الأَحداث؟ | `event_graph.events` ordered by `verb_position` |
| إلى ماذا تَحَوَّلَ شَيء؟ | `Transformation` subgraph (from `event_extractor`'s transformation list); if empty → `Zero` |

**Contract name:** `QAAnswerTypeGate:v1`.

**Current status in working tree:** **none.**

---

## I. Proposed implementation phases

The phasing follows the governance prompt verbatim. Each phase has explicit non-goals (the "do NOT touch" list).

| Phase | Scope | Bug families | Files (expected) |
|---|---|---|---|
| **PHASE 0** | docs only | (this file) | `docs/bugs/BUGS_FROM_2_282_DETAILED.md` |
| **PHASE 1A** | segmentation lock | A1 ClosedFormSegmentationLock | `segmenter.py`, CSV |
| **PHASE 1B** | segmentation rule | A2 LamAlAmrSegmentationContract | `segmenter.py`, possibly CSV |
| **PHASE 1C** | segmentation rule | A3 PastSuffixBeforeImperfectPrefixContract | `segmenter.py` |
| **PHASE 2** | KB.SAM gates | C13, C14 | `samarrai_analyzer.py` |
| **PHASE 3** | L3 morphology / case | B4, B5, B6, B7, B8, B10, B11, B12, A9 | `i3rab_engine/layer1.py`, `layer2.py`, `layer3.py`, `root_by_alignment.py`, `normalizer.py` |
| **PHASE 4** | L4 relations | D15, D16, D17, E18 (Verb-in-clause certification, B12 dependency) | `relation_extractor.py` |
| **PHASE 5** | L5 events | E19, E20, + lām-al-amr mood propagation | `event_extractor.py`, `event_schema.py` |
| **PHASE 6** | L6 resolution | F21, F22, F23, + Min/Man inner resolver | `resolution_engine.py` |
| **PHASE 7** | L8 Q/A | H24 | `reasoning_engine.py` |
| **PHASE 8** | metrics | G24a / GraphSemanticSanityMetrics | `meaning_assembler.py` |

**Cross-phase invariants:**
- Each phase commits independently.
- Each phase has a checkpoint: `python3 clean_code/analyze_verse_v3.py --verse 2:282 --all > checkpoints/2_282/phase<N>_after.txt`, diffed against the previous checkpoint.
- Each phase reports MASAQ-alignment delta separately from "Arabic accuracy" claims.
- No phase introduces new Certificate emissions unless its own contract is the source.

**Dependencies between bug families (for reordering decisions if needed):**
- E18 depends on B12 (passive marker must exist before agent suppression can fire).
- E19 (full version with clause scoping) depends on a clause segmenter, which is M1.A — out of scope until that lands.
- F23 depends on B11 (must know which tokens are adjectives vs nouns to filter them as antecedents).
- H24 depends on E20 (must have normalized event names to answer "ماذا حَدَث").

**Working-tree reuse decision (for PHASE 1+):**
The prior session's working-tree drafts (`JALALAH_PROTECTION_*`, `DEMONSTRATIVE_COMPOUNDS_ATOMIC_*`, `IV_PREFIX_ROOT_EXTRACTION_*`, `EVENT_TIME_TENSE_GATE_*`, `L6_RELATIVE_WORDCLASS_GATE_*`, `WAZN_FIELD_DISCIPLINE_*`, `SEGMENTER_DISPLAY_STEM_*`) overlap with families A1 (partial), A9 (display-only), E19 (partial), F21 (partial). PHASE 1 onwards may inspect those drafts but is free to supersede them with the contracts named in this spec. The drafts are **not** automatically promoted.

---

## J. Acceptance checklist

For each PHASE > 0:

- [ ] Phase scope matches §I exactly — no extra families touched.
- [ ] Each bug family in scope has:
  - [ ] Named contract (matches §A-§H).
  - [ ] Test file with positive AND negative cases.
  - [ ] Before/after example from 2:282 in the commit message.
- [ ] No unrelated drift (git diff shows only files declared in §I for that phase).
- [ ] `python3 clean_code/analyze_verse_v3.py --verse 2:282 --all` runs to completion.
- [ ] Diff of new `phase<N>_after.txt` vs `phase<N-1>_after.txt` (or `out_2_282_phase4_off.txt` for PHASE 1) shows only expected changes in the affected layers.
- [ ] MASAQ-alignment metric reported separately; no claim of "Arabic accuracy improved".
- [ ] No new Certificate emissions outside the phase's own contract.
- [ ] All prior phase tests still pass.
- [ ] Commit message format: `Phase <N>: <one-line scope> — <bug families addressed>`.

For PHASE 0 specifically (this document):

- [x] File created at `docs/bugs/BUGS_FROM_2_282_DETAILED.md`.
- [x] All 25 bug families from the governance prompt are documented (A1, A2, A3, A9, B4, B5, B6, B7, B8, B10, B11, B12, C13, C14, D15, D16, D17, E18, E19, E20, F21, F22, F23, G24a, H24).
- [x] Each family has: locus, root cause, expected behavior, contract name, applies-to.
- [x] Working-tree overlap noted honestly for each family that has a partial draft.
- [x] No source files modified.
- [ ] Commit created with message `Document detailed bug families from 2:282 audit`.

---

## Out of scope for this document

- No implementation. No code change. No test added.
- No MASAQ regression metrics computed.
- No estimates of how many Quran verses each bug affects.
- No commitment to which phases will actually be approved for execution.
- No promises about non-Quranic Arabic accuracy.
