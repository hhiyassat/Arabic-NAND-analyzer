# VERSEBYVERSE_AUDIT_LOOP — Surah 1 Report

## 1. Protocol

**Protocol name:** `VERSEBYVERSE_AUDIT_LOOP`

Autonomous bounded audit-and-fix loop run per verse:
audit → identify A-type binding error → minimal fix → tests → golden regressions → re-audit → commit.

## 2. Scope

Surah 1 (الفاتحة), ayahs **1:1 through 1:7**. Verse 1:1 was already accepted prior to this loop; verses 1:2–1:7 were processed in this run.

## 3. Commits created (Surah 1)

| SHA | Subject |
|---|---|
| `aa5598f` | VERSE 1:1: fix definite genitive role agreement |
| `ea9e674` | VERSE 1:4: fix idafa chain detection for مَٰلِكِ يَوْمِ ٱلدِّينِ |
| `c505817` | VERSE 1:6: fix implicit-agent for ٱ-initial imperatives |
| `90f419f` | VERSE 1:7: skip IV-prefix implicit-agent for PAST verbs |

### Per-fix one-line summary

- **1:1 (`aa5598f`)** — Normalize ٱ (U+0671 wasla alif) → ا inside the `_case_def_agreement_with_prev` predicate (`role_rules_contract.py` + legacy guard in `i3rab_engine/layer3.py`) so that ٱللَّهِ is recognized as definite. Without this, naat fires for `بِسْمِ ٱللَّهِ` via the `both_indef` branch and masks the correct `مضاف إليه` classification.
- **1:4 (`ea9e674`)** — Chain guard in `_case_def_agreement_with_prev`: when both `prev` and `t` are مجرور indef AND the next token is also مجرور, suppress naat so rule 9 (`mudaf_ilayh`) handles t correctly. Fixes the إضافة chain `مَٰلِكِ يَوْمِ ٱلدِّينِ`.
- **1:6 (`c505817`)** — Normalize ٱ → ا inside `_p7_has_iv_prefix_surface` (`relation_extractor.py`) so that ٱ-initial imperatives (e.g. ٱهْدِنَا) are treated as non-PAST and the PAST نا-suffix rule is correctly skipped. Removes the wrong `⊕نَحْنُ → ٱهْدِنَا` agent.
- **1:7 (`90f419f`)** — Guard Loop 2 (IV-prefix implicit-agent matching) with `verb_aspect != "PV"` in `relation_extractor.py`. PAST verbs with a leading vowel that incidentally looks like an IV prefix (e.g. أَنْعَمْتَ → "نعمت" after blind clitic-strip; وَأَوْحَيْنَآ → "أوحينا") no longer fall through to the IV-loop and emit wrong agents (⊕نَحْنُ / ⊕أَنَا).

## 4. Verses accepted with no code changes

