from __future__ import annotations

import asyncio
import logging
import re
import time

from spotify_lrc_overlay.models.track import PlaybackSnapshot, Track

LOGGER = logging.getLogger(__name__)

BROWSER_SOURCES = ("chrome", "msedge", "firefox", "brave", "opera")


class BaseDetector:
    async def snapshot(self) -> PlaybackSnapshot:
        raise NotImplementedError


class WindowsMediaSessionDetector(BaseDetector):
    def __init__(self) -> None:
        self._manager = None
        self._last_metadata_read = 0.0
        self._last_track: Track | None = None

    async def _ensure_manager(self):
        if self._manager is None:
            from winsdk.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as SessionManager,
            )

            self._manager = await SessionManager.request_async()
        return self._manager

    async def snapshot(self) -> PlaybackSnapshot:
        manager = await self._ensure_manager()
        sessions = list(manager.get_sessions())
        session = self._select_spotify_session(sessions) or manager.get_current_session()
        if not session:
            return PlaybackSnapshot(track=None, position_ms=0, is_playing=False, detected_by="media-session")

        playback = session.get_playback_info()
        timeline = session.get_timeline_properties()
        status = str(playback.playback_status).lower()
        is_playing = "playing" in status
        position_ms = _timespan_to_ms(timeline.position)

        now = time.monotonic()
        if self._last_track is None or now - self._last_metadata_read >= 1.0:
            media = await session.try_get_media_properties_async()
            source = str(session.source_app_user_model_id or "")
            title = str(media.title or "").strip()
            artist = str(media.artist or "").strip()
            album = str(media.album_title or "").strip()
            self._last_metadata_read = now
            self._last_track = (
                Track(title=title, artist=artist, album=album, source=source) if title else None
            )

        if not self._last_track:
            return PlaybackSnapshot(track=None, position_ms=position_ms, is_playing=is_playing, detected_by="media-session")

        return PlaybackSnapshot(
            track=self._last_track,
            position_ms=position_ms,
            is_playing=is_playing,
            detected_by="media-session",
        )

    @staticmethod
    def _select_spotify_session(sessions):
        spotify_like = []
        browser_like = []
        for session in sessions:
            source = str(session.source_app_user_model_id or "").lower()
            if "spotify" in source:
                spotify_like.append(session)
            elif any(browser in source for browser in BROWSER_SOURCES):
                browser_like.append(session)
        return spotify_like[0] if spotify_like else (browser_like[0] if browser_like else None)


class WindowTitleFallbackDetector(BaseDetector):
    title_pattern = re.compile(r"(?P<artist>.+?)\s+-\s+(?P<title>.+)")

    def __init__(self) -> None:
        self._last_read = 0.0
        self._last_title = ""

    async def snapshot(self) -> PlaybackSnapshot:
        now = time.monotonic()
        if now - self._last_read >= 1.0:
            self._last_title = await asyncio.to_thread(self._find_spotify_window_title)
            self._last_read = now

        title = self._last_title
        if not title:
            return PlaybackSnapshot(track=None, position_ms=0, is_playing=False, detected_by="window-title")

        match = self.title_pattern.match(title)
        if match:
            track = Track(
                title=match.group("title").strip(),
                artist=match.group("artist").strip(),
                source="window-title",
            )
        else:
            track = Track(title=title.strip(), artist="", source="window-title")

        return PlaybackSnapshot(track=track, position_ms=0, is_playing=True, detected_by="window-title")

    @staticmethod
    def _find_spotify_window_title() -> str:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        titles: list[str] = []

        enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def callback(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            text = buffer.value.strip()
            lowered = text.lower()
            if text and ("spotify" in lowered or " - " in text):
                titles.append(text.replace(" - Spotify", "").strip())
            return True

        user32.EnumWindows(enum_proc_type(callback), 0)
        for title in titles:
            if title and title.lower() != "spotify":
                return title
        return ""


class CompositeSpotifyDetector(BaseDetector):
    def __init__(self) -> None:
        self._primary: BaseDetector | None = None
        self._primary_retry_after = 0.0
        self._fallback = WindowTitleFallbackDetector()

    async def snapshot(self) -> PlaybackSnapshot:
        now = time.monotonic()
        if self._primary is None and now >= self._primary_retry_after:
            try:
                self._primary = WindowsMediaSessionDetector()
            except Exception as exc:
                LOGGER.warning("Windows media session unavailable: %s", exc)
                self._primary_retry_after = now + 5.0

        if self._primary is not None:
            try:
                snapshot = await self._primary.snapshot()
                if snapshot.track:
                    return snapshot
            except Exception as exc:
                LOGGER.warning("Media session snapshot failed, falling back: %s", exc)
                self._primary = None
                self._primary_retry_after = now + 5.0

        return await self._fallback.snapshot()


def _timespan_to_ms(value) -> int:
    if value is None:
        return 0
    if hasattr(value, "total_seconds"):
        return max(0, int(value.total_seconds() * 1000))
    if hasattr(value, "duration"):
        return max(0, int(value.duration / 10_000))
    try:
        return max(0, int(value / 10_000))
    except (TypeError, ValueError):
        return 0
