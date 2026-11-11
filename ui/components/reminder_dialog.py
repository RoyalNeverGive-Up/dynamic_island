# ui/components/reminder_dialog.py - Floating Notification for Todos, Alarms, and Habits
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QMouseEvent
from config import PRIORITY_CONFIG
from storage import storage, format_alarm_repeat
from ui.styles import THEME, MAIN_STYLE
from ui.components.icons import make_close_icon


class ReminderDialog(QDialog):
    action_completed = pyqtSignal(str)   # item_id
    action_snoozed = pyqtSignal(str)     # item_id
    action_dismissed = pyqtSignal()

    def __init__(self, payload: dict, parent=None):
        super().__init__(parent)
        self.payload = payload
        self.item_type = payload.get("type", "todo")
        self.is_alarm = self.item_type == "alarm"
        self.is_habit = self.item_type == "habit"
        self.item_data = payload.get("habit") or payload.get("alarm") or payload.get("todo") or payload

        if self.is_habit:
            self.setWindowTitle("健康习惯提醒")
            self.setFixedSize(450, 330)
        elif self.is_alarm:
            self.setWindowTitle("闹钟响铃")
            self.setFixedSize(430, 300)
        else:
            self.setWindowTitle("待办到期提醒")
            self.setFixedSize(430, 300)

        self.setStyleSheet(MAIN_STYLE)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._init_ui()

        # Position on primary screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = max(60, (screen.height() - self.height()) // 3)
        self.move(x, y)

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 12, 12, 12)

        if self.is_habit:
            theme_color = "#38BDF8"
            glow_color = QColor(56, 189, 248, 120)
        elif self.is_alarm:
            theme_color = "#34D399"
            glow_color = QColor(52, 211, 153, 110)
        else:
            theme_color = THEME['accent_orange']
            glow_color = QColor(255, 159, 10, 100)

        # Main glowing container
        container = QFrame(self)
        container.setObjectName("IslandContainer")
        container.setStyleSheet(f"""
            background-color: #141724;
            border: 1.5px solid {theme_color};
            border-radius: 18px;
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(glow_color)
        shadow.setOffset(0, 6)
        container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # 1. Header Bar
        header = QHBoxLayout()
        header.setSpacing(8)

        icon_char = "💧" if self.is_habit else ("⏰" if self.is_alarm else "🔔")
        icon_lbl = QLabel(icon_char)
        icon_lbl.setStyleSheet("font-size: 20px;")
        header.addWidget(icon_lbl)

        if self.is_habit:
            title_text = "循环习惯 · 定时喝水打卡"
        elif self.is_alarm:
            title_text = "周期闹钟响铃 · 灵动打卡"
        else:
            title_text = "待办到期提醒 · 灵动通知"

        alert_title = QLabel(title_text)
        alert_title.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 800;
            color: {theme_color};
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

        # 2. Details Card
        detail_card = QFrame()
        detail_card.setStyleSheet("""
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 4px;
        """)
        card_layout = QVBoxLayout(detail_card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(6)

        # Badges row
        badge_row = QHBoxLayout()
        badge_row.setSpacing(6)

        if self.is_habit:
            cnt = self.item_data.get("today_count", 0)
            tgt = self.item_data.get("target_count", 8)
            h_badge = QLabel(f"💧 今日已完成: {cnt} / {tgt} 杯")
            h_badge.setStyleSheet("color: #38BDF8; background: rgba(56, 189, 248, 0.15); font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 5px;")
            badge_row.addWidget(h_badge)

            time_range = f"活跃时段: {self.item_data.get('start_time', '09:00')} ~ {self.item_data.get('end_time', '18:00')}"
            range_badge = QLabel(time_range)
            range_badge.setStyleSheet("color: #CBD5E1; background: rgba(255, 255, 255, 0.08); font-size: 11px; padding: 2px 6px; border-radius: 5px;")
            badge_row.addWidget(range_badge)

        elif self.is_alarm:
            rep_text = format_alarm_repeat(self.item_data)
            rep_badge = QLabel(rep_text)
            rep_badge.setStyleSheet("color: #A7F3D0; background: rgba(16, 185, 129, 0.2); font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 5px;")
            badge_row.addWidget(rep_badge)

            count = self.item_data.get("checkin_count", 0)
            count_badge = QLabel(f"🎯 累计打卡 {count} 次")
            count_badge.setStyleSheet("color: #F472B6; background: rgba(244, 114, 182, 0.15); font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 5px;")
            badge_row.addWidget(count_badge)

        else:
            cat = self.item_data.get("category", "默认")
            cat_badge = QLabel(cat)
            cat_badge.setStyleSheet("color: #CBD5E1; background: rgba(255, 255, 255, 0.08); font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 5px;")
            badge_row.addWidget(cat_badge)

            prio = self.item_data.get("priority", "medium")
            prio_info = PRIORITY_CONFIG.get(prio, PRIORITY_CONFIG["medium"])
            prio_badge = QLabel(prio_info["label"])
            prio_badge.setStyleSheet(f"color: {prio_info['color']}; background-color: {prio_info['bg']}; font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 5px;")
            badge_row.addWidget(prio_badge)

        badge_row.addStretch()
        card_layout.addLayout(badge_row)

        # Title
        title_lbl = QLabel(self.item_data.get("title", ""))
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #FFFFFF; line-height: 1.3;")
        card_layout.addWidget(title_lbl)

        layout.addWidget(detail_card)

        # 3. Actions Row
        if self.is_habit:
            # Custom prompt: let user choose when to trigger next
            choice_lbl = QLabel("请选择下一次提醒时间 (同时记录喝水 +1 杯):")
            choice_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #38BDF8; margin-top: 2px;")
            layout.addWidget(choice_lbl)

            btn_grid = QHBoxLayout()
            btn_grid.setSpacing(6)

            intervals = [
                ("30分后", 30),
                ("45分后", 45),
                ("60分后", 60),
                ("90分后", 90),
            ]
            for lbl, mins in intervals:
                btn = QPushButton(f"💧 {lbl}")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(56, 189, 248, 0.2);
                        color: #38BDF8;
                        border: 1px solid rgba(56, 189, 248, 0.4);
                        border-radius: 6px;
                        padding: 6px 4px;
                        font-size: 11px;
                        font-weight: 700;
                    }
                    QPushButton:hover {
                        background: #38BDF8;
                        color: #000000;
                    }
                """)
                btn.clicked.connect(lambda chk, m=mins: self._on_habit_checked(m))
                btn_grid.addWidget(btn)

            layout.addLayout(btn_grid)

            sub_row = QHBoxLayout()
            sub_row.addStretch()
            dismiss_h_btn = QPushButton("稍后/本次跳过")
            dismiss_h_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            dismiss_h_btn.setStyleSheet("color: #94A3B8; font-size: 11px; background: transparent; border: none;")
            dismiss_h_btn.clicked.connect(self._on_dismiss)
            sub_row.addWidget(dismiss_h_btn)
            layout.addLayout(sub_row)

        else:
            # Normal alarm or todo buttons
            btn_row = QHBoxLayout()
            btn_row.setSpacing(8)

            if self.is_alarm:
                self.done_btn = QPushButton("🎯 完成打卡")
            else:
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
        if getattr(self, "_drag_pos", None) and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def _on_habit_checked(self, minutes: int):
        item_id = self.item_data["id"]
        storage.checkin_habit(item_id, next_interval_minutes=minutes)
        self.action_completed.emit(item_id)
        self.accept()

    def _on_done(self):
        item_id = self.item_data["id"]
        if self.is_alarm:
            storage.checkin_alarm(item_id)
        else:
            storage.toggle_todo(item_id)
        self.action_completed.emit(item_id)
        self.accept()

    def _on_snooze(self):
        item_id = self.item_data["id"]
        if self.is_alarm:
            storage.snooze_alarm(item_id, minutes=5)
        else:
            storage.snooze_todo(item_id, minutes=5)
        self.action_snoozed.emit(item_id)
        self.accept()

    def _on_dismiss(self):
        self.action_dismissed.emit()
        self.reject()
