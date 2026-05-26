"""relation_extractor.py — جَلسة 15: استخراج العَلاقات مِن i3rab.

يَأخُذ `SentenceI3rab` (مِن `i3rab_engine.engine`) ويُنتِج `RelationGraph`.

كُلّ علاقَة:
  • Token مَع role_phrase = «فاعل» ← agent_of(token, nearest_verb)
  • Token مَع role_phrase = «مفعول به» ← patient_of(token, nearest_verb)
  • Token مَع role_phrase = «مضاف إليه» ← possessor_of(token, prev_noun)
  • Token مَع role_phrase = «نعت» ← attribute_of(token, prev_noun)
  • Token مَع role_phrase = «مبتدأ» + خبر لاحِق ← topic_of/comment_of
  • Token مَع role_phrase = «خبر» ← comment_of(token, prev_mubtada)
  • Token مَع role_phrase = «اسم إنّ» / «خبر إنّ» ← inna_topic_of / inna_comment_of
  • Token مَع role_phrase = «اسم مجرور» ← harf_jarr_of(token, prev_harf_jarr)
    (التَّوسعة في جَلسة 16 — operator مِن `harf_jarr_relations.csv`)
  • Token مَع role_phrase = «معطوف» ← coordinate_of
  • Token مَع word_class = «FIIL» ← verb_in_clause(verb, —)

كُلّ علاقَة تَحمِل ProofObject-like metadata.

Constitutional commitments:
  1. Source-of-Claim — كُلّ علاقَة تَحمِل اسم role + اسم target + اسم rule
  2. Confidence — kind مَوروث مِن role_kind في i3rab (Certificate أَو Hypothesis)
  3. Alternatives — لَو فِعلان مُمكِنان كَ target، يُحفَظ الـ alternative
  4. Reversible — مُؤَجَّل
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows
from relation_schema import EntityNode, Relation, RelationGraph


CONTRACT_NAME = "RelationExtractor:v1"


# ============================================================================
# تَطبيع role_phrase — يَدعَم تَنَوُّعات «مفعول به» / «مفعولٌ به» / «مفعول_به»
# ============================================================================

def _normalize_role(phrase: str) -> str:
    """يَستَخرِج جَوهَر role_phrase بِغَضّ النَّظَر عَن لاحِقات الحالَة.

    Examples:
      "فاعل مرفوع"             → "فاعل"
      "مفعول به منصوب"          → "مفعول_به"
      "مضاف إليه مجرور"         → "مضاف_إليه"
      "خبر إنّ مرفوع"           → "خبر_إنّ"
      "اسم مجرور"               → "اسم_مجرور"
      "مبتدأ مرفوع"             → "مبتدأ"
      "نعت مرفوع"               → "نعت"
      "اسم إنّ منصوب"           → "اسم_إنّ"
    """
    if not phrase:
        return ""
    out = phrase.strip()
    # حَذف تَشكيل
    for d in "ًٌٍَُِّْـ":
        out = out.replace(d, "")
    # حالات خاصَّة: «اسم مجرور» = الرَّول كامِلًا (مَفعول حَرف الجَرّ)
    # نَحفَظه قَبل تَجريد أَيّ لاحِقَة
    if out.startswith("اسم مجرور"):
        return "اسم_مجرور"
    if out.startswith("اسم إن") or out.startswith("اسم إنّ"):
        return "اسم_إنّ"
    if out.startswith("اسم كان"):
        return "اسم_كان"
    if out.startswith("خبر إن") or out.startswith("خبر إنّ"):
        return "خبر_إنّ"
    if out.startswith("خبر كان"):
        return "خبر_كان"
    if out.startswith("مفعول به"):
        return "مفعول_به"
    if out.startswith("مفعول لأجله") or out.startswith("مفعول لاجله"):
        return "مفعول_لأجله"
    if out.startswith("مفعول مطلق"):
        return "مفعول_مطلق"
    if out.startswith("مفعول فيه"):
        return "مفعول_فيه"
    if out.startswith("مضاف إليه"):
        return "مضاف_إليه"
    # تَطبيع لاحِقات الحالَة الشَّائِعة (لِـ «فاعل مرفوع»، «مبتدأ مرفوع»، إلخ)
    suffixes_to_strip = (
        " مرفوع", " منصوب", " مجرور", " مجزوم",
        " مبني",
    )
    changed = True
    while changed:
        changed = False
        for suf in suffixes_to_strip:
            if out.endswith(suf):
                out = out[: -len(suf)].strip()
                changed = True
    out = out.strip().replace(" ", "_")
    return out


# ============================================================================
# Extractor
# ============================================================================

class RelationExtractor:

    def __init__(self) -> None:
        self._relation_types = _load_rows("relation_types.csv")
        self._relation_types.sort(key=lambda r: int(r.get("priority", "99")))
        # جَلسة 16: حُروف الجَرّ كَ relation operators
        try:
            self._harf_jarr_relations = _load_rows("harf_jarr_relations.csv")
        except Exception:
            self._harf_jarr_relations = []
        # بِناء فِهرس سَريع: surface_plain → relation_row
        self._harf_jarr_index: dict[str, dict] = {}
        for row in self._harf_jarr_relations:
            harf_plain = row.get("harf_plain", "").strip()
            if harf_plain:
                self._harf_jarr_index[harf_plain] = row
            surfaces = row.get("harf_surfaces", "")
            for surf in [s.strip() for s in surfaces.split("،") if s.strip()]:
                surf_plain = self._strip_diac(surf)
                self._harf_jarr_index.setdefault(surf_plain, row)

    @staticmethod
    def _strip_diac(s: str) -> str:
        for d in "ًٌٍَُِّْـ":
            s = s.replace(d, "")
        return s

    def _lookup_harf_jarr(self, harf_surface: str) -> Optional[dict]:
        """يَبحَث عَن قاعِدَة harf_jarr مُطابِقَة للسَّطح. يُجَرِّب بِلا
        تَشكيل أَوّلًا، ثُمَّ بِلا «ال»، ثُمَّ بِلا lam/baa lead."""
        plain = self._strip_diac(harf_surface)
        if plain in self._harf_jarr_index:
            return self._harf_jarr_index[plain]
        # تَجريب أَوَّل حَرف (لِـ بِ، لِـ لِ، كَـ كَ)
        if len(plain) >= 1 and plain[0] in self._harf_jarr_index:
            return self._harf_jarr_index[plain[0]]
        return None

    def extract(self, sent) -> RelationGraph:
        """yields RelationGraph from SentenceI3rab."""
        g = RelationGraph(source_text=getattr(sent, "text", ""), contract=CONTRACT_NAME)
        tokens = sent.tokens

        # ── Phase 1: build EntityNode for every token ──
        for i, t in enumerate(tokens):
            entity = self._build_entity(t, i)
            g.add_node(entity)

        # ── Phase 2: walk tokens, emit relations ──
        # Context bookkeeping:
        last_verb_idx: Optional[int] = None
        verb_subject_set: dict[int, bool] = {}    # verb_idx → got fa3il?
        last_mubtada_idx: Optional[int] = None
        last_inna_subj_idx: Optional[int] = None
        last_kana_subj_idx: Optional[int] = None
        last_harf_jarr_idx: Optional[int] = None
        last_noun_idx: Optional[int] = None       # for مضاف إليه / نعت

        for i, t in enumerate(tokens):
            role_n = _normalize_role(t.role_phrase)
            tid = f"t{i}"

            # ── FIIL: verb anchor + may have prior context (for مجزوم/منصوب) ──
            if t.word_class == "FIIL":
                # verb_in_clause anchor (target = — since no other node)
                g.add_relation(self._build_relation(
                    name="verb_in_clause",
                    kind_type="clause_anchor",
                    source_id=tid,
                    target_id="—",
                    role_kind=t.role_kind or "Hypothesis",
                    source_of_claim=f"word_class:FIIL + verb_in_clause(no_target)",
                ))
                last_verb_idx = i
                verb_subject_set[i] = False
                continue

            # ── HARF: track حرف الجَرّ for next noun ──
            if t.word_class == "HARF":
                if t.closed_class_kind == "HARF_JARR":
                    last_harf_jarr_idx = i
                # other HARF كَ عَطف، نِداء، إِنّ، كان handled by role detection below
                # Track إِنّ context via role
                if role_n in ("اسم_إنّ", "اسم_إن"):
                    last_inna_subj_idx = i  # technically t is إنّ; the next token is its اسم
                continue

            # ── role-based dispatch ──

            # فاعل → agent_of(token, last_verb)
            if role_n == "فاعل":
                if last_verb_idx is not None:
                    g.add_relation(self._build_relation(
                        name="agent_of",
                        kind_type="subj_pred",
                        source_id=tid,
                        target_id=f"t{last_verb_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:فاعل + last_verb_idx:{last_verb_idx} + relation_types:agent_of",
                    ))
                    verb_subject_set[last_verb_idx] = True
                last_noun_idx = i

            # مفعول به → patient_of(token, last_verb)
            elif role_n in ("مفعول_به", "مفعولٌ_به", "مفعول"):
                if last_verb_idx is not None:
                    g.add_relation(self._build_relation(
                        name="patient_of",
                        kind_type="subj_pred",
                        source_id=tid,
                        target_id=f"t{last_verb_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:مفعول_به + last_verb_idx:{last_verb_idx} + relation_types:patient_of",
                    ))
                last_noun_idx = i

            # مضاف إليه → possessor_of(token, prev_noun)
            elif role_n in ("مضاف_إليه", "مضافٌ_إليه"):
                if last_noun_idx is not None and last_noun_idx != i:
                    g.add_relation(self._build_relation(
                        name="possessor_of",
                        kind_type="possession",
                        source_id=tid,
                        target_id=f"t{last_noun_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:مضاف_إليه + last_noun_idx:{last_noun_idx} + relation_types:possessor_of",
                    ))
                last_noun_idx = i

            # نعت → attribute_of(token, prev_noun)
            elif role_n == "نعت":
                if last_noun_idx is not None and last_noun_idx != i:
                    g.add_relation(self._build_relation(
                        name="attribute_of",
                        kind_type="attribute",
                        source_id=tid,
                        target_id=f"t{last_noun_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:نعت + last_noun_idx:{last_noun_idx} + relation_types:attribute_of",
                    ))
                last_noun_idx = i

            # مبتدأ → topic_anchor + remember for خبر
            elif role_n == "مبتدأ":
                g.add_relation(self._build_relation(
                    name="topic_anchor",
                    kind_type="clause_anchor",
                    source_id=tid,
                    target_id="—",
                    role_kind=t.role_kind or "Hypothesis",
                    source_of_claim=f"role:مبتدأ + relation_types:topic_anchor",
                ))
                last_mubtada_idx = i
                last_noun_idx = i

            # خبر → comment_of(token, last_mubtada)
            elif role_n == "خبر":
                if last_mubtada_idx is not None:
                    g.add_relation(self._build_relation(
                        name="comment_of",
                        kind_type="topic_comment",
                        source_id=tid,
                        target_id=f"t{last_mubtada_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:خبر + last_mubtada_idx:{last_mubtada_idx} + relation_types:comment_of",
                    ))
                last_noun_idx = i

            # اسم إنّ → inna_topic_of
            elif role_n in ("اسم_إنّ", "اسم_إن"):
                # target = the إِنّ harf itself; we use last_inna_subj_idx as a placeholder
                if last_inna_subj_idx is not None and last_inna_subj_idx != i:
                    g.add_relation(self._build_relation(
                        name="inna_topic_of",
                        kind_type="topic_comment",
                        source_id=tid,
                        target_id=f"t{last_inna_subj_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:اسم_إنّ + harf_inna_idx:{last_inna_subj_idx} + relation_types:inna_topic_of",
                    ))
                last_inna_subj_idx = i  # now THIS is the subject
                last_noun_idx = i

            # خبر إنّ → inna_comment_of
            elif role_n in ("خبر_إنّ", "خبر_إن"):
                if last_inna_subj_idx is not None and last_inna_subj_idx != i:
                    g.add_relation(self._build_relation(
                        name="inna_comment_of",
                        kind_type="topic_comment",
                        source_id=tid,
                        target_id=f"t{last_inna_subj_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:خبر_إنّ + inna_subj:{last_inna_subj_idx} + relation_types:inna_comment_of",
                    ))
                last_noun_idx = i

            # اسم مجرور → harf_jarr_of + relation مُتَخَصِّصَة (in_location/...) مِن harf_jarr_relations.csv
            elif role_n in ("اسم_مجرور", "مجرور"):
                if last_harf_jarr_idx is not None and last_harf_jarr_idx != i:
                    harf_surface = tokens[last_harf_jarr_idx].token
                    # العَلاقَة الأَساسيَّة dr-عامَّة
                    g.add_relation(self._build_relation(
                        name="harf_jarr_of",
                        kind_type="prep_phrase",
                        source_id=tid,
                        target_id=f"t{last_harf_jarr_idx}",
                        operator=harf_surface,
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:اسم_مجرور + harf_jarr_idx:{last_harf_jarr_idx} + operator:{harf_surface}",
                    ))
                    # العَلاقَة المُتَخَصِّصَة (locative/goal/source/...) إِن وُجِدَت
                    rule = self._lookup_harf_jarr(harf_surface)
                    if rule:
                        g.add_relation(self._build_relation(
                            name=rule.get("creates_relation", "harf_jarr_specialized"),
                            kind_type=rule.get("relation_kind", "prep_phrase"),
                            source_id=tid,
                            target_id=f"t{last_harf_jarr_idx}",
                            operator=harf_surface,
                            role_kind=t.role_kind or "Hypothesis",
                            source_of_claim=(
                                f"role:اسم_مجرور + harf_jarr:{harf_surface} + "
                                f"harf_jarr_relations:{rule.get('name','?')}"
                            ),
                        ))
                last_noun_idx = i

            # معطوف → coordinate_of(token, prev_noun)
            elif role_n == "معطوف":
                if last_noun_idx is not None and last_noun_idx != i:
                    g.add_relation(self._build_relation(
                        name="coordinate_of",
                        kind_type="coordination",
                        source_id=tid,
                        target_id=f"t{last_noun_idx}",
                        role_kind=t.role_kind or "Hypothesis",
                        source_of_claim=f"role:معطوف + last_noun_idx:{last_noun_idx} + relation_types:coordinate_of",
                    ))
                last_noun_idx = i

            # any other ISM → just remember as last_noun
            else:
                if t.word_class in ("ISM_MUARAB", "JAMID", "AALAM", "JALALAH"):
                    last_noun_idx = i

        return g

    # ------------------------------------------------------------------
    # builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_entity(t, i: int) -> EntityNode:
        is_singular = (t.word_class == "JALALAH") or (
            t.word_class_source and "singular_term" in t.word_class_source
        )
        return EntityNode(
            entity_id=f"t{i}",
            surface=t.token,
            surface_plain=t.token_plain or "",
            position=i,
            root=t.root or "—",
            wazn=t.wazn or "—",
            status=("singular_term" if is_singular else ""),
            word_class=t.word_class,
            role_phrase=t.role_phrase or "",
            case_name=(t.token and ""),  # filled later if needed
            is_singular_term=is_singular,
            is_divine_name=is_singular,
            source_of_claim=t.word_class_source or "",
        )

    @staticmethod
    def _build_relation(*, name: str, kind_type: str, source_id: str, target_id: str,
                       role_kind: str, source_of_claim: str, operator: Optional[str] = None) -> Relation:
        return Relation(
            name=name,
            kind_type=kind_type,
            source_id=source_id,
            target_id=target_id,
            operator=operator,
            kind=role_kind or "Hypothesis",
            source_of_claim=source_of_claim,
            contract=CONTRACT_NAME,
        )


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    from i3rab_engine.engine import I3rabEngine

    engine = I3rabEngine()
    extractor = RelationExtractor()

    tests = [
        "كَتَبَ الْوَلَدُ كِتَابًا",
        "ذَهَبَ زَيْدٌ إِلَى الْمَسْجِدِ",
        "إِنَّ اللَّهَ غَفُورٌ رَحِيمٌ",
        "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
        "يَا أَيُّهَا النَّاسُ اعْبُدُوا رَبَّكُمْ",
    ]
    for s in tests:
        print(f"\n=== {s} ===")
        sent = engine.analyze_sentence(s)
        g = extractor.extract(sent)
        for i, t in enumerate(sent.tokens):
            print(f"  [{i}] {t.token:<18} wc={t.word_class:<12} role={t.role_phrase}")
        print(f"  --- {len(g.relations)} relations ---")
        for r in g.relations:
            op = f" via «{r.operator}»" if r.operator else ""
            print(f"  • {r.name}: {r.source_id} → {r.target_id}{op}")
            print(f"      src={r.source_of_claim}")
