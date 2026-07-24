from __future__ import annotations

import re

from spotify_lrc_overlay.models.lyrics import LyricLine, Lyrics


TIME_TAG_RE = re.compile(r"\[(?P<min>\d{1,3}):(?P<sec>\d{2})(?:[.:](?P<frac>\d{1,3}))?\]")


def parse_lrc(raw_lrc: str, source: str = "LRCLIB") -> Lyrics:
    lines: list[LyricLine] = []

    for raw_line in raw_lrc.splitlines():
        tags = list(TIME_TAG_RE.finditer(raw_line))
        if not tags:
            continue

        text = TIME_TAG_RE.sub("", raw_line).strip()
        for tag in tags:
            minutes = int(tag.group("min"))
            seconds = int(tag.group("sec"))
            fraction = tag.group("frac") or "0"
            millis = int(fraction.ljust(3, "0")[:3])
            time_ms = minutes * 60_000 + seconds * 1000 + millis
            lines.append(LyricLine(time_ms=time_ms, text=text))

    lines.sort(key=lambda line: line.time_ms)
    return Lyrics(lines=lines, source=source)
