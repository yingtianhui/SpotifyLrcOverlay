from __future__ import annotations

import logging
import os
import time

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot

from spotify_lrc_overlay.models.lyrics import Lyrics
from spotify_lrc_overlay.models.track import PlaybackSnapshot, Track
from spotify_lrc_overlay.services.lrclib_client import LrclibClient
from spotify_lrc_overlay.services.playback_poller import PlaybackPoller
from spotify_lrc_overlay.views.floating_lyrics import FloatingLyricsWindow

LOGGER = logging.getLogger(__name__)
DEFAULT_LYRIC_ADVANCE_MS = 1500
MIN_LYRIC_ADVANCE_MS = 800
MAX_LYRIC_ADVANCE_MS = 2000
LYRIC_ADVANCE_STEP_MS = 100


class LyricsFetchSignals(QObject):
    finished = Signal(object, object, object)


class LyricsFetchTask(QRunnable):
    def __init__(self, client: LrclibClient, track: Track) -> None:
        super().__init__()
        self.signals = LyricsFetchSignals()
        self._client = client
        self._track = track

    @Slot()
    def run(self) -> None:
        try:
            lyrics = self._client.get_lyrics(self._track)
            self.signals.finished.emit(self._track, lyrics, None)
        except Exception as exc:
            self.signals.finished.emit(self._track, None, exc)


