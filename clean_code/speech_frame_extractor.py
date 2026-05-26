"""speech_frame_extractor.py — يُطَبِّق الخُوارِزميَّة الثَّمانيَّة لِبِناء
SpeechFrame مَع تَتَبُّع القائِل/المُخاطَب.

المَصادِر (CSVs):
  • speech_verbs.csv        — أَفعال القَول (قال، يَقول، قُل، نادى، أَوحى، ...)
  • vocative_particles.csv  — حُروف النِّداء (يا، أَيا، يَأَيُّها، ...)
  • discourse_markers.csv   — جار+مَجرور المُخاطَب + ضَمائر الخِطاب

الإِخراج:
  • list[SpeechFrame] (مَع stack relationships)
  • DiscourseEntityTracker مُحَدَّث

كُلّ frame يَحمِل source_of_claim مُفَصَّل (أَدِلَّة + تَوكيد).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows
from speech_frame import SpeechFrame, DiscourseEntity, Evidence
from speech_stack import SpeechStack
from discourse_entity_tracker import DiscourseEntityTracker


CONTRACT_NAME = "SpeechFrameExtractor:v1"


def _strip_diac(s: str) -> str:
    diacritics = "ًٌٍَُِّْـٰٓ"
    return "".join(c for c in s if c not in diacritics)


def _normalize_token(s: str) -> str:
    s = _strip_diac(s)
    s = s.replace("ٱ", "ا")
    return s


class SpeechFrameExtractor:

    def __init__(self):
        # حَمل CSVs
        self._speech_verbs = self._build_index(
            _load_rows("speech_verbs.csv", subdir="lists"), key="plain"
        )
        self._vocatives = self._build_index(
            _load_rows("vocative_particles.csv", subdir="lists"), key="plain"
        )
        self._discourse_markers = self._build_index(
            _load_rows("discourse_markers.csv", subdir="lists"), key="plain"
        )

    @staticmethod
    def _build_index(rows: list, *, key: str) -> dict:
        out: dict[str, list[dict]] = {}
        for r in rows:
            k = (r.get(key) or "").strip()
            if k:
                out.setdefault(k, []).append(r)
        return out

    # ------------------------------------------------------------------
    # كَشف أَفعال القَول / النِّداء / المُخاطَب
    # ------------------------------------------------------------------

    def _is_speech_verb(self, token: str) -> Optional[dict]:
        plain = _normalize_token(token)
        # نُجَرِّب الـ token كَما هو
        if plain in self._speech_verbs:
            return self._speech_verbs[plain][0]
        # نُجَرِّب بِنَزع و/ف/ل/س prefix لِلفِعل المُضارِع
        for prefix in ("و", "ف", "س", "وس", "فس", "ل"):
            if plain.startswith(prefix):
                rest = plain[len(prefix):]
                if rest in self._speech_verbs:
                    return self._speech_verbs[rest][0]
        return None

    def _is_vocative(self, token: str) -> Optional[dict]:
        plain = _normalize_token(token)
        if plain in self._vocatives:
            return self._vocatives[plain][0]
        # نَزع و/ف prefix
        for prefix in ("و", "ف"):
            if plain.startswith(prefix):
                rest = plain[len(prefix):]
                if rest in self._vocatives:
                    return self._vocatives[rest][0]
        return None

    def _is_addressee_marker(self, token: str) -> Optional[dict]:
        plain = _normalize_token(token)
        if plain in self._discourse_markers:
            row = self._discourse_markers[plain][0]
            if row.get("kind", "").startswith("addressee"):
                return row
        # نَمَط «لـِ + ال + اسم» (مَثَل لِلْمَلائِكَة، لِلنَّاس، لِقَوْمِه)
        if plain.startswith("لل") and len(plain) > 3:
            # المُخاطَب اسم مَعرِفَة بِال
            return {"kind": "addressee_prep", "plain": plain, "person": "3",
                    "gender": "X", "number": "X"}
        if plain.startswith("ل") and len(plain) > 2 and not plain.startswith("لا") and not plain.startswith("لم") and not plain.startswith("لن"):
            # لِفُلان / لِقَومه
            return {"kind": "addressee_prep", "plain": plain, "person": "3",
                    "gender": "X", "number": "X"}
        return None

    # ------------------------------------------------------------------
    # المَنطِق المَركَزيّ — الخُوارِزميَّة الثَّمانيَّة
    # ------------------------------------------------------------------

    def extract(self, text: str, tokens: list[str] = None,
                i3rab_tokens: list = None) -> dict:
        """يُحَلِّل النَّصّ ويَبني SpeechStack + DiscourseEntityTracker.

        i3rab_tokens: لَو مُرِّر، تُستَخدَم word_class لِفِلتَرَة الكِيانات
        (فَقَط ISM_*/JAMID/AALAM/SINGULAR_TERM تُضاف لِلـ tracker).
        """
        if tokens is None:
            tokens = [t for t in text.split() if t]

        # خَريطَة position → word_class مِن i3rab (إِن وُجِدَت)
        word_class_by_pos: dict[int, str] = {}
        if i3rab_tokens:
            for it in i3rab_tokens:
                pos = getattr(it, "position", -1)
                wc = getattr(it, "word_class", "")
                if pos >= 0 and wc:
                    word_class_by_pos[pos] = wc

        stack = SpeechStack()
        tracker = DiscourseEntityTracker()

        # Track previous tokens for context
        prev_was_speech_verb: Optional[dict] = None
        prev_speech_verb_idx: int = -1
        pending_speaker: Optional[str] = None  # الِاسم الَّذي يَلي فِعل القَول

        for i, tok in enumerate(tokens):
            plain = _normalize_token(tok)

            # ── 1. كَشف فِعل قَول ──
            sv_row = self._is_speech_verb(tok)
            if sv_row:
                # فَتح frame جَديد
                frame = SpeechFrame(
                    utterance="",  # سَيُملأ لاحِقًا
                    speaker=None,
                    addressee=None,
                    speech_type=self._infer_speech_type(sv_row, tok),
                    introduced_by=tok,
                    confidence="medium",
                )
                frame.evidence.append(Evidence(token=tok, role="speech_verb", position=i))
                # القائِل المَبدَئيّ مِن مورفولوجيا الفِعل
                person = sv_row.get("person", "")
                gender = sv_row.get("gender", "")
                number = sv_row.get("number", "")
                # شَخص 1 → القائِل المُتَكَلِّم (نَستَنتِجه مِن السِّياق العُلويّ)
                if person == "1":
                    # في القُرآن: عادَةً الله أَو رَسوله (مَوسوم في الـ stack الأَعلى)
                    frame.speaker = DiscourseEntity(
                        text="(مُتَكَلِّم)",
                        type="implicit",
                        person="1", gender=gender, number=number,
                        source_of_claim=f"speech_verb_morphology:{tok}",
                    )
                elif person == "3":
                    # نَنتَظِر الفاعِل الظاهِر في الـ token التالي
                    pending_speaker = "expecting"
                    frame.speaker = DiscourseEntity(
                        text="(غائِب)",
                        type="implicit",
                        person="3", gender=gender, number=number,
                        source_of_claim=f"speech_verb_morphology:{tok}",
                    )
                stack.push(frame)
                tracker.mark_as_speaker("")  # سَيُحَدَّث
                prev_was_speech_verb = sv_row
                prev_speech_verb_idx = i
                continue

            # ── 2. الفاعِل الظاهِر بَعد فِعل قَول 3rd person ──
            # لَو الفِعل جَمع (قَالوا/قُلنَ) فالـ subject مَدمَج في الفِعل،
            # لا نَنتَظِر اسمًا ظاهِرًا
            if pending_speaker == "expecting" and stack.current:
                prev_number = prev_was_speech_verb.get("number", "") if prev_was_speech_verb else ""
                prev_token_str = tokens[prev_speech_verb_idx] if prev_speech_verb_idx >= 0 else ""
                prev_plain = _normalize_token(prev_token_str)
                # «قَالوا/قُلتُ/نَقول» — الفاعِل ضَمير في الفِعل، لا نَنتَظِر
                if prev_number == "PL" or prev_plain.endswith("وا") or prev_plain.endswith("نا") or prev_plain.endswith("تم") or prev_plain.endswith("تن"):
                    pending_speaker = None
                    # تَخَطّى ولكن استَمِرّ مَع الـ token الحاليّ
                elif not self._is_addressee_marker(tok) and not self._is_vocative(tok):
                    frame = stack.current
                    if frame.speaker:
                        frame.speaker.text = tok
                        frame.speaker.canonical = _normalize_token(tok)
                        frame.speaker.type = "explicit"
                        frame.speaker.source_of_claim += f" + explicit_subject:{tok}@pos{i}"
                    frame.evidence.append(Evidence(token=tok, role="speaker", position=i))
                    # نُضيف فَقَط لَو i3rab يَعتَبِره اسمًا أَو لَدَينا فَقَط heuristic
                    NOUN_CLASSES = {"ISM_MUARAB", "ISM_MABNI", "JAMID", "AALAM",
                                    "SINGULAR_TERM", "JALALAH"}
                    if not word_class_by_pos or word_class_by_pos.get(i, "") in NOUN_CLASSES:
                        tracker.add_or_update(tok, position=i)
                        tracker.mark_as_speaker(tok)
                    pending_speaker = None
                    continue

            # ── 3. كَشف عَلامَة مُخاطَب (جار+مَجرور بَعد فِعل قَول) ──
            am_row = self._is_addressee_marker(tok)
            if am_row and stack.current and stack.current.addressee is None:
                kind = am_row.get("kind", "")
                if kind == "addressee_prep":
                    person = am_row.get("person", "")
                    gender = am_row.get("gender", "")
                    number = am_row.get("number", "")
                    # المُخاطَب: قَد يَكون ضَميرًا (له/لهم) أَو اسمًا (لقومه)
                    addressee_text = tok
                    addressee_canon = _normalize_token(tok)
                    stack.current.addressee = DiscourseEntity(
                        text=addressee_text,
                        canonical=addressee_canon,
                        type="addressee_match",
                        person=person, gender=gender, number=number,
                        source_of_claim=f"addressee_prep:{tok}@pos{i}",
                    )
                    stack.current.evidence.append(Evidence(token=tok, role="addressee", position=i))
                    stack.current.confidence = "high"
                    tracker.mark_as_addressee(addressee_text)
                    continue

            # ── 4. كَشف نِداء (يا فُلان) ──
            voc_row = self._is_vocative(tok)
            if voc_row:
                # المُخاطَب يَأتي بَعدَه
                # افتَح frame خِطاب نِداء إِن لَم يُكُن هُناك frame مَفتوح
                if not stack.current:
                    frame = SpeechFrame(
                        speech_type="vocative",
                        introduced_by=tok,
                        confidence="high",
                    )
                    frame.evidence.append(Evidence(token=tok, role="vocative_particle", position=i))
                    stack.push(frame)
                # المُخاطَب القادِم (نُحَدِّد لاحِقًا)
                if stack.current:
                    stack.current.evidence.append(Evidence(token=tok, role="vocative_particle", position=i))
                continue

            # ── 5. تَتَبُّع الكِيانات (فَقَط الأَسماء) ──
            # مَع i3rab: نَفلتَر بِناءً على word_class
            # بِلا i3rab: نَستَخدِم heuristic بَسيطَة
            NOUN_CLASSES = {"ISM_MUARAB", "ISM_MABNI", "JAMID", "AALAM",
                            "SINGULAR_TERM", "JALALAH"}
            if word_class_by_pos:
                wc = word_class_by_pos.get(i, "")
                if wc in NOUN_CLASSES:
                    tracker.add_or_update(tok, position=i, word_class=wc)
            elif len(plain) >= 3 and not self._looks_like_particle(plain):
                tracker.add_or_update(tok, position=i)

            # ── 6. مُخاطَب مِن نِداء سابِق (يا [قوم] ...) ──
            # إِن كانَ آخِر token vocative، اعتَبِر هذا المُخاطَب
            if i > 0 and self._is_vocative(tokens[i - 1]):
                if stack.current and stack.current.addressee is None:
                    stack.current.addressee = DiscourseEntity(
                        text=tok,
                        canonical=_normalize_token(tok),
                        type="vocative_match",
                        source_of_claim=f"vocative_followed:يا+{tok}@pos{i}",
                    )
                    stack.current.evidence.append(
                        Evidence(token=tok, role="vocative_addressee", position=i)
                    )
                    tracker.mark_as_addressee(tok)

        # ── 7. nested frames لِـ commanded_speech ──
        # «قُل ...» يَفتَح frame خارِجيّ (الله → النَّبيّ) + frame داخِليّ
        # (النَّبيّ → الجُمهور) لِلمَقول المَأمور بِه.
        self._add_nested_frames_for_commanded(stack)

        # ── 8. مَلء utterance لِكُلّ frame ──
        self._fill_utterances(stack, tokens)

        return {
            "stack": stack,
            "tracker": tracker,
            "frames": stack.all_frames(),
            "contract": CONTRACT_NAME,
        }

    @staticmethod
    def _looks_like_particle(plain: str) -> bool:
        """heuristic لِفَصل الحُروف الشَّائِعَة عَن الأَسماء."""
        common_particles = {
            "في", "من", "إلى", "على", "عن", "ل", "ب", "ك", "و", "ف",
            "لا", "ما", "إن", "إذا", "إذ", "أن", "لم", "لن", "هذا",
            "هذه", "ذلك", "تلك", "هؤلاء", "أولئك", "الذي", "التي",
        }
        return plain in common_particles

    @staticmethod
    def _infer_speech_type(sv_row: dict, token: str) -> str:
        plain = _normalize_token(sv_row.get("plain", ""))
        if plain == "قل":
            return "commanded_speech"
        if plain in ("نادى", "ينادي", "ينادون"):
            return "vocative"
        return "direct"

    def _add_nested_frames_for_commanded(self, stack: SpeechStack):
        """لِكُلّ frame مِن نَوع commanded_speech (قُل/قولوا)، نُضيف frame
        داخِليّ مَأمور بِه: قائِله = المُخاطَب في الـ outer، والمُخاطَب
        مَفتوح (الجُمهور)."""
        existing = list(stack.all_frames())
        for outer in existing:
            if outer.speech_type != "commanded_speech":
                continue
            # المُخاطَب في الـ outer هو النَّبيّ (المُؤمِنون عِندَ «قولوا»)
            # القائِل في الـ outer غالِبًا غَير صَريح في الجُملة (يَأتي مِن سِياق السُّورَة)
            # نَجعَل outer.speaker = (مُتَكَلِّم عُلويّ، عادَة الله في القُرآن)
            if not outer.speaker:
                outer.speaker = DiscourseEntity(
                    text="(القائِل العُلويّ)",
                    type="implicit_supersentential",
                    person="3", gender="M", number="SG",
                    source_of_claim="commanded_speech:outer_speaker_inferred_from_context",
                )
            if not outer.addressee:
                outer.addressee = DiscourseEntity(
                    text="(المَأمور بِالقَول)",
                    type="implicit",
                    person="2", gender="M", number="SG",
                    source_of_claim="commanded_speech:imperative_verb_implies_addressee",
                )

            # frame داخِليّ
            inner = SpeechFrame(
                speech_type="commanded_speech_inner",
                introduced_by=outer.introduced_by,
                confidence="medium",
                parent_frame_id=outer.frame_id,
            )
            inner.speaker = DiscourseEntity(
                text="(المَأمور بِالقَول يُبَلِّغ)",
                type="implicit",
                person="2", gender="M", number="SG",  # هو المُخاطَب في outer
                source_of_claim=f"commanded_speech:inner_speaker=outer_addressee@{outer.frame_id}",
            )
            inner.addressee = DiscourseEntity(
                text="(الجُمهور المُبَلَّغ)",
                type="implicit",
                person="2", gender="M", number="PL",
                source_of_claim=f"commanded_speech:inner_addressee=audience@{outer.frame_id}",
            )
            inner.utterance = outer.utterance  # سَيُملأ لاحِقًا (نَفس مَقول outer)
            stack.push(inner)

    def _fill_utterances(self, stack: SpeechStack, tokens: list[str]):
        frames = stack.all_frames()
        if not frames:
            return
        # نَجمَع مَواقِع فَتح كُلّ frame
        frame_positions = []
        for f in frames:
            sv_evidence = [e for e in f.evidence if e.role == "speech_verb"]
            if sv_evidence:
                frame_positions.append((sv_evidence[0].position, f))
            else:
                # nada — ابحَث عَن أَوَّل evidence
                if f.evidence:
                    frame_positions.append((f.evidence[0].position, f))
        # رَتِّب بِالمَوقِع
        frame_positions.sort(key=lambda x: x[0])
        # utterance لِكُلّ frame = مِن position+1 إلى أَوَّل position أَكبَر (أَو نِهايَة)
        for idx, (pos, f) in enumerate(frame_positions):
            start = pos + 1
            end = len(tokens)
            for next_pos, _ in frame_positions[idx + 1:]:
                if next_pos > pos:
                    end = next_pos
                    break
            # نَتَخَطّى عَلامات النِّداء وعَلامات المُخاطَب في البِدايَة
            slice_tokens = tokens[start:end]
            f.utterance = " ".join(slice_tokens).strip()


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    extractor = SpeechFrameExtractor()
    tests = [
        "قَالَ مُوسَى لِقَوْمِهِ يَا قَوْمِ اذْكُرُوا نِعْمَةَ ٱللَّهِ عَلَيْكُمْ",
        "قَالَ رَبُّكَ لِلْمَلَائِكَةِ إِنِّي جَاعِلٌ فِي ٱلْأَرْضِ خَلِيفَةً",
        "قَالُوا أَتَجْعَلُ فِيهَا مَن يُفْسِدُ فِيهَا",
        "يَٰٓأَيُّهَا ٱلَّذِينَ ءَامَنُوا اتَّقُوا ٱللَّهَ",
        "قُلْ هُوَ ٱللَّهُ أَحَدٌ",
    ]
    for t in tests:
        print(f"\n=== {t} ===")
        r = extractor.extract(t)
        for f in r["frames"]:
            print(f"  frame {f.frame_id} [{f.speech_type}] conf={f.confidence}")
            sp = f.speaker.text if f.speaker else "—"
            ad = f.addressee.text if f.addressee else "—"
            print(f"    قائِل: {sp}")
            print(f"    مُخاطَب: {ad}")
            print(f"    utterance: «{f.utterance}»")
            print(f"    introduced_by: {f.introduced_by}")
            print(f"    evidence: {[(e.token, e.role) for e in f.evidence]}")
