import sys

from PySide6.QtWidgets import QApplication

from spotify_lrc_overlay.controllers.lyrics_controller import LyricsController
from spotify_lrc_overlay.utils.logging_config import configure_logging


def main() -> int:
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("Spotify LRC Overlay")
    controller = LyricsController()
    app.aboutToQuit.connect(controller.stop)
    controller.start()
    return app.exec()
