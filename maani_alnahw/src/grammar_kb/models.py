"""grammar_kb/models.py — نَماذِج بَيانات قاعِدَة المَعرِفَة النَّحويَّة.

كُلّ سِجِلّ JSON-serializable.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Optional


# ─── مَرجِع الكِتاب ─────────────────────────────────────────────────────────

@dataclass
class SourceRef:
    book: str = "معاني النحو"
    author: str = "فاضل صالح السامرائي"
    part: int = 0
    page_start: int = 0
    page_end: Optional[int] = None
    raw_excerpt: Optional[str] = None       # مَقتَطَع قَصير جِدًّا فَقَط
    cleaned_excerpt: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ─── صَفحَة ───────────────────────────────────────────────────────────────

@dataclass
class Page:
    doc_id: str
    part: int
    page: int
    raw_text: str
    source_file: str
    cleaned_text: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ─── تَصحيح OCR ────────────────────────────────────────────────────────────

@dataclass
class OCRCorrection:
    part: int
    page: int
    raw: str
    normalized: str
    reason: list = field(default_factory=list)
    confidence: float = 0.0
    action: str = "applied"          # applied / suggest_only / rejected

    def to_dict(self) -> dict:
        return asdict(self)


# ─── مَوضوع / باب ──────────────────────────────────────────────────────────

@dataclass
class Topic:
    topic_id: str
    title: str
    part: int
    start_page: int
    end_page: Optional[int] = None
    parent_topic_id: Optional[str] = None
    raw_heading: str = ""
    normalized_heading: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


# ─── بِطاقَة قاعِدَة ────────────────────────────────────────────────────────

@dataclass
class RuleCard:
    rule_id: str
    topic_id: str
    title: str
    source: dict = field(default_factory=dict)
    trigger: dict = field(default_factory=dict)
    syntactic_effect: dict = field(default_factory=dict)
    semantic_effect: dict = field(default_factory=dict)
    conditions: list = field(default_factory=list)
    exceptions_or_warnings: list = field(default_factory=list)
    examples: list = field(default_factory=list)
    author_position: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


# ─── مِثال ─────────────────────────────────────────────────────────────────

@dataclass
class Example:
    example_id: str
    rule_id: str
    text: str
    type: str = "constructed_example"   # constructed_example / quranic_example / poetic_example
    source: dict = field(default_factory=dict)
    expected_analysis: dict = field(default_factory=dict)
    surah: Optional[str] = None
    surah_num: Optional[int] = None
    ayah: Optional[int] = None
    needs_quran_verification: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# ─── خِلاف عُلَماء ────────────────────────────────────────────────────────

@dataclass
class Opinion:
    opinion_id: str
    topic_id: str
    issue: str
    opinions: list = field(default_factory=list)  # [{holder, claim, status}]
    source: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ─── تَحليل تَركيب ──────────────────────────────────────────────────────────

@dataclass
class ConstructionAnalysis:
    construction_id: str
    surface_parse: dict = field(default_factory=dict)
    deep_predication: str = ""
    semantic_effect: str = ""
    modality: str = ""
    source: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ─── تَركيب العَدَد المَعدود ───────────────────────────────────────────────

@dataclass
class NumberCountedPhrase:
    span: str
    type: str = "NUMBER_COUNTED_PHRASE"
    numeric_value: int = 0
    number_structure: dict = field(default_factory=dict)
    counted: dict = field(default_factory=dict)
    semantic_entity: dict = field(default_factory=dict)
    agreement_check: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ─── قاعِدَة دَلاليَّة لِحَرف جَرّ ───────────────────────────────────────────

@dataclass
class PrepositionSemanticRule:
    rule_id: str
    preposition: str
    primary_meaning: str
    secondary_meanings: list = field(default_factory=list)
    substitution_rejected_for: list = field(default_factory=list)
    tadmeen_alternative_for: list = field(default_factory=list)
    source: dict = field(default_factory=dict)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


# ─── قاعِدَة تَضمين ────────────────────────────────────────────────────────

@dataclass
class TadmeenRule:
    rule_id: str
    surface_verb: str
    original_meaning: str
    included_meaning: str
    evidence: str
    semantic_gain: str
    source: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ─── دَعوى دَلاليَّة (SemanticClaim) — أَصغَر وَحدَة ─────────────────────────

@dataclass
class SemanticClaim:
    """أَصغَر دَعوى مَعنويَّة قابِلَة لِلِاستخراج مِن صَفحَة."""
    claim_id: str
    part: int
    page: int
    topic_id: Optional[str] = None
    topic_title: Optional[str] = None
    paragraph_id: Optional[str] = None
    raw_excerpt: str = ""             # مَقتَطَع قَصير مِن النَّصّ
    cleaned_excerpt: str = ""         # بَعدَ تَنظيف OCR
    normalized_claim: str = ""        # صياغَة عَرَبيَّة سَلِسَة
    claim_type: str = ""              # واحِد مِن 20 نَوعًا (see taxonomy)
    grammatical_focus: list = field(default_factory=list)
    semantic_focus: list = field(default_factory=list)
    triggers: dict = field(default_factory=dict)
    examples_mentioned: list = field(default_factory=list)
    quran_refs: list = field(default_factory=list)
    scholars_mentioned: list = field(default_factory=list)
    author_position: Optional[str] = None
    certainty_level: str = "asserted"  # asserted / probable / contested / hypothetical
    confidence: float = 0.0
    needs_manual_review: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# ─── بِطاقَة مَعنًى (MeaningCard) — عُنقود مِن claims ───────────────────────

@dataclass
class MeaningCard:
    meaning_id: str
    title: str
    meaning_type: str = ""            # construction_meaning / particle_meaning / ...
    topic_path: list = field(default_factory=list)
    description: str = ""
    syntactic_effect: dict = field(default_factory=dict)
    semantic_effect: dict = field(default_factory=dict)
    triggers: dict = field(default_factory=dict)
    conditions: list = field(default_factory=list)
    exceptions: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    examples: list = field(default_factory=list)
    source_claims: list = field(default_factory=list)  # list of claim_ids
    source_refs: list = field(default_factory=list)
    engine_applicability: str = "interpretive_note"
    # values: direct_rule / heuristic_rule / interpretive_note / review_only
    confidence: float = 0.0
    needs_manual_review: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# ─── تَغطيَة الصَّفحات ──────────────────────────────────────────────────────

@dataclass
class PageCoverage:
    part: int
    page: int
    topic_title: Optional[str] = None
    char_count: int = 0
    paragraph_count: int = 0
    claims_count: int = 0
    meaning_cards_count: int = 0
    has_ocr_warnings: bool = False
    extraction_status: str = "extracted"
    # values: extracted / no_semantic_content / low_confidence / needs_manual_review
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ─── سَطر طابور المُراجَعَة اليَدَويَّة ──────────────────────────────────

@dataclass
class ManualReviewItem:
    part: int
    page: int
    reason: str = ""
    suggested_action: str = "manual review"
    raw_excerpt_sample: str = ""
    confidence: float = 0.0
    related_topic: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)
