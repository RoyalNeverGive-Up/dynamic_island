from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QMouseEvent
from config import PRIORITY_CONFIG
from storage import storage, format_repeat_display
from ui.styles import THEME, MAIN_STYLE
from ui.components.icons import make_close_icon

class ReminderDialog(QDialog):
    action_completed = pyqtSignal(str)   # todo_id
    action_snoozed = pyqtSignal(str)     # todo_id
    action_dismissed = pyqtSignal()

    def __init__(self, todo: dict, parent=None):
        super().__init__(parent)
        self.todo = todo
        self.setWindowTitle("待办到期提醒")
        self.setFixedSize(420, 290)
        self.setStyleSheet(MAIN_STYLE)

        # Always on top so user working in other windows sees it immediately!
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._init_ui()

        # Position nicely in the top-center or center of primary screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = max(60, (screen.height() - self.height()) // 3)
        self.move(x, y)

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 12, 12, 12)

        # Main glowing alert container
        container = QFrame(self)
        container.setObjectName("IslandContainer")
        container.setStyleSheet(f"""
            background-color: #141724;
            border: 1.5px solid {THEME['accent_orange']};
            border-radius: 18px;
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(255, 159, 10, 100))
        shadow.setOffset(0, 6)
        container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # 1. Header Bar: Bell + Title + Close Button
        header = QHBoxLayout()
        header.setSpacing(8)

        bell_lbl = QLabel("🔔")
        bell_lbl.setStyleSheet("font-size: 20px;")
        header.addWidget(bell_lbl)

        alert_title = QLabel("待办到期提醒 · 灵动通知")
        alert_title.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 800;
            color: {THEME['accent_orange']};
        """)
        header.addWidget(alert_title)

        header.addStretch()

        close_btn = QPushButton()
        close_btn.setObjectName("IconButton")
        close_btn.setFixedSize(28, 28)
        close_btn.setIcon(make_close_icon(16))
        close_btn.setIconSize(QSize(16, 16))
        close_btn.setToolTip("关闭通知")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self._on_dismiss)
        header.addWidget(close_btn)

        layout.addLayout(header)

        # 2. Task Details Card
        task_card = QFrame()
        task_card.setStyleSheet(f"""
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 4px;
        """)
        card_layout = QVBoxLayout(task_card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(6)

        # Badges row: Priority + Category + Repeat
        badge_row = QHBoxLayout()
        badge_row.setSpacing(6)

        prio = self.todo.get("priority", "medium")
        prio_info = PRIORITY_CONFIG.get(prio, PRIORITY_CONFIG["medium"])
        prio_badge = QLabel(prio_info["label"])
        prio_badge.setStyleSheet(f"""
            color: {prio_info['color']};
            background-color: {prio_info['bg']};
            font-size: 11px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 6px;
        """)
        badge_row.addWidget(prio_badge)

        cat = self.todo.get("category", "默认")
        cat_badge = QLabel(cat)
        cat_badge.setStyleSheet("""
            color: #CBD5E1;
            background-color: rgba(255, 255, 255, 0.08);
            font-size: 11px;
            font-weight: 600;
            padding: 2px 7px;
            border-radius: 6px;
        """)
        badge_row.addWidget(cat_badge)

        rep_desc = format_repeat_display(self.todo)
        if rep_desc:
            rep_badge = QLabel(rep_desc)
            rep_badge.setStyleSheet("""
                color: #34D399;
                background-color: rgba(52, 211, 153, 0.18);
                border: 1px solid rgba(52, 211, 153, 0.35);
                font-size: 11px;
                font-weight: 700;
                padding: 2px 7px;
                border-radius: 6px;
            """)
            badge_row.addWidget(rep_badge)

        badge_row.addStretch()
        card_layout.addLayout(badge_row)

        # Task Title (Large, bold, high contrast, word wrap)
        self.title_lbl = QLabel(self.todo.get("title", ""))
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setStyleSheet("""
            font-size: 16px;
            font-weight: 800;
            color: #FFFFFF;
            line-height: 1.3;
        """)
        card_layout.addWidget(self.title_lbl)

        # Due time & description
        due = self.todo.get("due_time", "")
        if due:
            due_lbl = QLabel(f"⏰ 截止时刻: <span style='color: #38BDF8; font-weight: bold;'>{due}</span>")
            due_lbl.setTextFormat(Qt.TextFormat.RichText)
            due_lbl.setStyleSheet("font-size: 12px; color: #94A3B8;")
            card_layout.addWidget(due_lbl)

        desc = self.todo.get("description", "")
        if desc:
            desc_lbl = QLabel(f"📝 备注: {desc}")
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet("font-size: 12px; color: #CBD5E1;")
            card_layout.addWidget(desc_lbl)

        layout.addWidget(task_card)

        # 3. Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.done_btn = QPushButton("✓ 标记完成")
        self.done_btn.setObjectName("SuccessButton")
        self.done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.done_btn.setFixedHeight(34)
        self.done_btn.clicked.connect(self._on_done)
        btn_row.addWidget(self.done_btn)

        self.snooze_btn = QPushButton("⏰ 稍后 5分钟")
        self.snooze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.snooze_btn.setFixedHeight(34)
        self.snooze_btn.clicked.connect(self._on_snooze)
        btn_row.addWidget(self.snooze_btn)

        self.dismiss_btn = QPushButton("知道了")
        self.dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dismiss_btn.setFixedHeight(34)
        self.dismiss_btn.clicked.connect(self._on_dismiss)
        btn_row.addWidget(self.dismiss_btn)

        layout.addLayout(btn_row)
        outer_layout.addWidget(container)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if hasattr(self, "_drag_pos") and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def _on_done(self):
        todo_id = self.todo["id"]
        storage.toggle_todo(todo_id)
        self.action_completed.emit(todo_id)
        self.accept()

    def _on_snooze(self):
        todo_id = self.todo["id"]
        storage.snooze_todo(todo_id, minutes=5)
        self.action_snoozed.emit(todo_id)
        self.accept()

    def _on_dismiss(self):
        self.action_dismissed.emit()
        self.reject()
