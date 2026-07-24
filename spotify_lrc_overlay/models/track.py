from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Track:
    title: str
    artist: str
    album: str = ""
    source: str = ""

    @property
    def key(self) -> str:
        return f"{self.artist.strip().lower()}::{self.title.strip().lower()}"

    @property
    def display_name(self) -> str:
        if self.artist:
            return f"{self.title} - {self.artist}"
        return self.title


@dataclass(frozen=True)
class PlaybackSnapshot:
    track: Track | None
    position_ms: int
    is_playing: bool
    detected_by: str = ""
