from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from storage import storage
from ui.styles import THEME

class MemoTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

        # Save debounce timer
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(500)
        self.save_timer.timeout.connect(self._save_content)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Header
        top_row = QHBoxLayout()
        title_lbl = QLabel("📝 灵感便签")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
        top_row.addWidget(title_lbl)

        self.save_status = QLabel("已保存 ✓")
        self.save_status.setStyleSheet(f"font-size: 11px; color: {THEME['text_muted']};")
        top_row.addWidget(self.save_status)

        top_row.addStretch()

        self.copy_btn = QPushButton("复制内容")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy_all)
        top_row.addWidget(self.copy_btn)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.setObjectName("DangerButton")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear_all)
        top_row.addWidget(self.clear_btn)

        layout.addLayout(top_row)

        # Text Editor
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("随手记录会议纪要、临时想法、电话号码或代码片段...")
        self.text_edit.setPlainText(storage.get_memo())
        self.text_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.text_edit, 1)

    def _on_text_changed(self):
        self.save_status.setText("保存中...")
        self.save_timer.start()

    def _save_content(self):
        storage.save_memo(self.text_edit.toPlainText())
        self.save_status.setText("已保存 ✓")

    def _copy_all(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_edit.toPlainText())
        self.save_status.setText("已复制到剪贴板！📋")
        QTimer.singleShot(2000, lambda: self.save_status.setText("已保存 ✓"))

    def _clear_all(self):
        self.text_edit.clear()
        storage.save_memo("")
        self.save_status.setText("已清空")
