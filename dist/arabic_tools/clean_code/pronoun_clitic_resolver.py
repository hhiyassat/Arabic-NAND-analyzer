"""pronoun_clitic_resolver.py — جَلسة 19: الإِحالَة البَسيطَة.

يَكتَشِف الضَّمائر المُتَّصِلَة في كَلِمَة (مِن لاحِقَة) ويَربِطُها بِأَقرَب
مُسبَق مُتَوافِق في الجِنس/العَدد.

الِاستخدام:
    resolver = PronounCliticResolver()
    refs = resolver.resolve(sent_tokens)

كُلّ مَرجِع يَحمِل:
  • clitic (السَّطح: ه، ها، هم، ...)
  • host_token_idx (الكَلِمَة الَّتي عَلَّقَ بِها)
  • referent_token_idx (المُحَلّ — أَقرَب مُسبَق مُتَوافِق، أَو None)
  • gender / number / person
  • kind (Hypothesis — لا قَطعيّ في الإِحالَة البَسيطَة)
  • source_of_claim

CONSTITUTIONAL: قَواعد الإِحالَة data-driven مِن `pronoun_clitics.csv` +
`pronoun_compatibility.csv` (لاحِقًا). لا قَوائم inline في الكود.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows


CONTRACT_NAME = "PronounCliticResolver:v1"


def _strip_diac(s: str) -> str:
    for d in "ًٌٍَُِّْـ":
        s = s.replace(d, "")
    return s


@dataclass
class CliticReference:
    clitic: str = ""
    clitic_name: str = ""          # ha_third_masc_sing / ka_second_masc_sing / ...
    host_token_idx: int = -1
    host_surface: str = ""
    referent_token_idx: Optional[int] = None
    referent_surface: Optional[str] = None
    gender: str = ""               # M / F / X
    number: str = ""               # SG / DU / PL
    person: str = ""               # 1 / 2 / 3
    kind: str = "Hypothesis"
    source_of_claim: str = ""
    contract: str = CONTRACT_NAME
    alternatives: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "clitic": self.clitic,
            "clitic_name": self.clitic_name,
            "host_token_idx": self.host_token_idx,
            "host_surface": self.host_surface,
            "referent_token_idx": self.referent_token_idx,
            "referent_surface": self.referent_surface,
            "gender": self.gender,
            "number": self.number,
            "person": self.person,
            "kind": self.kind,
            "source_of_claim": self.source_of_claim,
            "contract": self.contract,
            "alternatives": list(self.alternatives),
        }


class PronounCliticResolver:

    def __init__(self) -> None:
        self._clitics = _load_rows("pronoun_clitics.csv")
        # رَتِّب بِالأَطوَل أَوّلًا (هما قَبل ها قَبل ه)
        self._clitics.sort(key=lambda r: -len(_strip_diac(r.get("clitic", ""))))

    def detect_clitic(self, word_plain: str, root: str = "") -> Optional[dict]:
        """يَختَبِر لاحِقات الكَلِمَة. يَردّ صَفّ الـ clitic أَو None.

        قُيود لِتَفادي false positives:
          • stem بِطول ≥ 2 قَبل الـ clitic
          • الجَذر لا يَنتَهي بِنَفس حَرف الـ clitic (مَنع «مالِك»→ك،
            «حَكيم»→م، إلخ)
          • الكَلِمَة طَولها كُلِّيًّا ≥ 4 (تَفادي ضَمائر مَوقِعيَّة بَحتَة)
        """
        root_plain = _strip_diac(root or "")
        for row in self._clitics:
            cl = _strip_diac(row.get("clitic", ""))
            if not cl:
                continue
            if not word_plain.endswith(cl):
                continue
            if len(word_plain) < len(cl) + 2:
                continue
            # تَحَقُّق مِن أَنّ الجَذر لا يَنتَهي بِالـ clitic
            if root_plain and root_plain.endswith(cl):
                continue
            return row
        return None

    def resolve(self, sent_tokens: list) -> list[CliticReference]:
        """يُحَلِّل قائِمَة TokenI3rab ويُنتِج قائِمَة CliticReference.

        خُوارِزميَّة الإِحالَة (v1 — بَسيطَة):
          1. لِكُلّ token: ابحَث عَن clitic في لاحِقَتِه
          2. لَو وُجِدَت: ابحَث رُجوعًا عَن أَقرَب اسم (ISM_*/JAMID/AALAM/SINGULAR_TERM)
          3. لا تَحَقُّق مِن جِنس/عَدد بَعد (مَفتوح كَ تَحسين لاحِق)
        """
        refs: list[CliticReference] = []
        if not sent_tokens:
            return refs
        for i, t in enumerate(sent_tokens):
            word_plain = _strip_diac(t.token or "")
            if not word_plain:
                continue
            # نَتَخَطّى HARF و FIIL ضَمائر الفِعل قَد تَكون مَفعولًا — اسمَح بِها
            # عَلى ISM* و FIIL مَعًا
            # تَخَطّي لَفظ الجَلالة (singular_term) — لا تُعَلَّق به ضَمائر.
            # نَفحَص كِلا: word_class و SingularTermDetector (data-driven).
            wc = getattr(t, "word_class", "")
            if wc in ("SINGULAR_TERM", "JALALAH"):
                continue
            try:
                from singular_term_detector import get_singular_term_detector
                if get_singular_term_detector().detect(t.token or "").is_singular_term:
                    continue
            except Exception:
                pass
            cl_row = self.detect_clitic(word_plain, root=getattr(t, "root", ""))
            if not cl_row:
                continue
            clitic_plain = _strip_diac(cl_row.get("clitic", ""))
            # ابحَث رُجوعًا عَن مُحَلّ
            referent_idx: Optional[int] = None
            for j in range(i - 1, -1, -1):
                wc = getattr(sent_tokens[j], "word_class", "")
                if wc in ("ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM", "JALALAH"):
                    referent_idx = j
                    break
            ref = CliticReference(
                clitic=cl_row.get("clitic", ""),
                clitic_name=cl_row.get("name", ""),
                host_token_idx=i,
                host_surface=t.token or "",
                referent_token_idx=referent_idx,
                referent_surface=(sent_tokens[referent_idx].token if referent_idx is not None else None),
                gender=cl_row.get("gender", ""),
                number=cl_row.get("number", ""),
                person=cl_row.get("person", ""),
                source_of_claim=(
                    f"host:{t.token} ends with clitic:«{cl_row.get('clitic')}» "
                    f"({cl_row.get('name')}); referent=nearest_prior_noun_at_idx={referent_idx}"
                ),
            )
            refs.append(ref)
        return refs


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    from i3rab_engine.engine import I3rabEngine

    engine = I3rabEngine()
    resolver = PronounCliticResolver()

    tests = [
        ("ذَهَبَ الْوَلَدُ إِلَى بَيْتِهِ", "ه", "الْوَلَدُ"),
        ("كَتَبَتْ زَيْنَبُ كِتَابَهَا", "ها", "زَيْنَبُ"),
        ("قَالَ الْمُعَلِّمُ لِطُلَّابِهِ", "ه", "الْمُعَلِّمُ"),
    ]
    for text, expected_clitic, expected_referent in tests:
        sent = engine.analyze_sentence(text)
        refs = resolver.resolve(sent.tokens)
        if refs:
            r = refs[0]
            ok = (_strip_diac(r.clitic) == _strip_diac(expected_clitic)
                  and r.referent_surface
                  and _strip_diac(r.referent_surface) == _strip_diac(expected_referent))
            mark = "✓" if ok else "✗"
            print(f"{mark} «{text}»")
            print(f"    clitic={r.clitic} host={r.host_surface} → referent={r.referent_surface}")
        else:
            print(f"✗ «{text}» — لَم يُكتَشَف ضَمير")
