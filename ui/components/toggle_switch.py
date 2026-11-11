# ui/components/toggle_switch.py - iOS Style Smooth Toggle Switch for Windows Dynamic Island
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen


class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = True, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._circle_position = 20.0 if checked else 3.0
        self.setFixedSize(42, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"circle_position", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self._start_animation()
            self.toggled.emit(self._checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._start_animation()
            self.toggled.emit(self._checked)
        super().mousePressEvent(event)

    def _start_animation(self):
        start_val = self._circle_position
        end_val = 21.0 if self._checked else 3.0
        self._anim.stop()
        self._anim.setStartValue(start_val)
        self._anim.setEndValue(end_val)
        self._anim.start()

    def get_circle_position(self) -> float:
        return self._circle_position

    def set_circle_position(self, pos: float):
        self._circle_position = pos
        self.update()

    circle_position = pyqtProperty(float, get_circle_position, set_circle_position)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background Track
        track_color = QColor(48, 209, 88) if self._checked else QColor(70, 75, 90)
        p.setBrush(QBrush(track_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, 42, 24, 12, 12)

        # Circle Knob
        knob_color = QColor(255, 255, 255)
        p.setBrush(QBrush(knob_color))
        p.drawEllipse(int(self._circle_position), 3, 18, 18)

        p.end()
