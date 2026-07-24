from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LyricLine:
    time_ms: int
    text: str


@dataclass
class Lyrics:
    lines: list[LyricLine]
    source: str = ""

    def line_at(self, position_ms: int) -> str:
        current, _next = self.lines_at(position_ms)
        return current

    def lines_at(self, position_ms: int) -> tuple[str, str]:
        if not self.lines:
            return "", ""

        left = 0
        right = len(self.lines) - 1
        best = 0
        while left <= right:
            mid = (left + right) // 2
            if self.lines[mid].time_ms <= position_ms:
                best = mid
                left = mid + 1
            else:
                right = mid - 1

        current = self.lines[best].text
        next_text = self.lines[best + 1].text if best + 1 < len(self.lines) else ""
        return current, next_text
