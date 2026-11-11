from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from storage import storage
from ui.styles import THEME
from ui.components.icons import make_close_icon

class AlertIsland(QWidget):
    action_completed = pyqtSignal(str)   # todo_id
    action_snoozed = pyqtSignal(str)     # todo_id
    action_dismissed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_todo = None

        self._init_ui()

        # Auto collapse timer (15 seconds)
        self.auto_dismiss_timer = QTimer(self)
        self.auto_dismiss_timer.setSingleShot(True)
        self.auto_dismiss_timer.setInterval(15000)
        self.auto_dismiss_timer.timeout.connect(self._on_auto_dismiss)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        # Bell Icon
        self.bell_label = QLabel("🔔")
        self.bell_label.setStyleSheet("font-size: 24px; background: transparent;")
        layout.addWidget(self.bell_label)

        # Center Info
        center_layout = QVBoxLayout()
        center_layout.setSpacing(2)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.tag_label = QLabel("⏰ 待办到期提醒")
        self.tag_label.setStyleSheet(f"""
            color: {THEME['accent_orange']};
            font-size: 11px;
            font-weight: 700;
            background: transparent;
        """)
        center_layout.addWidget(self.tag_label)

        self.title_label = QLabel("代办内容...")
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

    def trigger_alert(self, todo: dict):
        self.current_todo = todo
        title = todo.get("title", "")
        if len(title) > 20:
            title = title[:19] + "..."
        due = todo.get("due_time", "").split(" ")[-1]
        self.title_label.setText(f"{title} ({due})")
        self.auto_dismiss_timer.start()

    def _on_done(self):
        self.auto_dismiss_timer.stop()
        if self.current_todo:
            todo_id = self.current_todo["id"]
            storage.toggle_todo(todo_id)
            self.action_completed.emit(todo_id)

    def _on_snooze(self):
        self.auto_dismiss_timer.stop()
        if self.current_todo:
            todo_id = self.current_todo["id"]
            storage.snooze_todo(todo_id, minutes=5)
            self.action_snoozed.emit(todo_id)

    def _on_close(self):
        self.auto_dismiss_timer.stop()
        self.action_dismissed.emit()

    def _on_auto_dismiss(self):
        self.action_dismissed.emit()
