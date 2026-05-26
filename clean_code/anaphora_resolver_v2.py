"""anaphora_resolver_v2.py — حَلّ الضَّمائر باستخدام SpeechFrame + EntityTracker.

يَحُلّ مَحَلّ `pronoun_clitic_resolver.py` (v1 البَدائيّ الَّذي يَختار «أَقرَب اسم»).

المَنطِق الجَديد:
  • ضَمير المُخاطَب (شَخص 2: كم/ك/كما/كن) → addressee مِن الـ active SpeechFrame
  • ضَمير المُتَكَلِّم (شَخص 1: ي/نا) → speaker مِن الـ active SpeechFrame
  • ضَمير الغائِب (شَخص 3: ه/ها/هم/هن/هما) → كِيان مُتَوافِق جِنسًا/عَدَدًا في EntityTracker

كُلّ resolution يَحمِل:
  • source_of_claim مُفَصَّل (مِن أَيّ frame، مِن أَيّ entity)
  • kind (Certificate إِن مِن frame صَريح، Hypothesis إِن مِن خَلفيَّة، Zero إِن لا مَرجِع)
  • alternatives إِن كانَ هُناك أَكثَر مِن مَرشَّح

CONSTITUTIONAL: كُلّ القَواعِد data-driven مِن:
  • pronoun_clitics.csv (الضَّمائر + سِماتها)
  • singular_terms.csv (لِتَخَطّي الجَلالة)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows
from speech_frame import SpeechFrame, DiscourseEntity
from gender_detector import GenderDetector
from agreement_checker import AgreementChecker


CONTRACT_NAME = "AnaphoraResolver:v2"


def _strip_diac(s: str) -> str:
    diacritics = "ًٌٍَُِّْـٰٓ"
    return "".join(c for c in s if c not in diacritics)


@dataclass
class ResolvedReference:
    clitic: str = ""
    clitic_name: str = ""
    host_token: str = ""
    host_position: int = -1
    referent_text: Optional[str] = None
    referent_source: str = ""        # frame_addressee / frame_speaker / entity_match / unresolved
    referent_frame_id: Optional[str] = None
    gender: str = ""
    number: str = ""
    person: str = ""
    kind: str = "Hypothesis"         # Certificate / Hypothesis / Zero
    source_of_claim: str = ""
    contract: str = CONTRACT_NAME
    alternatives: list = field(default_factory=list)
    blockers: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "clitic": self.clitic,
            "clitic_name": self.clitic_name,
            "host_token": self.host_token,
            "host_surface": self.host_token,  # alias لِلتَّوافُق مَع v1 display
            "host_position": self.host_position,
            "host_token_idx": self.host_position,  # alias
            "referent_text": self.referent_text,
            "referent_surface": self.referent_text,  # alias
            "referent_token_idx": self.referent_text,  # alias (لَيس index لَكِن نَصّ)
            "referent_source": self.referent_source,
            "referent_frame_id": self.referent_frame_id,
            "gender": self.gender,
            "number": self.number,
            "person": self.person,
            "kind": self.kind,
            "source_of_claim": self.source_of_claim,
            "blockers": list(self.blockers),
            "alternatives": list(self.alternatives),
            "contract": self.contract,
        }


class AnaphoraResolverV2:

    def __init__(self):
        self._clitics = _load_rows("pronoun_clitics.csv")
        # رَتِّب بِالأَطوَل أَوّلًا
        self._clitics.sort(key=lambda r: -len(_strip_diac(r.get("clitic", ""))))
        self._gender_det = GenderDetector()
        self._agreement = AgreementChecker()

    def _detect_clitic(self, word_plain: str, root: str = "") -> Optional[dict]:
        root_plain = _strip_diac(root or "")
        for row in self._clitics:
            cl = _strip_diac(row.get("clitic", ""))
            if not cl:
                continue
            if not word_plain.endswith(cl):
                continue
            if len(word_plain) < len(cl) + 2:
                continue
            # لا يَنتَهي بِنَفس حَرف الـ clitic في الجَذر
            if root_plain and root_plain.endswith(cl):
                continue
            return row
        return None

    def resolve(
        self,
        tokens: list,                       # list[TokenI3rab] أَو list[str]
        frames: list[SpeechFrame] = None,    # SpeechFrames لِنَفس الجُملة
        tracker = None,                      # DiscourseEntityTracker
    ) -> list[ResolvedReference]:
        """يُحَلِّل tokens، يَستَخرِج الضَّمائر، ويَحُلُّها باستخدام السِّياق.

        frames: قائِمَة SpeechFrames المُكتَشَفَة في الجُملة (مِن SpeechFrameExtractor)
        tracker: DiscourseEntityTracker مَع الكِيانات المَفتوحَة
        """
        # تَخَطّى لَفظ مُنفَرِد
        try:
            from singular_term_detector import get_singular_term_detector
            stdet = get_singular_term_detector()
        except Exception:
            stdet = None

        results: list[ResolvedReference] = []
        # نَستَخرِج الـ active addressee/speaker مِن آخِر frame
        active_frame = frames[-1] if frames else None

        for i, tok in enumerate(tokens):
            token_str = tok.token if hasattr(tok, "token") else str(tok)
            if not token_str:
                continue
            word_plain = _strip_diac(token_str)

            # تَخَطّى الجَلالة
            if stdet and stdet.detect(token_str).is_singular_term:
                continue

            # كَشف clitic
            root = getattr(tok, "root", "") if hasattr(tok, "root") else ""
            cl_row = self._detect_clitic(word_plain, root=root)
            if not cl_row:
                continue

            person = cl_row.get("person", "")
            gender = cl_row.get("gender", "")
            number = cl_row.get("number", "")
            clitic = cl_row.get("clitic", "")

            ref = ResolvedReference(
                clitic=clitic,
                clitic_name=cl_row.get("name", ""),
                host_token=token_str,
                host_position=i,
                gender=gender,
                number=number,
                person=person,
            )

            # ── حَلّ بِناءً على الشَّخص ──
            if person == "2":
                # ضَمير مُخاطَب → addressee مِن الـ active frame
                if active_frame and active_frame.addressee:
                    ref.referent_text = active_frame.addressee.text
                    ref.referent_source = "frame_addressee"
                    ref.referent_frame_id = active_frame.frame_id
                    ref.kind = "Certificate" if active_frame.confidence == "high" else "Hypothesis"
                    ref.source_of_claim = (
                        f"person=2 → addressee from frame "
                        f"{active_frame.frame_id} ({active_frame.addressee.source_of_claim})"
                    )
                else:
                    ref.referent_source = "unresolved_addressee"
                    ref.kind = "Zero"
                    ref.blockers.append("no_active_frame_with_addressee")
                    ref.source_of_claim = (
                        f"person=2 — لا frame مَفتوح بِمُخاطَب صَريح؛ "
                        f"يَحتاج تَتَبُّع المُخاطَب عَبر السُّورَة"
                    )

            elif person == "1":
                # ضَمير مُتَكَلِّم → speaker مِن الـ active frame
                if active_frame and active_frame.speaker and active_frame.speaker.text != "(مُتَكَلِّم)" and active_frame.speaker.text != "(غائِب)":
                    ref.referent_text = active_frame.speaker.text
                    ref.referent_source = "frame_speaker"
                    ref.referent_frame_id = active_frame.frame_id
                    ref.kind = "Certificate" if active_frame.confidence == "high" else "Hypothesis"
                    ref.source_of_claim = (
                        f"person=1 → speaker from frame "
                        f"{active_frame.frame_id}"
                    )
                else:
                    ref.referent_source = "unresolved_speaker"
                    ref.kind = "Zero"
                    ref.blockers.append("no_active_frame_with_speaker")
                    ref.source_of_claim = (
                        f"person=1 — لا قائِل صَريح؛ "
                        f"يَحتاج تَتَبُّع المُتَكَلِّم عَبر السِّياق"
                    )

            elif person == "3":
                # ضَمير غائِب → كِيان مُتَوافِق جِنسًا/عَدَدًا (فَحص قَطعيّ بِـ AgreementChecker)
                if tracker:
                    # 1) اِجلِب المُرَشَّحين. لِلـ F.SG، نَجلِب أَيضًا الـ PL لِأَنّ
                    #    جَمع غَير العاقِل قَد يُطابِق بِـ F.SG.
                    if hasattr(tracker, "find_all_compatible"):
                        candidates = tracker.find_all_compatible(
                            gender=gender, number=number, person="3",
                            before_position=i, strict_gender=True,
                        )
                        if gender == "F" and number == "SG":
                            # أَضِف الـ PL كَ مُرَشَّحين بَديلين (لِلجَمع غَير العاقِل)
                            extra = tracker.find_all_compatible(
                                gender="X", number="PL", person="3",
                                before_position=i, strict_gender=False,
                            )
                            seen = {id(c) for c in candidates}
                            for c in extra:
                                if id(c) not in seen:
                                    candidates.append(c)
                    else:
                        fc = tracker.find_compatible(
                            gender=gender, number=number, person="3",
                            before_position=i,
                        )
                        candidates = [fc] if fc else []

                    # 2) لِكُلّ مُرَشَّح، فَحص قَطعيّ بِـ AgreementChecker + GenderDetector
                    pronoun_features = {
                        "clitic": clitic, "gender": gender,
                        "number": number, "person": person,
                    }
                    accepted = []
                    rejected = []
                    for cand in candidates:
                        if cand is None:
                            continue
                        # فَحص المُطابَقَة عَبر AgreementChecker
                        ag = self._agreement.check_pronoun_referent(
                            pronoun_features, cand.surface,
                        )
                        if ag.status in ("valid", "valid_non_human_plural"):
                            accepted.append((cand, ag))
                        else:
                            rejected.append((cand, ag))

                    if accepted:
                        # نَختار الأَحدَث (المُرَشَّحون مُرَتَّبون بِالأَحدَث)
                        cand, ag = accepted[0]
                        ref.referent_text = cand.surface
                        ref.referent_source = "entity_match"
                        ref.kind = "Certificate" if ag.status == "valid" else "Hypothesis"
                        ref.source_of_claim = (
                            f"person=3 + gender={gender} + number={number} → "
                            f"«{cand.canonical}» (last_pos={cand.last_position}) "
                            f"— AgreementChecker: {ag.status} "
                            f"(conf={ag.confidence})"
                        )
                        # alternatives
                        for alt_cand, alt_ag in accepted[1:]:
                            ref.alternatives.append({
                                "referent": alt_cand.surface,
                                "canonical": alt_cand.canonical,
                                "last_pos": alt_cand.last_position,
                                "status": alt_ag.status,
                                "confidence": alt_ag.confidence,
                            })
                    else:
                        ref.referent_source = "unresolved_3rd"
                        ref.kind = "Zero"
                        ref.blockers.append("no_agreement_passed")
                        rejected_summary = [
                            f"«{c.surface}»:{a.status}" for c, a in rejected[:3]
                        ]
                        ref.source_of_claim = (
                            f"person=3 + gender={gender} + number={number} — "
                            f"لا كِيان نَجَح في AgreementChecker. "
                            f"المَرفوضون: {', '.join(rejected_summary) if rejected_summary else 'لا مُرَشَّحين'}"
                        )
                else:
                    ref.referent_source = "no_tracker"
                    ref.kind = "Zero"
                    ref.blockers.append("tracker_unavailable")

            results.append(ref)

        return results
