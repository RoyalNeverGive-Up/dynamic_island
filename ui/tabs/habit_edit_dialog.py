# ui/tabs/habit_edit_dialog.py - Modal Dialog for Habit / Interval Reminders
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFrame, QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QMouseEvent
from ui.styles import THEME, MAIN_STYLE
from ui.components.icons import make_close_icon


class HabitEditDialog(QDialog):
    def __init__(self, habit: dict, parent=None):
        super().__init__(parent)
        self.habit = habit
        self.updated_data = None
        self.setWindowTitle("编辑循环提醒")
        self.setFixedSize(450, 480)
        self.setStyleSheet(MAIN_STYLE)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._init_ui()

        # Center on primary screen
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

        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # 1. Header
        header = QHBoxLayout()
        title_lbl = QLabel("💧 编辑循环习惯与提醒")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #FFFFFF;")
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
        layout.addLayout(header)

        # 2. Title
        layout.addWidget(QLabel("提醒名称:"))
        self.title_input = QLineEdit(self.habit.get("title", ""))
        self.title_input.setPlaceholderText("例如: 定时喝水打卡 💧、起身活动 🚶...")
        layout.addWidget(self.title_input)

        # 3. Time Range (Start Time ~ End Time)
        layout.addWidget(QLabel("提醒活跃时段 (开始时间 ~ 结束时间):"))
        time_range_row = QHBoxLayout()
        time_range_row.setSpacing(8)

        self.start_combo = QComboBox()
        for h in range(6, 24):
            self.start_combo.addItem(f"{h:02d}:00", f"{h:02d}:00")
            self.start_combo.addItem(f"{h:02d}:30", f"{h:02d}:30")
        cur_start = self.habit.get("start_time", "09:00")
        s_idx = self.start_combo.findData(cur_start)
        if s_idx >= 0:
            self.start_combo.setCurrentIndex(s_idx)
        time_range_row.addWidget(self.start_combo, 1)

        time_range_row.addWidget(QLabel("至"))

        self.end_combo = QComboBox()
        for h in range(7, 24):
            self.end_combo.addItem(f"{h:02d}:00", f"{h:02d}:00")
            self.end_combo.addItem(f"{h:02d}:30", f"{h:02d}:30")
        cur_end = self.habit.get("end_time", "18:00")
        e_idx = self.end_combo.findData(cur_end)
        if e_idx >= 0:
            self.end_combo.setCurrentIndex(e_idx)
        time_range_row.addWidget(self.end_combo, 1)

        layout.addLayout(time_range_row)

        # 4. Default Interval & Target Count
        layout.addWidget(QLabel("默认提醒间隔与每日目标:"))
        opts_row = QHBoxLayout()
        opts_row.setSpacing(10)

        # Interval combo
        self.interval_combo = QComboBox()
        intervals = [(20, "每 20 分钟"), (30, "每 30 分钟"), (45, "每 45 分钟"),
                     (60, "每 1 小时"), (90, "每 1.5 小时"), (120, "每 2 小时")]
        for m, lbl in intervals:
            self.interval_combo.addItem(lbl, m)
        cur_int = self.habit.get("default_interval", 45)
        for i in range(self.interval_combo.count()):
            if self.interval_combo.itemData(i) == cur_int:
                self.interval_combo.setCurrentIndex(i)
                break
        opts_row.addWidget(self.interval_combo, 1)

        # Target count combo
        self.target_combo = QComboBox()
        for c in range(2, 21):
            self.target_combo.addItem(f"目标 {c} 次/天", c)
        cur_target = self.habit.get("target_count", 8)
        t_idx = self.target_combo.findData(cur_target)
        if t_idx >= 0:
            self.target_combo.setCurrentIndex(t_idx)
        opts_row.addWidget(self.target_combo, 1)

        layout.addLayout(opts_row)

        # Notice
        tip = QLabel("💡 提示: 提醒触发弹窗时，您也可以根据当时的状态自由选择下一次多久后再次提醒。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #94A3B8; font-size: 11px; line-height: 1.4; padding: 4px;")
        layout.addWidget(tip)

        # 5. Buttons
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

    def _on_save(self):
        title = self.title_input.text().strip()
        if not title:
            return

        self.updated_data = {
            "title": title,
            "start_time": self.start_combo.currentData(),
            "end_time": self.end_combo.currentData(),
            "default_interval": self.interval_combo.currentData(),
            "target_count": self.target_combo.currentData(),
        }
        self.accept()
