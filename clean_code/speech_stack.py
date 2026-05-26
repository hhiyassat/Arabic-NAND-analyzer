"""speech_stack.py — مُكَدِّس الإِطارات لِلقَول المُتَداخِل.

في النَّصّ القُرآنيّ كَثيرًا ما تَتَداخَل الأُطُر:
  • الله يَأمُر النَّبيّ أَن يَقول → frame 1: الله → النَّبيّ، يَحتَوي frame 2 (مَأمور بِه)
  • قال زيد قال عمرو سأذهب → frame 1: زيد، يَحتَوي frame 2: عمرو

كُلّ push يَضيف إِطار جَديد، كُلّ pop يَرجِع لِلسابِق. الـ stack يَحفَظ
الـ frame النَّشِط حاليًّا.
"""

from __future__ import annotations

from typing import Optional
from speech_frame import SpeechFrame


CONTRACT_NAME = "SpeechStack:v1"


class SpeechStack:

    def __init__(self):
        self._stack: list[SpeechFrame] = []
        self._all_frames: list[SpeechFrame] = []  # كُلّ الأُطُر بِالتَّرتيب
        self._counter = 0

    def push(self, frame: SpeechFrame) -> SpeechFrame:
        self._counter += 1
        if not frame.frame_id:
            frame.frame_id = f"frame_{self._counter}"
        # رَبط بِالأَب إِن وُجِد
        if self._stack and not frame.parent_frame_id:
            frame.parent_frame_id = self._stack[-1].frame_id
        self._stack.append(frame)
        self._all_frames.append(frame)
        return frame

    def pop(self) -> Optional[SpeechFrame]:
        if self._stack:
            return self._stack.pop()
        return None

    @property
    def current(self) -> Optional[SpeechFrame]:
        return self._stack[-1] if self._stack else None

    @property
    def depth(self) -> int:
        return len(self._stack)

    def all_frames(self) -> list[SpeechFrame]:
        return list(self._all_frames)

    def to_dict(self) -> dict:
        return {
            "contract": CONTRACT_NAME,
            "depth": self.depth,
            "n_frames_total": len(self._all_frames),
            "frames": [f.to_dict() for f in self._all_frames],
        }
