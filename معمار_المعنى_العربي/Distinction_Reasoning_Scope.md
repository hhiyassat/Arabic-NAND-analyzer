# حَسم نِطاق الاستِدلال (Reasoning Scope)
## بَوّابَة دُستوريَّة لِـ Phase G — قِمَّة المَعمار

> **تاريخ الحَسم:** 2026-05-23
> **الحالَة:** دُستوريّ — مَبدَأ تَأسيسيّ لِطَبَقَة 7 (Reasoning)
> **يُرجَع إِليه:** `15_Executive_Roadmap.md §4.G` + `12_Project_Scope_Declaration.md §4`

---

## 1. السُّؤال

ما الأَسئلَة الَّتي يَستَطيع المُحَلِّل الإِجابَة عَنها، وَ ما الَّتي يَجِب أَن يَرفُضها صَراحَةً؟

هذا أَخطَر سُؤال في المَشروع — لأنّ Reasoning Layer هي **المُخرَج النِّهائيّ لِلمُستَخدِم**.

---

## 2. داخِل النِّطاق (مَقبول)

أَسئلَة بِنيَويَّة-حَدَثيَّة قابِلَة لِلإِجابَة مِن الـ MeaningGraph:

| النَّوع | المِثال | المَصدَر |
|---|---|---|
| **WHO** | مَن قَرَأَ الكِتابَ؟ | agent_of(قرأ) |
| **WHAT** | ماذا قَرَأَ زَيدٌ؟ | patient_of(قرأ، agent=زَيد) |
| **WHEN** | مَتى قَرَأَ زَيدٌ؟ | event.tense + event.time_value |
| **WHERE** | أَينَ قَرَأَ زَيدٌ؟ | in_location(event) |
| **HOW** | كَيف قَرَأَ زَيدٌ؟ | manner(event) |
| **HOW-MANY** (M4) | كَم رَجُلًا جاءَ؟ | numeric extraction + count |
| **WHAT-RELATION** | ما العَلاقَة بَين زَيد وَ الكِتاب؟ | edges بَين nodeَين |
| **TRANSFORMATION** | إلى ماذا تَحَوَّلَ زَيد؟ | transformation.state_after |
| **SEQUENCE** | ما الَّذي حَدَثَ ثُمّ ماذا؟ | events بِالتَّرتيب |
| **EXISTS** | هَل ذُكِرَ زَيد في النَّصّ؟ | search nodes |

---

## 3. خارِج النِّطاق (مَرفوض دُستوريًّا)

```
لَو سُئِلَ المُحَلِّل أَيّ مِن هذه، يَجِب أَن يَرُدّ صَراحَةً:
«هذا خارِج نِطاقي. أَنا أُحَلِّل البِنيَة، لا أُفَسِّر.»
```

| النَّوع | المِثال | السَّبَب |
|---|---|---|
| **WHY (تَفسير قَصد)** | لِماذا قَرَأَ زَيدٌ الكِتابَ؟ | يَتَطَلَّب فَهم نِيَّة |
| **INTERPRETATION** | ما المَعنى الباطِن لِلآيَة؟ | اجتِهاد تَفسيريّ |
| **JUDGMENT** | هَل فِعل زَيدٍ صَحيح؟ | حُكم أَخلاقيّ/فِقهيّ |
| **PROPHECY** | ماذا سَيَحدُث بَعد ذلِك؟ | تَنَبُّؤ |
| **AESTHETIC** | هَل هذه الآيَة جَميلَة؟ | حُكم ذاتيّ |
| **METAPHOR** | ما المَجاز هُنا؟ | research frontier |
| **THEOLOGY** | ما الحُكم الفِقهيّ؟ | يَتَطَلَّب أُصول الفِقه |
| **MOTIVATION** | لِماذا قالَ اللَّه ذلِك؟ | اجتِهاد لاهوتيّ |

---

## 4. القاعِدَة الذَّهَبيَّة

```
ALGORITHM answer_query(question):
    q_type = classify_question(question)

    if q_type in IN_SCOPE_TYPES:
        return query_meaning_graph(question)
    elif q_type in OUT_OF_SCOPE_TYPES:
        return RejectedAnswer(
            reason="خارِج النِّطاق التِّقنيّ",
            recommendation="تَوَجَّه لِمُتَخَصِّص (مُفَسِّر، فَقيه، أَديب)",
            kind="Zero"
        )
    else:
        return HypothesisAnswer(
            "لا أَستَطيع تَصنيف السُّؤال بِيَقين",
            alternatives=[...]
        )
```

---

## 5. WHY الخاصّ — حالَة مُختَلَطَة

**WHY السَّبَبيّ البُنيَويّ** (مَقبول):
- «لِماذا قُتِلَ الرَّجُل؟» إِذا كانَت الجُملَة فيها «بِسَبَب الكَذِب» → نَفحَص harf_jarr=بِسَبَب
- المُحَلِّل يُرجِع **العِلَّة المَذكورَة صَريحًا** فَقَط

**WHY التَّأويليّ** (مَرفوض):
- «لِماذا فَعَلَ ذلِك؟» إِذا لَم يُذكَر سَبَب في النَّصّ → خارِج النِّطاق
- المُحَلِّل لا يَخمِن

```python
def answer_why(question, graph):
    target_event = find_event(question, graph)
    cause = find_explicit_cause(target_event, graph)  # بحث عَن «بِسَبَب»، «لأنّ»
    if cause:
        return Certificate(cause)
    else:
        return Zero("لَم يُذكَر سَبَب صَريح في النَّصّ. التَّفسير خارِج نِطاقي.")
```

---

## 6. نِظام الإِجابَة (Schema)

```python
@dataclass
class Query:
    raw_text: str             # السُّؤال كَما طُرِحَ
    query_type: str            # who | what | when | where | how | how_many | exists | relation
    target_entity: Optional[str]
    target_event: Optional[str]
    is_in_scope: bool

@dataclass
class Answer:
    query: Query
    kind: Literal["Certificate", "Hypothesis", "Zero"]
    contract: str             # مِن أَيّ عَقد جاءَت الإِجابَة؟
    answer: Optional[str]     # النَّصّ النِّهائيّ
    evidence: list[str]       # node_ids + edge_ids المُستَخدَمَة كَدَليل
    alternatives: list[str]
    blockers: list[str]
    rejected_reason: Optional[str]  # لَو خارِج النِّطاق
```

---

## 7. مَعايير القَبول (مِن Roadmap §4.G)

- **دِقَّة الإِجابات البَسيطَة:** ≥ 70%
- **رَفض الأَسئلَة خارِج النِّطاق:** **100%** (لا اجتِهاد!)
- **تَتَبُّع كُلّ إِجابَة لِـ evidence:** 100%
- **كَشف الكَمّيّات (M4):** ≥ 95%

---

## 8. النَّتيجَة الدُّستوريَّة

> **المُحَلِّل في Phase G يَجيب فَقَط عَن أَسئلَة قابِلَة لِلِاستِدلال البُنيَويّ مِن الـ MeaningGraph.**
> **كُلّ سُؤال يَتَطَلَّب اجتِهاد بَشَريّ يُرفَض صَراحَةً بِـ Zero + سَبَب.**

البَوّابَة مَفتوحَة → Phase G التَّنفيذيَّة تَبدَأ.
