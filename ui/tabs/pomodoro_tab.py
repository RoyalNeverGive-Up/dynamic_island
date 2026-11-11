from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from pomodoro_service import PomodoroService
from ui.styles import THEME

class PomodoroTab(QWidget):
    def __init__(self, pomodoro_service: PomodoroService, parent=None):
        super().__init__(parent)
        self.service = pomodoro_service
        self._init_ui()
        self._connect_service()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Mode Selector Buttons
        mode_box = QHBoxLayout()
        mode_box.setSpacing(8)

        self.btn_work = QPushButton("🍅 专注 (25分)")
        self.btn_short = QPushButton("☕ 短休 (5分)")
        self.btn_long = QPushButton("🌴 长休 (15分)")

        for btn in (self.btn_work, self.btn_short, self.btn_long):
            btn.setObjectName("NavTabButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            mode_box.addWidget(btn)

        self.btn_work.clicked.connect(lambda: self.service.set_mode(PomodoroService.MODE_WORK))
        self.btn_short.clicked.connect(lambda: self.service.set_mode(PomodoroService.MODE_SHORT_BREAK))
        self.btn_long.clicked.connect(lambda: self.service.set_mode(PomodoroService.MODE_LONG_BREAK))

        layout.addLayout(mode_box)

        # 2. Main Timer Display Card
        timer_card = QFrame()
        timer_card.setObjectName("TaskCard")
        card_layout = QVBoxLayout(timer_card)
        card_layout.setContentsMargins(24, 28, 24, 28)
        card_layout.setSpacing(10)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.mode_label = QLabel(self.service.current_mode)
        self.mode_label.setStyleSheet(f"""
            color: {THEME['accent_orange']};
            font-size: 13px;
            font-weight: 600;
            background: transparent;
        """)
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.mode_label)

        self.time_label = QLabel("25:00")
        self.time_label.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 54px;
            font-weight: bold;
            font-family: 'Consolas', 'Segoe UI', monospace;
            background: transparent;
        """)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.time_label)

        # Smooth progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {THEME['accent_orange']};
                border-radius: 3px;
            }}
        """)
        card_layout.addWidget(self.progress_bar)

        layout.addWidget(timer_card)

        # 3. Control Buttons
        ctrl_box = QHBoxLayout()
        ctrl_box.setSpacing(12)
        ctrl_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.toggle_btn = QPushButton("▶ 开始专注")
        self.toggle_btn.setObjectName("PrimaryButton")
        self.toggle_btn.setFixedSize(140, 38)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.service.toggle)
        ctrl_box.addWidget(self.toggle_btn)

        self.reset_btn = QPushButton("↺ 重置")
        self.reset_btn.setFixedSize(90, 38)
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self.service.reset)
        ctrl_box.addWidget(self.reset_btn)

        layout.addLayout(ctrl_box)

        # 4. Today's Pomodoro Stats
        self.stats_label = QLabel("今日专注: 0 个番茄钟 (0 分钟)")
        self.stats_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stats_label)

        layout.addStretch()

        self._update_mode_buttons()

    def _connect_service(self):
        self.service.tick.connect(self._on_tick)
        self.service.state_changed.connect(self._on_state_changed)
        self.service.completed.connect(self._on_completed)

    def _on_tick(self, remaining: int, total: int, mode_name: str):
        mins = remaining // 60
        secs = remaining % 60
        self.time_label.setText(f"{mins:02d}:{secs:02d}")
        self.mode_label.setText(mode_name)

        if total > 0:
            pct = int((remaining / total) * 100)
            self.progress_bar.setValue(pct)

        self._update_mode_buttons()

    def _on_state_changed(self, is_running: bool):
        if is_running:
            self.toggle_btn.setText("⏸ 暂停")
            self.toggle_btn.setStyleSheet(f"""
                background-color: {THEME['accent_orange']};
                border-color: {THEME['accent_orange']};
                color: #FFFFFF;
                font-weight: 600;
            """)
        else:
            self.toggle_btn.setText("▶ 开始" if self.service.remaining_seconds == self.service.total_seconds else "▶ 继续")
            self.toggle_btn.setStyleSheet("")

    def _on_completed(self, mode_name: str):
        count = self.service.completed_count
        mins = count * 25
        self.stats_label.setText(f"今日专注: {count} 个番茄钟 ({mins} 分钟) 🔥")

    def _update_mode_buttons(self):
        cur = self.service.current_mode
        self.btn_work.setProperty("active", "true" if cur == PomodoroService.MODE_WORK else "false")
        self.btn_short.setProperty("active", "true" if cur == PomodoroService.MODE_SHORT_BREAK else "false")
        self.btn_long.setProperty("active", "true" if cur == PomodoroService.MODE_LONG_BREAK else "false")

        for b in (self.btn_work, self.btn_short, self.btn_long):
            b.style().unpolish(b)
            b.style().polish(b)
