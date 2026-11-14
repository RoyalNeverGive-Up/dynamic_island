# ui/components/custom_interval_dialog.py - Topmost Styled Modal for Custom Interval Input
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSpinBox, QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QMouseEvent
from ui.styles import THEME, MAIN_STYLE
from ui.components.icons import make_close_icon


class CustomIntervalDialog(QDialog):
    def __init__(self, title: str = "自定义提醒间隔", prompt: str = "请输入提醒间隔 (分钟):",
                 initial_value: int = 45, min_val: int = 1, max_val: int = 720, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(460, 310)
        self.setStyleSheet(MAIN_STYLE)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._title_text = title
        self._prompt_text = prompt
        self._initial_val = initial_value
        self._min_val = min_val
        self._max_val = max_val
        self._selected_value = initial_value
        self._drag_pos = None

        self._init_ui()

        # Center on parent or screen
        if parent and hasattr(parent, "window") and parent.window():
            p_geo = parent.window().geometry()
            x = p_geo.x() + (p_geo.width() - self.width()) // 2
            y = p_geo.y() + (p_geo.height() - self.height()) // 2
        else:
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
        self.move(max(20, x), max(20, y))

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        container = QFrame(self)
        container.setObjectName("IslandContainer")
        container.setStyleSheet("""
            background-color: #141724;
            border: 1.5px solid #38BDF8;
            border-radius: 18px;
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(56, 189, 248, 120))
        shadow.setOffset(0, 5)
        container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)

        # 1. Header
        header = QHBoxLayout()
        header.setSpacing(10)
        icon_lbl = QLabel("⏱️")
        icon_lbl.setStyleSheet("font-size: 18px;")
        header.addWidget(icon_lbl)

        title_lbl = QLabel(self._title_text)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #38BDF8;")
        header.addWidget(title_lbl)
        header.addStretch()

        close_btn = QPushButton()
        close_btn.setObjectName("IconButton")
        close_btn.setFixedSize(28, 28)
        close_btn.setIcon(make_close_icon(14))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setToolTip("取消并关闭")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # 2. Prompt Label
        prompt_lbl = QLabel(self._prompt_text)
        prompt_lbl.setStyleSheet("color: #E2E8F0; font-size: 13px; font-weight: 600; line-height: 1.3;")
        layout.addWidget(prompt_lbl)

        # 3. Dedicated Large SpinBox Input
        self.spin = QSpinBox()
        self.spin.setRange(self._min_val, self._max_val)
        self.spin.setValue(self._initial_val)
        self.spin.setSuffix("  分钟后")
        self.spin.setSingleStep(5)
        self.spin.setFixedHeight(44)
        self.spin.setStyleSheet("""
            QSpinBox {
                background: #1E2337;
                color: #FFFFFF;
                border: 1.5px solid rgba(56, 189, 248, 0.5);
                border-radius: 8px;
                padding: 4px 14px;
                font-size: 16px;
                font-weight: 800;
            }
            QSpinBox:focus {
                border: 2px solid #38BDF8;
                background: #232A42;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 24px;
                background: rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                margin: 2px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: rgba(56, 189, 248, 0.3);
            }
        """)
        layout.addWidget(self.spin)

        # 4. Quick preset pills row
        pills_box = QVBoxLayout()
        pills_box.setSpacing(6)

        pill_title = QLabel("快捷预设:")
        pill_title.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        pills_box.addWidget(pill_title)

        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(6)
        presets = [
            ("15分钟", 15),
            ("25分钟", 25),
            ("30分钟", 30),
            ("45分钟", 45),
            ("60分钟", 60),
            ("90分钟", 90),
        ]
        for lbl, p in presets:
            pill = QPushButton(lbl)
            pill.setFixedHeight(30)
            pill.setCursor(Qt.CursorShape.PointingHandCursor)
            pill.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.07);
                    color: #CBD5E1;
                    border: 1px solid rgba(255, 255, 255, 0.14);
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 2px 6px;
                }
                QPushButton:hover {
                    background: rgba(56, 189, 248, 0.25);
                    color: #38BDF8;
                    border-color: #38BDF8;
                }
            """)
            pill.clicked.connect(lambda chk, val=p: self.spin.setValue(val))
            pills_layout.addWidget(pill)
        pills_box.addLayout(pills_layout)
        layout.addLayout(pills_box)

        layout.addStretch()

        # 5. Action Buttons (Cancel / Confirm)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #CBD5E1;
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 7px;
                padding: 6px 18px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.16);
                color: #FFFFFF;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("✓ 确定设定")
        ok_btn.setObjectName("PrimaryButton")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setFixedHeight(36)
        ok_btn.setStyleSheet("""
            QPushButton {
                background: #38BDF8;
                color: #000000;
                font-weight: 800;
                border-radius: 7px;
                padding: 6px 22px;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover {
                background: #7DD3FC;
            }
        """)
        ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)
        outer.addWidget(container)

    def _on_ok(self):
        self._selected_value = self.spin.value()
        self.accept()

    def value(self) -> int:
        return self._selected_value

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if getattr(self, "_drag_pos", None) and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    @classmethod
    def get_interval(cls, parent=None, title="自定义提醒间隔", prompt="请输入提醒间隔 (分钟):",
                     default_val=45, min_val=1, max_val=720) -> tuple[int, bool]:
        dlg = cls(title=title, prompt=prompt, initial_value=default_val,
                  min_val=min_val, max_val=max_val, parent=parent)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        res = dlg.exec()
        if res == QDialog.DialogCode.Accepted:
            return dlg.value(), True
        return default_val, False
