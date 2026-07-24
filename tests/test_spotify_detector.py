import unittest

from spotify_lrc_overlay.services.spotify_detector import _timespan_to_ms


class FakeTimeSpan:
    def __init__(self, duration: int) -> None:
        self.duration = duration


class SpotifyDetectorTest(unittest.TestCase):
    def test_timespan_duration_ticks_to_ms(self) -> None:
        self.assertEqual(_timespan_to_ms(FakeTimeSpan(12_345_000)), 1234)


if __name__ == "__main__":
    unittest.main()