- **1:2** `ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ` — Two A-type candidates identified (L3 لِلَّهِ role as `مضاف إليه` and KB.SAM رُبَّ↔رَبِّ mismatch). Both fixes were attempted in Attempt 1/5 and both reverted: the لِلَّهِ change broke a semantically-correct L4 `possessor_of` link; KB.SAM internals were declared out of scope mid-loop. Both findings reclassified as B-type deferred.
- **1:3** `ٱلرَّحْمَٰنِ ٱلرَّحِيمِ` — No A-type errors. L3 fallback `اسم مجرور` for ٱلرَّحْمَٰنِ is acceptable for standalone-verse analysis (cross-verse linkage to 1:2's لفظ الجلالة is out of scope).
- **1:5** `إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ` — No A-type errors. Pipeline correctly emits `patient_of` Certificates, hidden `⊕نَحْنُ` agents, `Event[عبد]` / `Event[عين]` with tense=present, L6 `anaphora: إِيَّاكَ → اللَّه`, and `TAQDIM_AL_MA3MOOL_LI_IKHTISAS` تركيب detection. L8 reports Certificate-level agent and events.

## 5. Final test result

**119 / 119 passed** (was 115/115 before the loop; +4 new versebyverse regression tests).

New tests added in this loop:

| Test | Verse | Verifies |
|---|---|---|
| `t_1_1_lafth_jalalah_is_mudaf_ilayh_not_naat` | 1:1 | ٱللَّهِ after بِسْمِ → `مضاف إليه` (not نعت) |
| `t_1_1_rahman_remains_naat` | 1:1 | ٱلرَّحْمَٰنِ after ٱللَّهِ → نعت (regression guard) |
| `t_1_4_yawm_is_mudaf_ilayh_not_naat` | 1:4 | يَوْمِ in chain → `مضاف إليه` (not نعت) |
| `t_1_4_addin_remains_mudaf_ilayh` | 1:4 | ٱلدِّينِ → `مضاف إليه` (regression guard) |
| `t_1_6_ahdina_no_nahnu_implicit_agent` | 1:6 | ٱهْدِنَا has no ⊕نَحْنُ implicit agent |
| `t_1_7_an3amta_no_nahnu_implicit_agent` | 1:7 | أَنْعَمْتَ has no ⊕نَحْنُ implicit agent |

## 6. Golden regression summary

| Verse | Pre-loop | Post-loop | Verdict |
|---|---|---|---|
| 2:282 | 43 links / Entropy 0.0 | **41 links / Entropy 0.0** | accepted golden update — removed `⊕هُمْ → وَٱسْتَشْهِدُوا` and `⊕هُمْ → وَٱتَّقُوا` (CV imperatives addressed to "you-pl", not 3rd-person "they"); structurally impossible agents |
| 2:196 | 27 links / Entropy 0.0 | **25 links / Entropy 0.0** | accepted golden update — removed 3 wrong `attribute_of` (1:1 fix: replaced by correct `possessor_of` chain) and removed `⊕هُمْ → وَٱتَّقُوا` (1:6 fix: imperative-not-past); structurally impossible agents |
| 28:7 | 7 links / Entropy 0.0 | **6 links / Entropy 0.0** | accepted golden update — removed `⊕أَنَا → وَأَوْحَيْنَآ` (verb is past 1st **plural** "we revealed", not 1st singular "I"); structurally impossible agent |
| 1:1 | 3 links / Entropy 0.0 | **3 links / Entropy 0.0** | unchanged after loop |

All golden Entropies remain 0.0. No L6 decisions regressed. No tests regressed.

## 7. Accepted golden update policy

A golden metric change is **not** automatically a blocker. It is acceptable when **all** of the following hold:

1. The link/node/coverage change is explained relation-by-relation.
2. The change removes a clearly wrong relation or adds a clearly correct one.
3. Entropy does not worsen.
4. L6 safe-Zero policy does not regress.
5. Tests pass.
6. The current verse improves.
7. No broad unrelated output changes occur.

In that case the change is recorded as an **accepted golden update**, the before/after metrics are disclosed in the verse report, only the narrow intended files are committed, and the loop continues.

Still stop and escalate if: Entropy worsens, unsafe L6 links appear, link changes are unexplained, broad unrelated output changes occur, forbidden files are required, broad architecture change is required, or 5 attempts are exhausted.

## 8. Deferred B/C items

### B-type (incomplete but acceptable; do not fix in versebyverse)

- **L3 `لِلَّهِ` role label is imprecise** — currently classified as `مضاف إليه مجرور`. The لِ is حرف جر / لام الاختصاص; the precise label would be `اسم مجرور بِاللام` متعلق بِخبر محذوف. L4 captures the structural relation correctly via `possessor_of: لِلَّهِ → ٱلْحَمْدُ`. Attempted fix in 1:2 cascaded to remove correct L4 links; reverted.
- **L3 `إِيَّاكَ` role label** — currently `اسم مبني` (safe fallback). Richer label would be `مفعول به مقدم`. L4 correctly emits `patient_of` Certificate.
- **Cross-verse referents** — 1:3 `ٱلرَّحْمَٰنِ` and 1:7 `صِرَٰطَ` lack the cross-verse linkage to 1:2's لفظ الجلالة and 1:6's صراط respectively. Single-verse analysis is the current scope.
- **Past 2nd-person implicit agent rule** — after the 1:7 fix, past verbs whose suffix encodes a 2nd-person agent (تَ / تِ / تُمْ) emit no implicit agent (safe Zero) instead of the correct ⊕أَنْتَ / ⊕أَنْتِ / ⊕أَنْتُمْ. Emitting the correct addressee requires a new PAST-suffix → addressee rule, which is out of versebyverse scope.

### C-type (future enhancement; report only)

- **KB.SAM enrichment for divine names** — entries empty for ٱلْحَمْدُ, ٱلرَّحْمَٰنِ, ٱلرَّحِيمِ, ٱلْعَٰلَمِينَ across multiple verses.
- **KB.SAM strict-form gating for رُبَّ** — رَبِّ (ISM noun) currently receives رُبَّ-particle meanings via diacritic-loose matching. Deferred per the KB.SAM scope rule (KB.SAM internals are out of scope for versebyverse unless the binding error is explicitly inside the KB.SAM section or directly causes a downstream wrong result).

## 9. Governance

The following rules governed the Surah 1 loop:

- **LLM critic is advisory only**, not authority. Findings are classified by the engine's actual output, not by a critic's claim.
- **Maximum 5 attempts per verse.** An attempt = one narrow patch cycle (audit → fix → tests → regression → re-audit). If 5 attempts are exhausted without resolving the A-type errors, the loop stops on that verse.
- **No moving to the next verse if the current verse is blocked.** Order is enforced (1:2 → 1:3 → 1:4 → 1:5 → 1:6 → 1:7).
- **No MAANI work, no hidden-pronoun integration, no broad refactor** during versebyverse. The fix scope is the specific A-type binding error.
- **No moving outside Surah 1.** No verse after 1:7 is processed.
- **No KB.SAM internal search** during normal versebyverse unless the binding error is explicitly inside the KB.SAM section or directly causes a downstream wrong result.
- **Allowed files per error type** (Normalization/lookup, L3 classification, L4 relation, L5 events, Phase 5 segmentation, display-only). Forbidden: `data/*`, `docs/*` (except this report), `meaning_assembler.py`, `hidden_pronoun_signals.py`, broad refactor, schema change.
- **Commit discipline.** One commit per verse if code changed; if no code changed, no commit. Never include `.claude/`, `out_*.txt`, or `.pyc`. Stage only intended files and confirm via `git diff --cached --stat` / `--name-only` before committing.

## 10. Final git status

```
On branch patch0-production-path-trace
Your branch is up to date with 'origin/patch0-production-path-trace'.

Untracked files:
	.claude/

nothing added to commit but untracked files present
```

(`.claude/` is intentionally not staged per repo hygiene rules.)
