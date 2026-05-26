# حَسم Meaning vs Interpretation
## بَوّابَة دُستوريَّة لِـ Phase F

> **تاريخ الحَسم:** 2026-05-23
> **الحالَة:** دُستوريّ — مَبدَأ تَأسيسيّ لِطَبَقَة المَعنى
> **يُرجَع إِليه:** `15_Executive_Roadmap.md §4.F` + `12_Project_Scope_Declaration.md`

---

## 1. السُّؤال

ما الفَرق العَمَليّ بَين:
- **Meaning (المَعنى):** ما يَنبَني آليًّا مِن البِنيَة
- **Interpretation (التَّأويل):** ما يَحتاج اجتِهاد بَشَريّ

هذا الفَرق يُحَدِّد بِالضَّبط **ما يَخرُج المُحَلِّل** وَ **ما لا يَخرُج**.

---

## 2. التَّمييز العَمَليّ

### Meaning = «ما تَقوله الجُملَة بُنيَويًّا»

- يَنبَني آليًّا مِن: `entities + relations + events + resolutions`
- قابِل لِلتَّحَقُّق آليًّا (consistent / contradictory)
- يُمكِن قِياسه: تَغطيَة tokens، اتِّساق الشَّبَكَة
- لا يَتَطَلَّب حُكم خارِجيّ

**أَمثِلَة:**
- «قَرَأَ زَيدٌ الكِتابَ في المَسجِدِ»
  - **Meaning:** event(قرأ، agent=زَيد، patient=الكِتاب، location=المَسجِد، tense=past)
  - هذا ما تَقوله الجُملَة بِنيَويًّا، لا اجتِهاد فيه.

### Interpretation = «ما يَقصُده القائِل»

- يَتَطَلَّب: مَعرِفَة المُتَكَلِّم، السِّياق الثَّقافيّ، نِيَّة، تَأويل بَلاغيّ
- لا يُقاس آليًّا (مَن يَحكُم؟)
- يَتَغَيَّر بِالقارِئ

**أَمثِلَة:**
- «قَرَأَ زَيدٌ الكِتابَ»
  - **Interpretation:** زَيد كانَ مُجتَهِدًا / كَسولًا / يَستَعِدّ لِامتِحان...
  - هذه فُهومات مُمكِنَة لَكِنّ لا تَنبَني مِن الجُملَة وَحدها.

---

## 3. القاعِدَة الذَّهَبيَّة

```
Meaning(text) = Structural_Composition(
    entities,
    relations,
    events,
    resolutions
)

Interpretation(text) = Meaning(text) + Human_Knowledge + Context + Inference
                       └────────────┘  └──── خارِج النِّطاق ────┘
                       داخِل النِّطاق
```

**النَّتيجَة:** المُحَلِّل يُخرِج Meaning فَقَط. الـ Interpretation = مَسؤوليَّة المُستَخدِم.

---

## 4. أَنماط داخِل النِّطاق (Meaning)

### 4.1 تَجميع الجُملَة

- ضَمّ entities + relations + events + resolutions في graph واحِد
- مَثَل: «قَرَأَ زَيدٌ الكِتابَ» →
  ```
  Entity(زَيد)──agent_of──>Event(قرأ)<──patient_of──Entity(الكِتاب)
  ```

### 4.2 تَجميع النَّصّ

- ربط شَبَكات الجُمَل عَبر الإِحالات
- مَثَل: «جاءَ زَيدٌ. ثُمَّ ذَهَبَ هو» →
  ```
  جاءَ(agent=زَيد) ──then──> ذَهَبَ(agent=هو→زَيد)
  ```

### 4.3 قِياس الاتِّساق

- هَل graph النَّصّ يَحوي تَناقُضات بِنيَويَّة؟
- مَثَل: «جاءَ زَيدٌ. لَم يَأتِ زَيدٌ» → تَناقُض!

### 4.4 قِياس الغُموض

- entropy عَلى الـ Hypotheses في النَّصّ
- نَصّ كُلّه Certificate = entropy = 0 (لا غُموض)
- نَصّ كُلّه Hypothesis مُتَعَدِّد القِراءات = entropy عالِيَة

---

## 5. أَنماط خارِج النِّطاق (Interpretation)

| النَّمَط | السَّبَب |
|---|---|
| تَفسير قُرآنيّ | يَتَطَلَّب اجتِهاد |
| استِخراج الحُكم الفِقهيّ | يَتَطَلَّب أُصول الفِقه |
| تَقدير النِّيَّة الباطِنَة | غَير قابِل لِلقِياس |
| استِنباط بَلاغيّ (الإِعجاز) | لا مِتري مَوضوعيّ |
| تَأويل المَجاز | research frontier |
| الحُكم عَلى الجَمال الأَدَبيّ | ذاتيّ |
| السُّخريَة وَ التَّوريَة | تَحتاج سياق ثَقافيّ غَنيّ |

---

## 6. ما هو الـ MeaningGraph

```python
@dataclass
class MeaningNode:
    """عُقدة في شَبَكَة المَعنى — كِيان أَو حَدَث."""
    node_id: str
    node_type: str   # "entity" | "event" | "transformation"
    surface: str
    position: int
    proof: ProofObject  # كَيف عَرَفنا أَنّ هذا node؟

@dataclass
class MeaningEdge:
    """رابِطَة في الشَّبَكَة — relation أَو resolution."""
    edge_id: str
    edge_type: str   # "agent_of" | "anaphora_to" | "transformation_of" | ...
    source: str       # node_id
    target: str       # node_id
    proof: ProofObject

@dataclass
class MeaningGraph:
    """الـ graph الكامِل لِنَصّ."""
    text: str
    nodes: list[MeaningNode]
    edges: list[MeaningEdge]
    coverage_pct: float
    contradictions: list
    entropy: float       # مِقياس الغُموض الكُلّيّ
```

---

## 7. مَعايير القَبول الدُّستوريَّة

مِن `15_Executive_Roadmap.md §4.F`:
- **اتِّساق الشَّبَكَة:** no contradictions ≥ 95%
- **تَغطيَة الـ tokens:** ≥ 90%

مِن `12_Project_Scope_Declaration.md`:
- كُلّ node + edge بِـ ProofObject (100%)
- كُلّ alternative مَحفوظَة (100%)

---

## 8. النَّتيجَة الدُّستوريَّة

> **Meaning = ما يَنبَني مِن البِنيَة (داخِل النِّطاق).**
> **Interpretation = ما يُضاف مِن المَعرِفَة الخارِجيَّة (خارِج النِّطاق).**
>
> Phase F يَبني MeaningGraph فَقَط. مَن أَرادَ Interpretation فَلَيس عَلى المُحَلِّل أَن يَفعَله.

البَوّابَة مَفتوحَة → Phase F التَّنفيذيَّة تَبدَأ.
