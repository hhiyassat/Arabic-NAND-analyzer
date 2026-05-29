# NO DIACRITIC STRIPPING RULE
# لا إزالة للتشكيل

## Statement

**Arabic diacritics are part of linguistic identity, not optional ornamentation.**
الحركات جزء من الهوية اللغوية للكلمة، لا زينة قابلة للحذف.

Removing diacritics conflates words that are linguistically distinct (e.g., `مَن` the relative/interrogative/conditional pronoun vs `مِن` the preposition), produces false alignments, and invalidates any downstream analysis built on those alignments.

This rule applies to **all** code and tooling that handles Arabic linguistic comparison:

- analyzer logic (segmenter, classifier, role rules, relation extractor, event extractor, resolution engine, meaning assembler, KB.SAM, MAANI)
- the MASAQ diff and any successor evaluation harness
- temporary scripts under `/tmp` or anywhere outside the repo tree
- diagnostic dumps and audit reports
- automated tests (unit, regression, golden, characterization)
- written reports (Markdown, JSONL, console output)
- future tooling not yet written

There is no carve-out for "just diagnostics" or "just temporary code". If a piece of logic produces a comparison key that drives a decision — alignment, classification, mismatch family, or fix recommendation — that key must preserve linguistic diacritics.

## Diacritics that MUST be preserved in primary comparison

The eight linguistic vowel/consonant marks that distinguish Arabic word identity:

| Mark | Codepoint | Name |
|---|---|---|
| `َ` | U+064E | fatha |
| `ُ` | U+064F | damma |
| `ِ` | U+0650 | kasra |
| `ً` | U+064B | fathatan (tanwīn fath) |
| `ٌ` | U+064C | dammatan (tanwīn damm) |
| `ٍ` | U+064D | kasratan (tanwīn kasr) |
| `ّ` | U+0651 | shadda |
| `ْ` | U+0652 | sukūn |

All eight must survive any normalization step used as a **primary comparison key**.

## Quranic-only marks — what MAY be folded or removed

The following marks are Quranic recitation aids or visual-presentation artifacts. They carry no linguistic identity by themselves; MASAQ MSA spelling does not include them. They may be folded or removed in normalization helpers used for comparison:

| Mark | Codepoint | Action |
|---|---|---|
| `ٱ` | U+0671 (wasla alif) | fold → `ا` (same sound) |
| `آ` | U+0622 (alif madda) | fold → `ا` (MASAQ writes plain ا) |
| `ٰ` | U+0670 (dagger alif) | remove (MASAQ writes هذا, not هاذا) |
| `ٓ` | U+0653 (madd mark) | remove |
| `۟` | U+06DF (small high zero) | remove |
| `ـ` | U+0640 (tatweel) | remove (visual only) |

This is consistent with how the MTL lookup, the diacritic-safe MASAQ diff, and the UninflectedVerbContract lexicon already operate: they fold Quranic-only marks while preserving the eight linguistic diacritics.

## Forbidden as primary logic

The following operations must NOT appear in any primary comparison key, alignment routine, classification rule, or fix-recommendation pipeline:

- Stripping fatha (`َ`)
- Stripping damma (`ُ`)
- Stripping kasra (`ِ`)
- Stripping sukūn (`ْ`)
- Stripping shadda (`ّ`)
- Stripping any tanwin (`ً`, `ٌ`, `ٍ`)
- Using a plain/stripped Arabic form as the **primary** key for alignment, role/class comparison, or family classification
- Aligning `مَن` with `مِن` because both reduce to `من` after stripping
- Producing bug-family recommendations or fix priorities from stripped-diacritic comparison output

## Allowed only as a secondary diagnostic

A stripped-diacritic form may exist in a tool as a **secondary, clearly-labelled diagnostic field**:

- Acceptable field names: `diagnostic_plain`, `diag_plain`, `diag_plain_masaq`, `diag_plain_analyzer`
- The field must be clearly named with a `diag_*` or `diagnostic_*` prefix
- The field MUST NOT drive: alignment decisions, mismatch classification, or fix recommendation
- The field MAY be used for: human-readable JSONL output, fuzzy debug grep, exploratory triage logs

If a diagnostic field is consulted in a way that influences a decision, that consultation is a violation of this rule.

## Worked examples

The following pairs are linguistically distinct words; they must never collide in primary comparison:

- `مَن` ≠ `مِن`
- `مَنْ` ≠ `مِنْ`
- `مَنِ` ≠ `مِنِ`
- `مَا` ≠ `مَآ` (though Quranic-mark fold of `آ`→`ا` makes them equal — this is acceptable because `آ` is in the Quranic-fold allowlist)
- `حَقَّ` ≠ `حَقٌّ` (tanwīn distinguishes)
- `كَتَبَ` (PV verb) ≠ `كُتُب` (ISM plural) — both stripped to `كتب`

Any tool that treats these pairs as equal in its primary comparison key is broken and must be fixed before its output is trusted for prioritization.

## Governance

1. **Any report using stripped forms as primary comparison is INVALID for family prioritization.** Family counts, suspect-token rankings, and recommended-next-family conclusions drawn from such a report do not carry forward.
2. **Previous stripped-diacritic MASAQ reports are invalid for new recommendations unless independently revalidated** under the diacritic-preserving methodology. Specifically: any MASAQ diff output produced before the diacritic-safe runner was introduced should be re-derived before its findings drive a code change.
3. **Any future exception to this rule requires explicit written approval** from the project owner, recorded in a successor RULE_LOCK document. No verbal or implicit exceptions.

## Note on already-validated fixes

The following committed fixes were validated by direct production tests against the analyzer's vocalized output (not by stripped-diacritic MASAQ comparison alone). They remain valid under this rule:

- **`c744094`** — `MASAQ F3: recover verb classifications via lookup fallback`
  Validates correct FIIL/aspect classification on Quranic surfaces via the MTL Quranic-mark-fold + strict-form fallback. Tests assert exact-vocalized surface match for each target verb.
- **`fe36ca9`** — `MASAQ F3: suppress false genitive naat roles`
  Validates the إضافة-vs-نعت guards (functional-locative prev, pronoun-suffix host) via direct L3 role-phrase assertion on the verses’ analyzer output. No stripped form involved.
- **`4c8b953`** — `MASAQ F3: certify uninflected verb forms`
  Lexicon entries are stored fully vocalized; the detector folds only Quranic-only marks before exact-match lookup. Tests assert FIIL/PV on exact analyzer surfaces.

The MASAQ F3 family counts that **motivated** these fixes were derived from the older diacritic-stripping methodology, but the **acceptance criteria** for each fix were exact-vocalized production assertions. Those acceptance criteria remain sound under this rule.

Any future fix proposed off a stripped-diacritic family count must, before implementation, either:
- Re-derive the family count under the diacritic-preserving methodology and confirm the cluster size, or
- Justify on first principles why the specific surfaces being fixed are correct binding errors regardless of the family-count context.