class LyricsController(QObject):
    def __init__(self) -> None:
        super().__init__()
        self._window = FloatingLyricsWindow()
        self._window.offset_decreased.connect(self._decrease_offset)
        self._window.offset_increased.connect(self._increase_offset)
        self._window.offset_reset.connect(self._reset_offset)

        self._poller = PlaybackPoller(interval_seconds=0.1)
        self._poller.snapshot_ready.connect(self._on_snapshot)
        self._poller.error.connect(self._on_error)
        self._thread_pool = QThreadPool.globalInstance()
        self._client = LrclibClient()

        self._current_track: Track | None = None
        self._current_lyrics: Lyrics | None = None
        self._last_snapshot: PlaybackSnapshot | None = None
        self._last_text = ""
        self._pending_keys: set[str] = set()

        self._last_reported_position_ms = 0
        self._estimated_position_ms = 0
        self._last_progress_tick = time.monotonic()
        self._last_diagnostic_log = 0.0
        self._lyric_advance_ms = _read_lyric_advance_ms()
        self._window.set_offset_ms(self._lyric_advance_ms)

    def start(self) -> None:
        self._window.show()
        self._poller.start()

    @Slot()
    def stop(self) -> None:
        self._poller.stop()
        self._poller.wait(1500)

    @Slot(object)
    def _on_snapshot(self, snapshot: PlaybackSnapshot) -> None:
        self._last_snapshot = snapshot
        track = snapshot.track
        if track is None:
            self._current_track = None
            self._current_lyrics = None
            self._reset_progress()
            self._set_text("等待 Spotify 播放...")
            return

        if self._current_track is None or track.key != self._current_track.key:
            LOGGER.info("Track changed: %s via %s", track.display_name, snapshot.detected_by)
            self._current_track = track
            self._current_lyrics = None
            self._reset_progress(snapshot.position_ms)
            self._set_text(f"正在加载歌词：{track.display_name}")
            self._fetch_lyrics(track)

        position_ms = self._resolve_position(snapshot)
        self._log_diagnostics(snapshot, position_ms)

        if self._current_lyrics:
            self._set_lyrics_for_position(position_ms, track)

    @Slot(str)
    def _on_error(self, message: str) -> None:
        LOGGER.warning("Poller error: %s", message)
        self._set_text("检测 Spotify 时出错，正在重试...")

    def _fetch_lyrics(self, track: Track) -> None:
        if track.key in self._pending_keys:
            return
        self._pending_keys.add(track.key)
        task = LyricsFetchTask(self._client, track)
        task.signals.finished.connect(self._on_lyrics_loaded)
        self._thread_pool.start(task)

    @Slot(object, object, object)
    def _on_lyrics_loaded(
        self,
        track: Track,
        lyrics: Lyrics | None,
        error: Exception | None,
    ) -> None:
        self._pending_keys.discard(track.key)
        if self._current_track is None or track.key != self._current_track.key:
            return

        if error is not None:
            LOGGER.warning("Lyrics fetch failed for %s: %s", track.display_name, error)
            self._set_text(f"歌词加载失败，正在重试：{track.display_name}")
            QTimer.singleShot(5000, lambda: self._retry_lyrics(track))
            return

        self._current_lyrics = lyrics
        if lyrics and lyrics.lines:
            position_ms = max(self._estimated_position_ms, self._last_reported_position_ms)
            self._set_lyrics_for_position(position_ms, track)
            LOGGER.info("Loaded %s lyric lines for %s", len(lyrics.lines), track.display_name)
        else:
            self._set_text(f"未找到同步歌词：{track.display_name}")
            LOGGER.info("No synced lyrics for %s", track.display_name)

    def _set_text(self, text: str) -> None:
        if text == self._last_text:
            return
        self._last_text = text
        self._window.set_lyric(text)

    def _retry_lyrics(self, track: Track) -> None:
        if self._current_track is not None and track.key == self._current_track.key:
            self._fetch_lyrics(track)

    def _set_lyrics_for_position(self, position_ms: int, track: Track) -> None:
        if not self._current_lyrics:
            return
        display_position_ms = position_ms + self._lyric_advance_ms
        current, next_text = self._current_lyrics.lines_at(display_position_ms)
        if current and next_text:
            self._set_text(f"{current}\n{next_text}")
        else:
            self._set_text(current or track.display_name)

    def _reset_progress(self, position_ms: int = 0) -> None:
        now = time.monotonic()
        self._last_reported_position_ms = max(0, position_ms)
        self._estimated_position_ms = max(0, position_ms)
        self._last_progress_tick = now
        self._last_diagnostic_log = 0.0

    def _resolve_position(self, snapshot: PlaybackSnapshot) -> int:
        now = time.monotonic()
        elapsed_ms = max(0, int((now - self._last_progress_tick) * 1000))
        reported_ms = max(0, snapshot.position_ms)

        if reported_ms > 0 and abs(reported_ms - self._last_reported_position_ms) >= 50:
            self._estimated_position_ms = reported_ms
        elif snapshot.is_playing:
            self._estimated_position_ms += elapsed_ms

        self._last_reported_position_ms = reported_ms
        self._last_progress_tick = now
        return self._estimated_position_ms

    def _set_offset(self, offset_ms: int) -> None:
        self._lyric_advance_ms = max(MIN_LYRIC_ADVANCE_MS, min(MAX_LYRIC_ADVANCE_MS, offset_ms))
        self._window.set_offset_ms(self._lyric_advance_ms)
        LOGGER.info("Lyric offset changed to %sms", self._lyric_advance_ms)
        if self._current_track and self._current_lyrics:
            self._set_lyrics_for_position(self._estimated_position_ms, self._current_track)

    @Slot()
    def _decrease_offset(self) -> None:
        self._set_offset(self._lyric_advance_ms - LYRIC_ADVANCE_STEP_MS)

    @Slot()
    def _increase_offset(self) -> None:
        self._set_offset(self._lyric_advance_ms + LYRIC_ADVANCE_STEP_MS)

    @Slot()
    def _reset_offset(self) -> None:
        self._set_offset(DEFAULT_LYRIC_ADVANCE_MS)

    def _log_diagnostics(self, snapshot: PlaybackSnapshot, resolved_position_ms: int) -> None:
        now = time.monotonic()
        if now - self._last_diagnostic_log < 5.0:
            return
        self._last_diagnostic_log = now
        track_name = snapshot.track.display_name if snapshot.track else "None"
        LOGGER.info(
            "Playback: %s | playing=%s | reported=%sms | resolved=%sms | lyric_position=%sms | detected_by=%s",
            track_name,
            snapshot.is_playing,
            snapshot.position_ms,
            resolved_position_ms,
            resolved_position_ms + self._lyric_advance_ms,
            snapshot.detected_by,
        )


def _read_lyric_advance_ms() -> int:
    raw_value = os.environ.get("SPOTIFY_LRC_OFFSET_MS", "")
    if not raw_value:
        return DEFAULT_LYRIC_ADVANCE_MS
    try:
        value = int(raw_value)
    except ValueError:
        LOGGER.warning(
            "Invalid SPOTIFY_LRC_OFFSET_MS=%r, using %sms",
            raw_value,
            DEFAULT_LYRIC_ADVANCE_MS,
        )
        return DEFAULT_LYRIC_ADVANCE_MS
    return max(MIN_LYRIC_ADVANCE_MS, min(MAX_LYRIC_ADVANCE_MS, value))
