# LESSON_v2 — proof_trace_hash ≠ old_nand

**التاريخ**: 2026-05-21
**السياق**: بعد أرشفة `old_nand` (LESSON.md)، اقتَرَح المستخدم تصميمًا
جديدًا للـ hash يَلتزم بقاعدة:

> **hash must not be source-of-claim**

نُفِّذ في `clean_code/integrity_seal.py`.

---

## الفرق الجوهريّ

|  | old_nand | proof_trace_hash |
|---|---|---|
| **يَدَّعي ماذا؟** | «هذه الإحداثيّة السياقيّة للكلمة» | «هذه الشهادة لم تُعدَّل» |
| **مدخله** | حقول التحليل الـ semantic (word_class, root, wazn, case…) | الـ claims + الـ trace في صيغتها الـ canonical |
| **مكانه في البنية** | بَجانب الحقول التحليليّة، مُتساوٍ معها | داخل `integrity{}` فقط، مُنفصِل تمامًا |
| **يَنتهك source-of-claim؟** | ✓ نَعَم — يَدَّعي معرفةً بلا عقد | ✗ لا — كل claim له عقد مُسمّى، الـ hash ختم خارجيّ |
| **حذفه يَكسر التحليل؟** | لا، لكنّ ادّعاءه كان زائفًا | لا للتحليل، نَعَم للتدقيق الأَرشيفيّ |
| **يَخدم سؤال** | (يُفترض) التَّعَرُّف السياقي ← خطأ | تَوثيق ثابت قابل للمراجعة |

---

## القاعدة المُؤَسَّسة كاختبار assertion

في `integrity_seal.py`:

```python
def assert_hash_not_source_of_claim(record: dict) -> None:
    """Raise AssertionError if any claim cites a hash as its source."""
    for c in record.get("claims", []):
        src = (c.get("source") or "").lower()
        if "hash" in src or "sha256" in src:
            raise AssertionError(
                f"❌ claim {c['id']} cites hash as source: {src}"
            )
```

تُستدعى داخل `Engine.analyze_sentence` على كل token. لو حاول مُطَوِّر
يومًا أن يَضع `source: "sha256:..."`، النظام يَرفض تشغيله.

---

## البنية المُعتمدة (لكل token)

```yaml
TokenI3rab:
  token: خَالِدٌ
  word_class: ISM_MUARAB
  # ... الحقول الـ semantic ...

  # === القسم الجديد: structured proof ===
  claims:
    - id: word_class
      value: ISM_MUARAB
      source: wazn_aligner_nominal:فَاعِل      ← اسم عقد، لا hash
    - id: root
      value: خلد
      source: root_pipeline:wazn_aligner
    - id: case
      value: 1
      source: case_by_final_diacritic
    - id: tanwin
      value: ضم
      source: case_by_final_diacritic:tanwin_marker
    - id: role
      value: فاعل مرفوع
      source: faail_positional

  trace:
    - contract: Layer1:WordClassClassifier
      result: Hypothesis
    - contract: Layer2:CaseMarkClassifier
      result: Hypothesis
    - contract: Layer3:RoleClassifier
      result: Hypothesis

  residuals: [...]

  integrity:                                    ← مَوقع الـ hash الوحيد
    canonicalization: json-canonical-v1
    hash_algorithm: sha256
    proof_trace_hash: sha256:5ba7f715e6f7ea07…
```

---

## ما الذي تَغيّر في الكود

1. **أُنشِئ** `clean_code/integrity_seal.py`:
   - `compute_proof_trace_hash(claims, trace)` — الدالّة الـ hash الوحيدة
   - `seal(claims, trace)` → Integrity object
   - `assert_hash_not_source_of_claim(record)` — اختبار دستوريّ
   - `assert_integrity_section_separate(record)` — اختبار عَزل

2. **حُذِف** من `TokenI3rab`:
   - `old_nand_path`
   - `old_nand_hash`
   - `old_nand_hash_dotted`

3. **أُضِيف** إلى `TokenI3rab`:
   - `claims: list`
   - `trace: list`
   - `residuals: list`
   - `integrity: dict`

4. **يُحتسَب** في `Engine.analyze_sentence`:
   - بعد Layer 3، يُبنى claims + trace من مُخرَجات الطبقات
   - يُختَم بـ `seal(claims, trace)`
   - تُستَدعى الـ assertions تلقائيًّا

5. **يُعرَض** في `i3rab.py -v`:
   - `[الختم]: sha256:5ba7f715e6f7…` (مُختصَر للقراءة)

---

## الفحوصات تَمرّ

```
✓ assert_hash_not_source_of_claim — لا claim يَستند لـ hash
✓ assert_integrity_section_separate — الـ integrity لا تَتسلَّل
✓ determinism — نفس المُدخَل = نفس الـ hash
✓ canonical_json — sorted keys، UTF-8، sequential bytes
```

---

## الدرس البَنيويّ

> **الـ Proof Trace يَشرح. الـ hash يَختِم.**

old_nand كان hash يُحاول الشرح (وفَشِل).
proof_trace_hash هو hash يَختم (ولا يَدَّعي شَرحًا).

الفرق ليس في الـ algorithm — الاثنان SHA-256.
الفرق في **الدور الدستوريّ**.

النظريّة التي كَتَبَها المشروع (14_Minimal_Complete_Theory) تَنصّ:
«كل claim له عقد مُصدِر». الـ hash ليس عقدًا — هو ختم على نتيجة العقود.
ما دام الـ hash بَقي خارج فضاء الـ claims، لا انتهاك.
