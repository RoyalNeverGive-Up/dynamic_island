# ui/tabs/alarm_edit_dialog.py - Modern Modal Dialog for Editing Recurring Alarms
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QComboBox, QPushButton, QFrame, QGraphicsDropShadowEffect,
    QApplication, QButtonGroup
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QMouseEvent
from config import REPEAT_DAILY, REPEAT_WEEKLY, REPEAT_WORKDAY, WEEKDAY_NAMES
from ui.styles import THEME, MAIN_STYLE
from ui.components.icons import make_close_icon


class AlarmEditDialog(QDialog):
    def __init__(self, alarm: dict, parent=None):
        super().__init__(parent)
        self.alarm = alarm
        self.updated_data = None
        self.setWindowTitle("编辑闹钟与习惯提醒")
        self.setFixedSize(480, 560)
        self.setStyleSheet(MAIN_STYLE)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._init_ui()

        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = max(40, (screen.height() - self.height()) // 2)
        self.move(x, y)

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 12, 12, 12)

        container = QFrame(self)
        container.setObjectName("IslandContainer")
        container.setStyleSheet("""
            background-color: #161824;
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 18px;
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 6)
        container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(18, 16, 18, 16)
        container_layout.setSpacing(12)

        # 1. Header
        header = QHBoxLayout()
        title_lbl = QLabel("⏰ 编辑周期闹钟与习惯")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #FFFFFF;")
        header.addWidget(title_lbl)
        header.addStretch()

        close_btn = QPushButton()
        close_btn.setObjectName("IconButton")
        close_btn.setFixedSize(28, 28)
        close_btn.setIcon(make_close_icon(16))
        close_btn.setIconSize(QSize(16, 16))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        container_layout.addLayout(header)

        # 2. Title Input
        container_layout.addWidget(QLabel("闹钟标题 / 习惯名称:"))
        self.title_input = QLineEdit(self.alarm.get("title", ""))
        self.title_input.setPlaceholderText("例如: 每周一例会、每天运动打卡...")
        container_layout.addWidget(self.title_input)

        # 3. Time Picker (Hours and Minutes)
        container_layout.addWidget(QLabel("响铃时间 (24小时制):"))
        time_row = QHBoxLayout()
        time_row.setSpacing(8)

        time_parts = self.alarm.get("time", "09:30").split(":")
        init_hour = int(time_parts[0]) if len(time_parts) > 0 and time_parts[0].isdigit() else 9
        init_minute = int(time_parts[1]) if len(time_parts) > 1 and time_parts[1].isdigit() else 30

        self.hour_combo = QComboBox()
        for h in range(24):
            self.hour_combo.addItem(f"{h:02d} 时", f"{h:02d}")
        self.hour_combo.setCurrentIndex(init_hour)
        time_row.addWidget(self.hour_combo, 1)

        self.minute_combo = QComboBox()
        for m in range(0, 60, 5):
            self.minute_combo.addItem(f"{m:02d} 分", f"{m:02d}")
        # Select matching or closest minute
        closest_m_idx = min(range(12), key=lambda i: abs(i * 5 - init_minute))
        self.minute_combo.setCurrentIndex(closest_m_idx)
        time_row.addWidget(self.minute_combo, 1)

        container_layout.addLayout(time_row)

        # 4. Repeat Type Pills
        container_layout.addWidget(QLabel("重复周期:"))
        rep_pills = QHBoxLayout()
        rep_pills.setSpacing(8)

        self.btn_daily = QPushButton("每天重复")
        self.btn_workday = QPushButton("工作日 (周一至周五)")
        self.btn_weekly = QPushButton("每周自定义")

        self.repeat_btns = {
            REPEAT_DAILY: self.btn_daily,
            REPEAT_WORKDAY: self.btn_workday,
            REPEAT_WEEKLY: self.btn_weekly,
        }

        current_rep = self.alarm.get("repeat_type", REPEAT_WEEKLY)

        for r_key, btn in self.repeat_btns.items():
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=r_key: self._set_repeat_mode(k))
            rep_pills.addWidget(btn)

        container_layout.addLayout(rep_pills)

        # 5. Weekday Selector for Weekly Mode
        self.days_box = QFrame()
        self.days_box.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 8px; padding: 6px;")
        days_layout = QHBoxLayout(self.days_box)
        days_layout.setContentsMargins(4, 4, 4, 4)
        days_layout.setSpacing(6)

        self.day_buttons = []
        selected_days = self.alarm.get("repeat_days", [1])
        for idx, name in enumerate(WEEKDAY_NAMES, start=1):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setChecked(idx in selected_days)
            btn.clicked.connect(self._update_weekday_style)
            days_layout.addWidget(btn)
            self.day_buttons.append((idx, btn))

        container_layout.addWidget(self.days_box)

        # 6. Description Input
        container_layout.addWidget(QLabel("备注 / 任务说明 (可选):"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("添加详细说明、会议链接或打卡要点...")
        self.desc_input.setPlainText(self.alarm.get("description", ""))
        self.desc_input.setFixedHeight(75)
        container_layout.addWidget(self.desc_input)

        # 7. Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("保存修改")
        save_btn.setObjectName("PrimaryButton")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        container_layout.addLayout(btn_row)
        outer_layout.addWidget(container)

        self._set_repeat_mode(current_rep)

    def _set_repeat_mode(self, mode: str):
        self.current_repeat = mode
        for k, btn in self.repeat_btns.items():
            btn.setChecked(k == mode)
            if k == mode:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #0A84FF;
                        color: #FFFFFF;
                        font-weight: 700;
                        border-radius: 6px;
                        padding: 6px 10px;
                        border: none;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.08);
                        color: #CBD5E1;
                        font-weight: 500;
                        border-radius: 6px;
                        padding: 6px 10px;
                        border: 1px solid rgba(255, 255, 255, 0.12);
                    }
                """)

        self.days_box.setVisible(mode == REPEAT_WEEKLY)
        self._update_weekday_style()

    def _update_weekday_style(self):
        for idx, btn in self.day_buttons:
            if btn.isChecked():
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(56, 189, 248, 0.25);
                        color: #38BDF8;
                        border: 1.5px solid #38BDF8;
                        border-radius: 6px;
                        font-size: 11px;
                        font-weight: 700;
                        padding: 4px 6px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.06);
                        color: #94A3B8;
                        border: 1px solid rgba(255, 255, 255, 0.12);
                        border-radius: 6px;
                        font-size: 11px;
                        padding: 4px 6px;
                    }
                """)

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

    def _on_save(self):
        title = self.title_input.text().strip()
        if not title:
            return

        h = self.hour_combo.currentData()
        m = self.minute_combo.currentData()
        time_str = f"{h}:{m}"

        repeat_type = self.current_repeat
        repeat_days = []
        if repeat_type == REPEAT_WEEKLY:
            repeat_days = [idx for idx, btn in self.day_buttons if btn.isChecked()]
            if not repeat_days:
                repeat_days = [1]
        elif repeat_type == REPEAT_DAILY:
            repeat_days = [1, 2, 3, 4, 5, 6, 7]
        elif repeat_type == REPEAT_WORKDAY:
            repeat_days = [1, 2, 3, 4, 5]

        self.updated_data = {
            "title": title,
            "description": self.desc_input.toPlainText().strip(),
            "time": time_str,
            "repeat_type": repeat_type,
            "repeat_days": repeat_days,
        }
        self.accept()
