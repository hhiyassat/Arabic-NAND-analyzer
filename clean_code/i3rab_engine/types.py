"""Data types for the i3rab engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Word classes — coarse top-level partition
WORD_CLASSES = (
    "HARF",        # particle: حرف جر / عطف / نفي / استفهام / ...
    "ISM_MABNI",   # built noun: ضمائر / أسماء إشارة / موصولة / استفهام / شرط
    "ISM_MUARAB",  # declinable noun: most derived nouns + non-essence جوامد
    "FIIL",        # verb: ماضٍ / مضارع / أمر
    "AALAM",       # proper noun (NOUN_PROP from MASAQ)
    "JAMID",       # essence noun (NOUN_CONCRETE from MASAQ)
    "JALALAH",     # لفظ الجلالة
    "UNKNOWN",
)

# i3rab cases (matches i3rab_ref/i3rab_cases.csv)
CASE_IDS = {
    1: "مَرْفُوع",
    2: "مَنْصُوب",
    3: "مَجْرُور",
    4: "مَجْزُوم",
    5: "مَبْنِي",
}

# Marks (matches i3rab_ref/i3rab_marks.csv)
MARK_IDS = {
    1: ("ضمة",        1, "الضَّمَّةُ الظَّاهِرَةُ"),
    2: ("ألف",        1, "الْأَلِفُ"),                 # مثنى مرفوع
    3: ("واو",        1, "الْوَاوُ"),                  # جمع مذكر سالم / الأسماء الخمسة
    4: ("فتحة",       2, "الْفَتْحَةُ الظَّاهِرَةُ"),
    5: ("ياء",        2, "الْيَاءُ"),                  # مثنى/جمع مذكر سالم منصوب
    6: ("كسرة",       3, "الْكَسْرَةُ الظَّاهِرَةُ"),
    7: ("ياء",        3, "الْيَاءُ"),                  # مثنى/جمع مذكر سالم مجرور
    8: ("سكون",       4, "السُّكُونُ الظَّاهِرُ"),
    9: ("حذف النون",  4, "حَذْفُ النُّونِ"),            # أفعال خمسة مجزومة
    10: ("كسرة",      2, "الْكَسْرَةُ"),                # جمع مؤنث سالم منصوب
    11: ("فتحة ممنوع", 2, "الْفَتْحَةُ ممنوع من الصرف"),
    12: ("فتحة ممنوع", 3, "الْفَتْحَةُ ممنوع من الصرف"),
    13: ("نون",       1, "ثُبُوتُ النُّونِ"),           # أفعال خمسة مرفوعة
    14: ("حذف نون",   2, "حَذْفُ النُّونِ"),            # أفعال خمسة منصوبة
}


@dataclass
class TokenI3rab:
    """Per-token i'rab analysis."""

    # Input
    token: str = ""           # surface form as it appeared
    token_plain: str = ""     # diacritic-stripped
    position: int = 0         # 0-based index in the sentence

    # Layer 1: WordClass
    word_class: str = "UNKNOWN"
    word_class_source: str = ""
    verb_aspect: str = ""     # PV / IV / CV / "" (for verbs only)

    # Layer 1 enrichment (from root_pipeline)
    root: str = ""
    wazn: str = ""

    # Closed-class enrichment
    closed_class_kind: str = ""   # HARF_JARR / ISM_MAWSOOL / DAMEER / ...
    operator_i3rab: str = ""      # default i3rab text from i3rab_operators.csv

    # Layer 2: Case + Mark
    case_id: Optional[int] = None
    case_source: str = ""
    mark_id: Optional[int] = None
    mark_source: str = ""
    # Tanwin marker: "ضم" / "فتح" / "كسر" / "" (empty if no tanwin).
    # Independent of mark_id so the 14-mark standard table stays clean.
    tanwin: str = ""

    # Layer 3: Role
    role_id: Optional[int] = None
    role_phrase: str = ""
    role_source: str = ""

    notes: list = field(default_factory=list)

    # Proof-theoretic metadata per layer (added 2026-05-20 per
    # 14_Minimal_Complete_Theory.md). Each layer's decision carries
    # its own kind/contract/blockers/alternatives.
    wordclass_kind: str = ""       # Certificate | Hypothesis | Zero
    wordclass_contract: str = ""
    wordclass_blockers: list = field(default_factory=list)
    wordclass_alternatives: list = field(default_factory=list)

    case_kind: str = ""
    case_contract: str = ""
    case_blockers: list = field(default_factory=list)
    case_alternatives: list = field(default_factory=list)

    role_kind: str = ""
    role_contract: str = ""
    role_blockers: list = field(default_factory=list)
    role_alternatives: list = field(default_factory=list)

    # Segmentation (carried through from the upstream segmenter)
    prefixes: list = field(default_factory=list)
    stem: str = ""
    suffixes: list = field(default_factory=list)

    # Phase 4 contextual-resolver metadata (added 2026-05-26).
    # Populated by engine.analyze_sentence ONLY when the
    # ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER flag is ON and
    # Layer 1 returns phase4_* keys. Empty dict otherwise — preserves
    # byte-identical flag-OFF behavior because to_dict() ignores it.
    # Keys (all optional, present only when produced upstream):
    #   phase4_selected_function, phase4_reason, phase4_context_features,
    #   phase4_masaq_compatible_class, phase4_original_candidates,
    #   phase4_certainty, phase4_source, phase4_unresolved_ambiguous
    phase4: dict = field(default_factory=dict)

    # === Proof-Theoretic structure (per 14_Minimal_Complete_Theory) ===
    # claims[] and trace[] are computed from the layer outputs by
    # engine.analyze_sentence(). They feed integrity_seal.compute_proof_trace_hash
    # — the ONLY place a hash exists in this token.
    # CONSTITUTIONAL RULE: no claim's source may cite a hash. The hash
    # seals; it does not explain. See clean_code/integrity_seal.py.
    claims: list = field(default_factory=list)    # [{id, value, source}]
    trace: list = field(default_factory=list)     # [{contract, result}]
    residuals: list = field(default_factory=list)
    integrity: dict = field(default_factory=dict)  # {canonicalization, hash_algorithm, proof_trace_hash}

    # Legacy old_nand fields REMOVED 2026-05-21. See archive/old_nand/LESSON.md
    # and archive/old_nand/LESSON_v2.md for why they were preserved as artifact
    # but excluded from the active TokenI3rab.

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "position": self.position,
            "word_class": self.word_class,
            "word_class_source": self.word_class_source,
            "verb_aspect": self.verb_aspect,
            "root": self.root,
            "wazn": self.wazn,
            "closed_class_kind": self.closed_class_kind,
            "operator_i3rab": self.operator_i3rab,
            "case_id": self.case_id,
            "case_name": CASE_IDS.get(self.case_id, "") if self.case_id else "",
            "case_source": self.case_source,
            "mark_id": self.mark_id,
            "mark_name": MARK_IDS[self.mark_id][0] if self.mark_id else "",
            "mark_source": self.mark_source,
            "role_id": self.role_id,
            "role_phrase": self.role_phrase,
            "role_source": self.role_source,
            "notes": list(self.notes),
            # Proof-theoretic per-layer
            "wordclass_proof": {
                "kind": self.wordclass_kind,
                "contract": self.wordclass_contract,
                "blockers": list(self.wordclass_blockers),
                "alternatives": list(self.wordclass_alternatives),
            },
            "case_proof": {
                "kind": self.case_kind,
                "contract": self.case_contract,
                "blockers": list(self.case_blockers),
                "alternatives": list(self.case_alternatives),
            },
            "role_proof": {
                "kind": self.role_kind,
                "contract": self.role_contract,
                "blockers": list(self.role_blockers),
                "alternatives": list(self.role_alternatives),
            },
        }


@dataclass
class SentenceI3rab:
    """Sentence-level i'rab — list of TokenI3rab plus inter-token relations."""

    text: str = ""
    tokens: list = field(default_factory=list)  # list[TokenI3rab]
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "tokens": [t.to_dict() for t in self.tokens],
            "notes": list(self.notes),
        }
