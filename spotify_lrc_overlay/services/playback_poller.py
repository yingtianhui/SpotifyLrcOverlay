from __future__ import annotations

import asyncio
import logging

from PySide6.QtCore import QThread, Signal

from spotify_lrc_overlay.models.track import PlaybackSnapshot
from spotify_lrc_overlay.services.spotify_detector import CompositeSpotifyDetector

LOGGER = logging.getLogger(__name__)


class PlaybackPoller(QThread):
    snapshot_ready = Signal(object)
    error = Signal(str)

    def __init__(self, interval_seconds: float = 0.1) -> None:
        super().__init__()
        self._interval_seconds = interval_seconds
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        asyncio.run(self._poll())

    async def _poll(self) -> None:
        detector = CompositeSpotifyDetector()
        retry_delay = self._interval_seconds

        while self._running:
            try:
                snapshot: PlaybackSnapshot = await detector.snapshot()
                self.snapshot_ready.emit(snapshot)
                retry_delay = self._interval_seconds
                await self._sleep_while_running(self._interval_seconds)
            except Exception as exc:
                LOGGER.exception("Playback polling failed")
                self.error.emit(str(exc))
                await self._sleep_while_running(min(5.0, retry_delay))
                retry_delay = min(5.0, retry_delay * 1.8)

    async def _sleep_while_running(self, seconds: float) -> None:
        remaining = seconds
        while self._running and remaining > 0:
            step = min(0.1, remaining)
            await asyncio.sleep(step)
            remaining -= step
