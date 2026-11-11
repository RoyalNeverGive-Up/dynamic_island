from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QComboBox, QPushButton, QFrame, QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QMouseEvent
from config import PRIORITY_CONFIG, CATEGORIES
from ui.styles import THEME, MAIN_STYLE
from ui.components.friendly_time_picker import FriendlyTimePicker
from ui.components.icons import make_close_icon

class TodoEditDialog(QDialog):
    def __init__(self, todo: dict, parent=None):
        super().__init__(parent)
        self.todo = todo
        self.updated_data = None
        self.setWindowTitle("编辑待办事项")
        self.setFixedSize(500, 620)
        self.setStyleSheet(MAIN_STYLE)

        # WindowStaysOnTopHint ensures dialog stays in front of IslandWindow on Windows
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
        container.setStyleSheet(f"""
            background-color: #161824;
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 18px;
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 6)
        container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(18, 16, 18, 16)
        container_layout.setSpacing(10)

        # Title Bar
        header = QHBoxLayout()
        title_label = QLabel("✏️ 编辑待办事项")
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        header.addWidget(title_label)

        close_btn = QPushButton()
        close_btn.setObjectName("IconButton")
        close_btn.setFixedSize(28, 28)
        close_btn.setIcon(make_close_icon(16))
        close_btn.setIconSize(QSize(16, 16))
        close_btn.setToolTip("关闭窗口 (ESC)")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        container_layout.addLayout(header)

        # Title Input
        lbl_t = QLabel("待办标题:")
        lbl_t.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        container_layout.addWidget(lbl_t)

        self.title_input = QLineEdit(self.todo.get("title", ""))
        self.title_input.setPlaceholderText("待办内容...")
        self.title_input.setStyleSheet("font-size: 13px; color: #FFFFFF; font-weight: 500;")
        container_layout.addWidget(self.title_input)

        # Priority & Category
        meta_layout = QHBoxLayout()

        meta_layout.addWidget(QLabel("优先级:"))
        self.priority_combo = QComboBox()
        self.priority_combo.addItem("🔴 紧急", "high")
        self.priority_combo.addItem("🟡 重要", "medium")
        self.priority_combo.addItem("🟢 普通", "low")
        cur_prio = self.todo.get("priority", "medium")
        idx = {"high": 0, "medium": 1, "low": 2}.get(cur_prio, 1)
        self.priority_combo.setCurrentIndex(idx)
        meta_layout.addWidget(self.priority_combo)

        meta_layout.addWidget(QLabel("分类:"))
        self.category_combo = QComboBox()
        for cat in CATEGORIES:
            self.category_combo.addItem(cat, cat)
        cur_cat = self.todo.get("category", "工作")
        if cur_cat in CATEGORIES:
            self.category_combo.setCurrentIndex(CATEGORIES.index(cur_cat))
        meta_layout.addWidget(self.category_combo)

        container_layout.addLayout(meta_layout)

        # Friendly Time Picker Component
        self.time_picker = FriendlyTimePicker(self)
        self.time_picker.set_data(
            due_time=self.todo.get("due_time", ""),
            repeat_type=self.todo.get("repeat_type", "none"),
            repeat_days=self.todo.get("repeat_days", []),
            repeat_time=self.todo.get("repeat_time", "")
        )
        container_layout.addWidget(self.time_picker)

        # Description / Note
        container_layout.addWidget(QLabel("备注 / 详情:"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("可选备注信息...")
        self.desc_input.setPlainText(self.todo.get("description", ""))
        self.desc_input.setMaximumHeight(60)
        container_layout.addWidget(self.desc_input)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存修改")
        save_btn.setObjectName("PrimaryButton")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        container_layout.addLayout(btn_layout)
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

    def _save(self):
        title = self.title_input.text().strip()
        if not title:
            self.title_input.setFocus()
            return

        due_str = self.time_picker.get_due_time()
        repeat_type = self.time_picker.get_repeat_type()
        repeat_days = self.time_picker.get_repeat_days()
        repeat_time = self.time_picker.get_repeat_time()
        reminder_enabled = self.time_picker.is_reminder_enabled()

        self.updated_data = {
            "title": title,
            "description": self.desc_input.toPlainText().strip(),
            "priority": self.priority_combo.currentData(),
            "category": self.category_combo.currentData(),
            "repeat_type": repeat_type,
            "repeat_days": repeat_days,
            "repeat_time": repeat_time,
            "due_time": due_str,
            "reminder_enabled": reminder_enabled,
            "reminded": False if due_str != self.todo.get("due_time") else self.todo.get("reminded", False),
        }
        self.accept()
