# ui/alert_island.py - Dynamic Island Alert Banner Supporting Todos and Recurring Alarms
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from storage import storage, get_habit_presentation
from ui.styles import THEME
from ui.components.icons import make_close_icon


class AlertIsland(QWidget):
    action_completed = pyqtSignal(str)   # item_id
    action_snoozed = pyqtSignal(str)     # item_id
    action_dismissed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_payload = None

        self._init_ui()

        # Auto collapse timer (60 seconds): if user doesn't interact within 1 min, auto-snooze 2 mins and collapse
        self.auto_dismiss_timer = QTimer(self)
        self.auto_dismiss_timer.setSingleShot(True)
        self.auto_dismiss_timer.setInterval(60000)
        self.auto_dismiss_timer.timeout.connect(self._on_auto_dismiss)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        # Icon Label
        self.bell_label = QLabel("🔔")
        self.bell_label.setStyleSheet("font-size: 24px; background: transparent;")
        layout.addWidget(self.bell_label)

        # Center Info
        center_layout = QVBoxLayout()
        center_layout.setSpacing(2)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.tag_label = QLabel("⏰ 到期提醒")
        self.tag_label.setStyleSheet(f"""
            color: {THEME['accent_orange']};
            font-size: 11px;
            font-weight: 700;
            background: transparent;
        """)
        center_layout.addWidget(self.tag_label)

        self.title_label = QLabel("提醒内容...")
        self.title_label.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 13px;
            font-weight: 600;
            background: transparent;
        """)
        center_layout.addWidget(self.title_label)
        layout.addLayout(center_layout, 1)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self.done_btn = QPushButton("✓ 完成")
        self.done_btn.setObjectName("SuccessButton")
        self.done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.done_btn.clicked.connect(self._on_done)
        btn_layout.addWidget(self.done_btn)

        self.snooze_btn = QPushButton("稍后 5分")
        self.snooze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.snooze_btn.clicked.connect(self._on_snooze)
        btn_layout.addWidget(self.snooze_btn)

        self.close_btn = QPushButton()
        self.close_btn.setObjectName("IconButton")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setIcon(make_close_icon(16))
        self.close_btn.setIconSize(QSize(16, 16))
        self.close_btn.setToolTip("忽略此提醒")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self._on_close)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def trigger_alert(self, payload: dict):
        self.current_payload = payload
        item_type = payload.get("type", "todo")
        title = payload.get("title", "")
        time_str = payload.get("time", "")

        if len(title) > 20:
            title = title[:19] + "..."

        if item_type == "habit":
            habit_info = get_habit_presentation(payload.get("habit") or payload)
            icon = habit_info["icon"]
            action_txt = habit_info["action_text"]
            theme_color = habit_info["color"]
            self.bell_label.setText(icon)
            self.tag_label.setText(f"{icon} 习惯提醒 · {title}")
            self.tag_label.setStyleSheet(f"color: {theme_color}; font-size: 11px; font-weight: 700; background: transparent;")
            self.done_btn.setText(f"{icon} {action_txt}")
            self.snooze_btn.setText("稍后 15分")
        elif item_type == "alarm":
            self.bell_label.setText("⏰")
            self.tag_label.setText("⏰ 周期闹钟响铃")
            self.tag_label.setStyleSheet("color: #34D399; font-size: 11px; font-weight: 700; background: transparent;")
            self.done_btn.setText("🎯 打卡完成")
            self.snooze_btn.setText("稍后 5分")
        else:
            self.bell_label.setText("🔔")
            self.tag_label.setText("📋 待办到期提醒")
            self.tag_label.setStyleSheet(f"color: {THEME['accent_orange']}; font-size: 11px; font-weight: 700; background: transparent;")
            self.done_btn.setText("✓ 完成")
            self.snooze_btn.setText("稍后 5分")

        suffix = f" ({time_str})" if time_str else ""
        self.title_label.setText(f"{title}{suffix}")
        self.auto_dismiss_timer.start()

    def _on_done(self):
        self.auto_dismiss_timer.stop()
        if not self.current_payload:
            return

        item_type = self.current_payload.get("type", "todo")
        item_id = self.current_payload.get("id")

        if item_type == "habit":
            storage.checkin_habit(item_id)
        elif item_type == "alarm":
            storage.checkin_alarm(item_id)
        else:
            storage.toggle_todo(item_id)

        self.action_completed.emit(item_id)

    def _on_snooze(self):
        self.auto_dismiss_timer.stop()
        if not self.current_payload:
            return

        item_type = self.current_payload.get("type", "todo")
        item_id = self.current_payload.get("id")

        if item_type == "habit":
            storage.snooze_habit(item_id, minutes=15)
        elif item_type == "alarm":
            storage.snooze_alarm(item_id, minutes=5)
        else:
            storage.snooze_todo(item_id, minutes=5)

        self.action_snoozed.emit(item_id)

    def _on_close(self):
        self.auto_dismiss_timer.stop()
        self.action_dismissed.emit()

    def _on_auto_dismiss(self):
        """Auto dismiss after 1 minute of inactivity: snooze for 2 minutes and collapse."""
        if self.current_payload:
            item_type = self.current_payload.get("type", "todo")
            item_id = self.current_payload.get("id")
            if item_type == "habit":
                storage.snooze_habit(item_id, minutes=2)
            elif item_type == "alarm":
                storage.snooze_alarm(item_id, minutes=2)
            else:
                storage.snooze_todo(item_id, minutes=2)
            self.action_snoozed.emit(item_id)
        else:
            self.action_dismissed.emit()
