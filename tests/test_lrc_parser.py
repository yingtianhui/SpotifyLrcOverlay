import unittest

from spotify_lrc_overlay.models.lrc_parser import parse_lrc


class LrcParserTest(unittest.TestCase):
    def test_parse_multiple_time_tags_and_sort(self) -> None:
        lyrics = parse_lrc("[00:10.50]second\n[00:01.000][00:02.000]first")

        self.assertEqual([line.time_ms for line in lyrics.lines], [1000, 2000, 10500])
        self.assertEqual(lyrics.line_at(1500), "first")
        self.assertEqual(lyrics.line_at(11000), "second")


if __name__ == "__main__":
    unittest.main()
