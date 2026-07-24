from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

from spotify_lrc_overlay.models.lrc_parser import parse_lrc
from spotify_lrc_overlay.models.lyrics import Lyrics
from spotify_lrc_overlay.models.track import Track

LOGGER = logging.getLogger(__name__)


class LrclibError(RuntimeError):
    pass


@dataclass
class LrclibClient:
    base_url: str = "https://lrclib.net/api"
    timeout_seconds: float = 5.0
    max_retries: int = 3

    def __post_init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": "SpotifyLrcOverlay/0.1.0 (https://lrclib.net)"}
        )
        self._cache: dict[str, Lyrics | None] = {}

    def get_lyrics(self, track: Track) -> Lyrics | None:
        cache_key = track.key
        if cache_key in self._cache:
            return self._cache[cache_key]

        for attempt in range(1, self.max_retries + 1):
            try:
                lyrics = self._request_lyrics(track)
                self._cache[cache_key] = lyrics
                return lyrics
            except requests.RequestException as exc:
                delay = min(2.0, 0.3 * attempt)
                LOGGER.warning("LRCLIB request failed on attempt %s: %s", attempt, exc)
                time.sleep(delay)

        raise LrclibError(f"Failed to fetch lyrics for {track.display_name}")

    def _request_lyrics(self, track: Track) -> Lyrics | None:
        response = self._session.get(
            f"{self.base_url}/search",
            params={"track_name": track.title, "artist_name": track.artist},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        results = response.json()

        best = self._choose_best_result(results, track)
        if not best:
            LOGGER.info("No LRCLIB result for %s", track.display_name)
            return None

        synced = best.get("syncedLyrics")
        if not synced:
            LOGGER.info("LRCLIB result has no synced lyrics for %s", track.display_name)
            return None

        return parse_lrc(synced, source="LRCLIB")

    @staticmethod
    def _choose_best_result(results: list[dict], track: Track) -> dict | None:
        if not results:
            return None

        wanted_title = track.title.strip().lower()
        wanted_artist = track.artist.strip().lower()
        for item in results:
            item_title = str(item.get("trackName", "")).strip().lower()
            item_artist = str(item.get("artistName", "")).strip().lower()
            if item_title == wanted_title and item_artist == wanted_artist:
                return item

        for item in results:
            if item.get("syncedLyrics"):
                return item
        return results[0]
