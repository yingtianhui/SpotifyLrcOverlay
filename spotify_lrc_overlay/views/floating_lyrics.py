from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class FloatingLyricsWindow(QWidget):
    offset_decreased = Signal()
    offset_increased = Signal()
    offset_reset = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._drag_offset: QPoint | None = None
        self.setWindowTitle("Spotify LRC Overlay")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(820, 142)

        self._close_button = self._make_button("X", QApplication.quit, width=28)
        self._close_button.setToolTip("关闭")

        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)
        title_bar.addStretch(1)
        title_bar.addWidget(self._close_button)

        self._label = QLabel("等待 Spotify 播放...")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setFont(QFont("Microsoft YaHei UI", 26, QFont.Weight.Bold))
        self._label.setStyleSheet("color: white; background: transparent;")

        self._next_label = QLabel("")
        self._next_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._next_label.setWordWrap(True)
        self._next_label.setFont(QFont("Microsoft YaHei UI", 18, QFont.Weight.DemiBold))
        self._next_label.setStyleSheet(
            "color: rgba(255, 255, 255, 170); background: transparent;"
        )

        self._offset_label = QLabel("提前 1500ms")
        self._offset_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._offset_label.setFont(QFont("Microsoft YaHei UI", 10))
        self._offset_label.setStyleSheet("color: rgba(255, 255, 255, 180);")

        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addStretch(1)
        controls.addWidget(self._make_button("-100", self.offset_decreased.emit))
        controls.addWidget(self._offset_label)
        controls.addWidget(self._make_button("重置", self.offset_reset.emit))
        controls.addWidget(self._make_button("+100", self.offset_increased.emit))
        controls.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 10, 22, 12)
        layout.setSpacing(3)
        layout.addLayout(title_bar)
        layout.addWidget(self._label)
        layout.addWidget(self._next_label)
        layout.addLayout(controls)

        self.resize(1020, 176)
        self.move(500, 780)

    def set_lyric(self, text: str) -> None:
        current, _, next_text = text.partition("\n")
        self._label.setText(current)
        self._next_label.setText(next_text)

    def set_offset_ms(self, offset_ms: int) -> None:
        self._offset_label.setText(f"提前 {offset_ms}ms")

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(0, 0, 0, 100))
        painter.setPen(QPen(QColor(255, 255, 255, 55), 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 10, 10)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        child = self.childAt(event.position().toPoint())
        if isinstance(child, QPushButton):
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            event.accept()

    def closeEvent(self, event) -> None:
        event.accept()

    @staticmethod
    def _make_button(text: str, callback, width: int = 54) -> QPushButton:
        button = QPushButton(text)
        button.setFixedSize(width, 24)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(callback)
        button.setStyleSheet(
            """
            QPushButton {
                color: white;
                background: rgba(255, 255, 255, 42);
                border: 1px solid rgba(255, 255, 255, 72);
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 72);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 96);
            }
            """
        )
        return button
