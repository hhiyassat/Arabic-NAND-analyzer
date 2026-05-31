"""reasoning_engine.py — Phase G: قِمَّة المَعمار.

MC-COMPLIANT:
  • أَنواع الأَسئلَة مِن CSV (query_types.csv)
  • كُلّ إِجابَة بِـ kind + contract + evidence
  • رَفض صَريح لِلأَسئلَة خارِج النِّطاق (100%)
  • لا اجتِهاد، لا تَفسير، لا تَخمين

CLI:
  python3 reasoning_engine.py "قَرَأَ زَيدٌ الكِتابَ" --ask "مَن قَرَأَ الكِتابَ؟"
  python3 reasoning_engine.py --verse 1:5 --ask "مَن المَعبود؟"
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

from meaning_assembler import MeaningAssembler
from meaning_graph import MeaningGraph

_HERE = Path(__file__).resolve().parent
QUERY_TYPES_CSV = _HERE / "data" / "contracts" / "rules" / "query_types.csv"

DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _normalize(s: str) -> str:
    return _strip_diac(_nfc(s))


# ─────────────────────────────────────────────────────────────────
# Query + Answer schemas
# ─────────────────────────────────────────────────────────────────

AnswerKind = Literal["Certificate", "Hypothesis", "Zero"]


@dataclass
class Query:
    raw_text: str
    query_type: str = "unknown"
    trigger_word: str = ""
    answer_strategy: str = "reject"
    is_in_scope: bool = False


@dataclass
class Answer:
    query: Query
    kind: AnswerKind
    contract: str
    answer: Optional[str] = None
    evidence: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    rejected_reason: Optional[str] = None

    @property
    def symbol(self) -> str:
        return {"Certificate": "✓", "Hypothesis": "?", "Zero": "✗"}[self.kind]

    def __str__(self) -> str:
        head = f"{self.symbol} [{self.kind}] "
        if self.rejected_reason:
            return head + f"مَرفوض: {self.rejected_reason}"
        if self.answer:
            return head + str(self.answer)
        return head + "لا إِجابَة"


# ─────────────────────────────────────────────────────────────────
# تَحميل query_types.csv
# ─────────────────────────────────────────────────────────────────

_QUERY_TYPES_CACHE: list[dict] | None = None


def _load_query_types() -> list[dict]:
    global _QUERY_TYPES_CACHE
    if _QUERY_TYPES_CACHE is not None:
        return _QUERY_TYPES_CACHE
    rows = []
    if QUERY_TYPES_CSV.exists():
        with open(QUERY_TYPES_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append({
                    "priority": int(row.get("priority", "99") or 99),
                    "trigger_word": _nfc(row.get("trigger_word", "").strip()),
                    "trigger_plain": _normalize(row.get("trigger_word", "").strip()),
                    "query_type": row.get("query_type", "").strip(),
                    "in_scope": row.get("in_scope", "").strip().lower() == "true",
                    "partial": row.get("in_scope", "").strip().lower() == "partial",
                    "answer_strategy": row.get("answer_strategy", "reject").strip(),
                    "description": row.get("description", "").strip(),
                })
    rows.sort(key=lambda r: r["priority"])
    _QUERY_TYPES_CACHE = rows
    return rows


# ─────────────────────────────────────────────────────────────────
# المُحَرِّك
# ─────────────────────────────────────────────────────────────────

class ReasoningEngine:
    """مُحَرِّك الِاستِدلال — يَستَجوِب MeaningGraph."""

    CONTRACT_QUERY_PARSE = "QueryParseContract:v1"
    CONTRACT_ANSWER = "ReasoningAnswerContract:v1"
    CONTRACT_REJECT = "OutOfScopeRejectContract:v1"

    def __init__(self):
        self.assembler = MeaningAssembler()

    # ──────────────────────────────────────────────────────────
    # Query parsing
    # ──────────────────────────────────────────────────────────

    def parse_query(self, question: str) -> Query:
        """يُصَنِّف السُّؤال — مِن CSV لا inline.

        Strategy: نَمُرّ عَلى الـ types بِالـ priority.
        لِكُلّ type نَفحَص هَل trigger يَظهَر كَ كَلِمَة مُستَقِلَّة في السُّؤال
        (لَيس substring — مَنع «ما» مِن مُطابَقَة «لِماذا»).

        PATCH 6 (2026-05-28) — Compound-question routing.
        Before the per-trigger priority loop, recognize compound
        question forms that the trigger-set alone routes incorrectly:
          • «ماذا حَدَث؟» / «ما حَدَث؟»   → events     (not patients)
          • «ما تَسَلسُل ...؟» / «التسلسل»  → sequence    (not patients via ما)
          • «إلى ماذا تَحَوَّلَ ...؟» / «صار إلى» → transformation (not patients via ماذا)
        This keeps the CSV unchanged and routes compound forms before
        the single-trigger pattern can mis-route them.
        """
        q_plain = _normalize(question)
        # تَقسيم بِالمَسافات + علامات التَّرقيم
        import re as _re
        q_words = set(_re.split(r"[\s؟?،,.!]+", q_plain))
        q_words.discard("")
        types = _load_query_types()

        # ── PATCH 6: compound-question routing ──────────────────
        # Detect حَدَث (root: ح-د-ث) in the question to identify
        # "what happened" / "what events" intent.
        has_ma_or_madha = bool(q_words & {"ما", "ماذا"})
        has_happened = any(w in q_words for w in ("حدث", "حدثت", "احداث", "الاحداث"))
        has_sequence = any(w in q_words for w in ("تسلسل", "ترتيب"))
        has_transform = any(w in q_words for w in ("تحول", "تحولت", "صار", "صارت", "تتحول"))
        has_ila = "الى" in q_words or "إِلَى" in q_words

        if has_ma_or_madha and has_sequence:
            return Query(raw_text=question, query_type="sequence",
                         trigger_word="ما+تَسَلسُل", answer_strategy="find_sequence",
                         is_in_scope=True)
        if (has_ma_or_madha and has_transform) or (has_ila and has_ma_or_madha):
            return Query(raw_text=question, query_type="transformation",
                         trigger_word="ماذا+تَحَوَّل", answer_strategy="find_transformation",
                         is_in_scope=True)
        if has_ma_or_madha and has_happened:
            return Query(raw_text=question, query_type="what_event",
                         trigger_word="ماذا+حَدَث", answer_strategy="find_events",
                         is_in_scope=True)
        # ────────────────────────────────────────────────────────

        for t in types:
            trigger_p = t["trigger_plain"]
            # المُطابَقَة الصَّحيحَة: trigger يَظهَر كَ كَلِمَة كامِلَة
            if trigger_p in q_words:
                return Query(
                    raw_text=question,
                    query_type=t["query_type"],
                    trigger_word=t["trigger_word"],
                    answer_strategy=t["answer_strategy"],
                    is_in_scope=t["in_scope"] and not t["partial"],
                )

        # fallback: substring matching فَقَط لِلكَلِمات الطَّويلَة (≥4 حُروف)
        # لِالتِقاط «تفسير»، «إعجاز»...
        for t in types:
            trigger_p = t["trigger_plain"]
            if len(trigger_p) >= 4 and trigger_p in q_plain:
                return Query(
                    raw_text=question,
                    query_type=t["query_type"],
                    trigger_word=t["trigger_word"],
                    answer_strategy=t["answer_strategy"],
                    is_in_scope=t["in_scope"] and not t["partial"],
                )

        return Query(raw_text=question, query_type="unknown")

    # ──────────────────────────────────────────────────────────
    # Strategies
    # ──────────────────────────────────────────────────────────

    def answer(self, text: str, question: str) -> Answer:
        """يُجيب عَن سُؤال حَول نَصّ."""
        query = self.parse_query(question)

        # رَفض الأَسئلَة خارِج النِّطاق (دُستوريّ — 100%)
        if not query.is_in_scope and query.answer_strategy == "reject":
            return Answer(
                query=query, kind="Zero",
                contract=self.CONTRACT_REJECT,
                rejected_reason=f"النَّوع «{query.query_type}» خارِج النِّطاق التِّقنيّ. تَوَجَّه لِمُتَخَصِّص.",
            )

        # بِناء الـ MeaningGraph
        graph = self.assembler.assemble(text)

        # تَوجيه لِلـ strategy المُناسِبَة
        strategy_map = {
            "find_agent": self._find_agent,
            "find_patient": self._find_patient,
            "find_patient_or_predicate": self._find_patient,
            "find_time": self._find_time,
            "find_location": self._find_location,
            "find_manner": self._find_manner,
            "find_quantity": self._find_quantity,
            "find_instrument": self._find_instrument,
            "check_existence": self._check_existence,
            "find_explicit_cause": self._find_explicit_cause,
            "find_sequence": self._find_sequence,
            "find_transformation": self._find_transformation,
            # PATCH 6 — new strategy for "ماذا حَدَث؟" (events, not patients)
            "find_events": self._find_events,
        }
        strategy = strategy_map.get(query.answer_strategy)
        if not strategy:
            return Answer(
                query=query, kind="Zero",
                contract=self.CONTRACT_ANSWER,
                rejected_reason=f"لا strategy مُسَجَّلَة لِـ «{query.answer_strategy}»",
            )

        return strategy(query, graph, question)

    # ──────────────────────────────────────────────────────────
    # Strategy implementations
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _dedupe_preserve_order(items: list) -> list:
        seen, out = set(), []
        for x in items:
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        return out

    def _find_agent(self, query: Query, graph: MeaningGraph, question: str) -> Answer:
        """مَن فَعَل ماذا؟ — يُرجِع كُلّ الفاعِلين الفَريدين."""
        agents, evidence = [], []
        for e in graph.edges:
            if e.edge_type == "agent_of":
                node = graph.get_node(e.source)
                if node:
                    agents.append(node.surface)
                    evidence.append(e.edge_id)
        agents = self._dedupe_preserve_order(agents)
        if not agents:
            return Answer(
                query=query, kind="Zero",
                contract=self.CONTRACT_ANSWER,
                rejected_reason="لا agent مَكشوف في النَّصّ",
            )
        # عَرض ≤ 5 فَواعِل، مَع إِشارَة لِلباقي
        head = agents[:5]
        rest = len(agents) - len(head)
        answer = " / ".join(head) + (f" (+{rest} آخَرين)" if rest > 0 else "")
        return Answer(
            query=query,
            kind="Certificate" if len(agents) == 1 else "Hypothesis",
            contract=self.CONTRACT_ANSWER,
            answer=answer,
            evidence=evidence[:5],
            alternatives=agents[1:],
        )

    def _find_patient(self, query: Query, graph: MeaningGraph, question: str) -> Answer:
        patients, evidence = [], []
        for e in graph.edges:
            if e.edge_type in ("patient_of", "patient2_of"):
                node = graph.get_node(e.source)
                if node:
                    patients.append(node.surface)
                    evidence.append(e.edge_id)
        patients = self._dedupe_preserve_order(patients)
        if not patients:
            return Answer(
                query=query, kind="Zero",
                contract=self.CONTRACT_ANSWER,
                rejected_reason="لا patient/مَفعول مَكشوف",
            )
        head = patients[:5]
        rest = len(patients) - len(head)
        answer = " / ".join(head) + (f" (+{rest} آخَرين)" if rest > 0 else "")
        return Answer(
            query=query,
            kind="Certificate" if len(patients) == 1 else "Hypothesis",
            contract=self.CONTRACT_ANSWER,
            answer=answer,
            evidence=evidence[:5],
            alternatives=patients[1:],
        )

    def _find_time(self, query: Query, graph: MeaningGraph, question: str) -> Answer:
        """PATCH 6 — Answer-Type Gate: temporal expressions ONLY.

        Returns scoped time_value entries (when_future, past, then, now,
        ...). Tense (past/present/command) is NOT a time expression —
        it is grammatical aspect. If only tense exists with no time
        adverb, return Zero (do not emit `tense:*` as a time answer).
        """
        times = []
        evidence = []
        tense_only = []
        for n in graph.nodes:
            if n.node_type in ("event", "transformation"):
                t = n.attributes.get("time_value")
                if t:
                    times.append(t)
                    evidence.append(n.node_id)
                else:
                    tense = n.attributes.get("tense")
                    if tense and tense != "unknown":
                        tense_only.append(tense)
        times = self._dedupe_preserve_order(times)
        if not times:
            # No real temporal expression — clearly label tense as
            # metadata, do NOT return it as the main answer.
            if tense_only:
                tenses = self._dedupe_preserve_order(tense_only)
                return Answer(
                    query=query, kind="Zero",
                    contract=self.CONTRACT_ANSWER,
                    rejected_reason=(
                        f"لا تَعبير زَمَنيّ صَريح في النَّصّ "
                        f"(وُجِدَ tense metadata فَقَط: {', '.join(tenses)})"
                    ),
                )
            return Answer(
                query=query, kind="Zero",
                contract=self.CONTRACT_ANSWER,
                rejected_reason="لا زَمَن صَريح في النَّصّ",
            )
        return Answer(
            query=query, kind="Certificate" if len(times) == 1 else "Hypothesis",
            contract=self.CONTRACT_ANSWER,
            answer=" / ".join(times),
            evidence=evidence,
        )

    def _find_location(self, query: Query, graph: MeaningGraph, question: str) -> Answer:
        """PATCH 6 — Answer-Type Gate: true place expressions ONLY.

        Sources accepted:
          • in_location (في), on_surface (على) — strong place edges
          • L3 role=ظرف مكان (locative-noun stems like بَيْنَ, عِندَ)

        Sources NOT accepted (pre-PATCH-6 they bled in via direction_to /
        from_source on temporal / entity nouns):
          • direction_to (إلى) — ambiguous: temporal أَجَل / spatial مكان
          • from_source (مِن)  — ambiguous: source-of-people / source-of-place

        Also reject known temporal nouns (أَجَل / يَوم / ساعَة / شَهر / سَنَة /
        وَقت) even if they appear in a place-edge end.
        """
        STRONG_LOC_EDGES = {"in_location", "on_surface"}
        SKIP_SURFACES = {"في", "فِي", "على", "عَلى", "عَلَىٰ", "إلى", "إِلى",
                         "من", "مِن", "عن", "عَن"}
        TEMPORAL_NOUN_ROOTS = {
            "اجل", "أجل", "يوم", "ساعة", "شهر", "سنة", "وقت", "حين",
            "ليل", "نهار", "صباح", "مساء", "عصر",
        }
        locations = []
        evidence = []

        # Source 1 — strong place edges only
        for e in graph.edges:
            if e.edge_type not in STRONG_LOC_EDGES:
                continue
            for end in (e.source, e.target):
                node = graph.get_node(end)
                if node is None:
                    continue
                wc = node.attributes.get("word_class", "") if node.attributes else ""
                if wc == "HARF":
                    continue
                surf = node.surface or ""
                if not surf or surf in SKIP_SURFACES:
                    continue
                # Reject temporal nouns by plain-text root match
                plain = _normalize(surf)
                if any(t in plain for t in TEMPORAL_NOUN_ROOTS):
                    continue
                locations.append(surf)
                evidence.append(e.edge_id)
                break

        # Source 2 — L3-certified locative nouns (role=ظرف مكان)
        for n in graph.nodes:
            if n.node_type != "entity":
                continue
            role = (n.attributes.get("role_phrase", "") or "") if n.attributes else ""
            if "ظرف مكان" in role:
                surf = n.surface or ""
                if surf and surf not in SKIP_SURFACES:
                    locations.append(surf)
                    evidence.append(n.node_id)

        locations = self._dedupe_preserve_order(locations)
        if not locations:
            return Answer(
                query=query, kind="Zero",
                contract=self.CONTRACT_ANSWER,
                rejected_reason="لا مَكان مَكشوف",
            )
        head = locations[:5]
        rest = len(locations) - len(head)
        answer = " / ".join(head) + (f" (+{rest} آخَرين)" if rest > 0 else "")
        return Answer(
            query=query, kind="Certificate" if len(locations) == 1 else "Hypothesis",
            contract=self.CONTRACT_ANSWER,
            answer=answer,
            evidence=evidence[:5],
        )

    def _find_events(self, query: Query, graph: MeaningGraph, question: str) -> Answer:
        """PATCH 6 — strategy for "ماذا حَدَث؟": return event/action labels only.

        Source: graph nodes with node_type in (event, transformation).
        Label: prefer verb_surface (the actual verb), fall back to the
        node's surface or type field. Returned in verse order.
        """
        events = sorted(
            [n for n in graph.nodes if n.node_type in ("event", "transformation")],
            key=lambda n: n.position,
        )
        if not events:
            return Answer(
                query=query, kind="Zero",
                contract=self.CONTRACT_ANSWER,
                rejected_reason="لا أَحداث مَكشوفَة",
            )
        labels = []
        evidence = []
        for n in events:
            label = ((n.attributes or {}).get("verb_surface") or n.surface or n.attributes.get("type") if n.attributes else None) or n.surface
            if label:
                labels.append(label)
                evidence.append(n.node_id)
        labels = self._dedupe_preserve_order(labels)
        if not labels:
            return Answer(
                query=query, kind="Zero",
                contract=self.CONTRACT_ANSWER,
                rejected_reason="أَحداث مَكشوفَة لَكِن بِدون labels",
            )
        head = labels[:5]
        rest = len(labels) - len(head)
        answer = " / ".join(head) + (f" (+{rest} آخَرين)" if rest > 0 else "")
        return Answer(
            query=query, kind="Certificate" if len(labels) == 1 else "Hypothesis",
            contract=self.CONTRACT_ANSWER,
            answer=answer,
            evidence=evidence[:5],
        )

    def _find_manner(self, query: Query, graph: MeaningGraph, question: str) -> Answer:
        return Answer(
            query=query, kind="Zero",
            contract=self.CONTRACT_ANSWER,
            rejected_reason="manner extraction غَير مُكتَمِل (يَحتاج حال detector)",
        )

    def _find_quantity(self, query: Query, graph: MeaningGraph, question: str) -> Answer:
        """M4 — استخراج الكَمّيّات."""
        # نَبحَث في النَّصّ عَن أَرقام أَو أَلفاظ عَدَد
        nums = re.findall(r"\d+", graph.text)
        # أَلفاظ عَدَد عَرَبيَّة (heuristic)
        ar_nums = []
        for w in ["واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة",
                  "ثمانية", "تسعة", "عشرة", "مئة", "أَلف", "مليون"]:
            if w in graph.text:
                ar_nums.append(w)
        if not nums and not ar_nums:
            return Answer(
                query=query, kind="Zero",
                contract=self.CONTRACT_ANSWER,
                rejected_reason="لا كَمّيَّة مَكشوفَة",
            )
        all_nums = nums + ar_nums
        return Answer(
            query=query, kind="Hypothesis",
            contract=self.CONTRACT_ANSWER,
            answer=" / ".join(all_nums),
            evidence=[f"numeric_token:{n}" for n in all_nums],
        )

    def _find_instrument(self, query: Query, graph: MeaningGraph, question: str) -> Answer:
        instruments = []
        evidence = []
        for n in graph.nodes:
            if n.node_type in ("event", "transformation"):
                inst = n.attributes.get("instrument")
                if inst:
                    instruments.append(inst)
                    evidence.append(n.node_id)
        if not instruments:
            return Answer(
                query=query, kind="Zero",
                contract=self.CONTRACT_ANSWER,
                rejected_reason="لا أَداة مَكشوفَة",
            )
        return Answer(
            query=query, kind="Certificate" if len(instruments) == 1 else "Hypothesis",
            contract=self.CONTRACT_ANSWER,
            answer=" / ".join(set(instruments)),
            evidence=evidence,
        )

    def _check_existence(self, query: Query, graph: MeaningGraph, question: str) -> Answer:
        """هَل ذُكِرَ X في النَّصّ؟ نَستَخرِج اسم الـ entity مِن السُّؤال."""
        # heuristic: نَستَخرِج كُلّ entities المَوجودَة + نُجيب نَعَم/لا حَسَب وُجود تَطابُق سَطحيّ
        question_plain = _normalize(question)
        found = []
        for n in graph.nodes:
            if n.node_type == "entity":
                np = _normalize(n.surface)
                if np and np in question_plain:
                    found.append(n.surface)
        if found:
            return Answer(
                query=query, kind="Certificate",
                contract=self.CONTRACT_ANSWER,
                answer=f"نَعَم — مَوجود: {' / '.join(found)}",
                evidence=[n for n in found],
            )
        return Answer(
            query=query, kind="Certificate",
            contract=self.CONTRACT_ANSWER,
            answer="لا — لَم يُذكَر",
        )

    def _find_sequence(self, query: Query, graph: MeaningGraph, question: str) -> Answer:
        """PATCH 6 — Multi-event reasoning: ordered events in verse order,
        joined with → arrows. Must differ structurally from the
        find_events answer (which uses / separators)."""
        events = sorted(
            [n for n in graph.nodes if n.node_type in ("event", "transformation")],
            key=lambda n: n.position
        )
        if len(events) < 2:
            return Answer(
                query=query, kind="Zero",
                contract=self.CONTRACT_ANSWER,
                rejected_reason="حَدَث واحِد فَقَط — لا تَسَلسُل",
            )
        # PATCH 6 — prefer verb_surface labels (not node.surface which
        # is the noun-tagged stem). Cap at 8 to keep display compact.
        labels = []
        for n in events:
            label = ((n.attributes or {}).get("verb_surface") or n.surface)
            labels.append(label)
        labels_dedup = []
        seen = set()
        for l in labels:
            if l and l not in seen:
                seen.add(l)
                labels_dedup.append(l)
        head = labels_dedup[:8]
        rest = len(labels_dedup) - len(head)
        seq = " → ".join(head) + (f" → (+{rest})" if rest > 0 else "")
        return Answer(
            query=query, kind="Hypothesis",
            contract=self.CONTRACT_ANSWER,
            answer=seq,
            evidence=[e.node_id for e in events][:8],
        )

    def _find_transformation(self, query: Query, graph: MeaningGraph, question: str) -> Answer:
        trans_nodes = [n for n in graph.nodes if n.node_type == "transformation"]
        if not trans_nodes:
            return Answer(
                query=query, kind="Zero",
                contract=self.CONTRACT_ANSWER,
                rejected_reason="لا تَحَوُّل مَكشوف",
            )
        results = []
        for n in trans_nodes:
            sb = n.attributes.get("state_before", "—")
            sa = n.attributes.get("state_after", "—")
            results.append(f"{sb} → {sa}")
        return Answer(
            query=query, kind="Certificate" if len(results) == 1 else "Hypothesis",
            contract=self.CONTRACT_ANSWER,
            answer=" / ".join(results),
            evidence=[n.node_id for n in trans_nodes],
        )

    def _find_explicit_cause(self, query: Query, graph: MeaningGraph, question: str) -> Answer:
        """لِماذا؟ نَفحَص فَقَط لَو سَبَب صَريح بِـ بِسَبَب / لأنّ."""
        causes = []
        text = graph.text
        for marker in ["بِسَبَب", "بسبب", "لأنّ", "لان", "لِأَنّ", "إِذ", "حَيثُ"]:
            if marker in text:
                # نَأخُذ ما بَعد المُؤَشِّر
                idx = text.find(marker) + len(marker)
                cause = text[idx:idx+50].strip()
                causes.append(f"{marker}: {cause}")
        if not causes:
            return Answer(
                query=query, kind="Zero",
                contract=self.CONTRACT_ANSWER,
                rejected_reason="لَم يُذكَر سَبَب صَريح في النَّصّ. التَّفسير خارِج نِطاقي.",
            )
        return Answer(
            query=query, kind="Certificate",
            contract=self.CONTRACT_ANSWER,
            answer=" / ".join(causes),
        )


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("text", nargs="?")
    p.add_argument("--verse", help="آيَة (سُورة:آية)")
    p.add_argument("--ask", required=True, help="السُّؤال")
    args = p.parse_args()

    if args.verse:
        verses_path = _HERE.parent / "data" / "quran-uthmani-with-pause-mark.txt"
        surah, ayah = args.verse.split(":")
        text = None
        with open(verses_path, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) >= 3 and parts[0] == str(int(surah)) and parts[1] == str(int(ayah)):
                    text = parts[2]
                    break
        if not text:
            print(f"⚠ لَم نَجِد {args.verse}")
            sys.exit(1)
    elif args.text:
        text = args.text
    else:
        p.print_help()
        sys.exit(1)

    engine = ReasoningEngine()
    answer = engine.answer(text, args.ask)

    print(f"النَّصّ:   {text}")
    print(f"السُّؤال: {args.ask}")
    print(f"النَّوع:   {answer.query.query_type} | in_scope={answer.query.is_in_scope}")
    print(f"الجَواب: {answer}")
    if answer.evidence:
        print(f"الدَّليل: {answer.evidence}")
    print(f"العَقد:   {answer.contract}")


if __name__ == "__main__":
    main()
