from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QComboBox, QPushButton, QFrame, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from storage import storage
from ui.styles import THEME

class SettingsTab(QWidget):
    settings_changed = pyqtSignal()
    reposition_requested = pyqtSignal(str)  # "top_center", "top_left", "top_right", "custom"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header = QLabel("⚙️ 偏好设置")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(header)

        settings = storage.get_settings()

        # 1. Position Card
        pos_card = QFrame()
        pos_card.setObjectName("TaskCard")
        pos_layout = QVBoxLayout(pos_card)
        pos_layout.setContentsMargins(14, 12, 14, 12)
        pos_layout.setSpacing(8)

        pos_title = QLabel("📍 灵动岛位置模式")
        pos_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        pos_layout.addWidget(pos_title)

        pos_row = QHBoxLayout()
        self.pos_combo = QComboBox()
        self.pos_combo.addItem("顶部居中 (经典灵动岛)", "top_center")
        self.pos_combo.addItem("顶部居左", "top_left")
        self.pos_combo.addItem("顶部居右", "top_right")
        self.pos_combo.addItem("自由拖拽位置", "custom")

        cur_mode = settings.get("position_mode", "top_center")
        modes = ["top_center", "top_left", "top_right", "custom"]
        if cur_mode in modes:
            self.pos_combo.setCurrentIndex(modes.index(cur_mode))

        self.pos_combo.currentIndexChanged.connect(self._on_pos_changed)
        pos_row.addWidget(self.pos_combo, 1)
        pos_layout.addLayout(pos_row)

        layout.addWidget(pos_card)

        # 2. General Settings Card
        gen_card = QFrame()
        gen_card.setObjectName("TaskCard")
        gen_layout = QVBoxLayout(gen_card)
        gen_layout.setContentsMargins(14, 12, 14, 12)
        gen_layout.setSpacing(10)

        gen_title = QLabel("🎛️ 交互与提醒")
        gen_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        gen_layout.addWidget(gen_title)

        # Always on top
        self.top_cb = QCheckBox("窗口始终置顶 (Always on Top)")
        self.top_cb.setChecked(settings.get("always_on_top", True))
        self.top_cb.toggled.connect(lambda v: self._update_setting("always_on_top", v))
        gen_layout.addWidget(self.top_cb)

        # Sound
        self.sound_cb = QCheckBox("启用待办到期声音提示 (双音提示音)")
        self.sound_cb.setChecked(settings.get("sound_enabled", True))
        self.sound_cb.toggled.connect(lambda v: self._update_setting("sound_enabled", v))
        gen_layout.addWidget(self.sound_cb)

        # CPU in compact
        self.cpu_cb = QCheckBox("在胶囊栏中显示实时 CPU 监控角标")
        self.cpu_cb.setChecked(settings.get("compact_show_cpu", True))
        self.cpu_cb.toggled.connect(lambda v: self._update_setting("compact_show_cpu", v))
        gen_layout.addWidget(self.cpu_cb)

        # Auto collapse
        self.collapse_cb = QCheckBox("鼠标移出面板自动收起胶囊 (离开 3秒)")
        self.collapse_cb.setChecked(settings.get("auto_collapse", False))
        self.collapse_cb.toggled.connect(lambda v: self._update_setting("auto_collapse", v))
        gen_layout.addWidget(self.collapse_cb)

        # Autostart on boot
        self.autostart_cb = QCheckBox("开机自动启动灵动岛 (后台无黑框静默运行)")
        self.autostart_cb.setChecked(storage.is_autostart_enabled())
        self.autostart_cb.toggled.connect(self._on_autostart_toggled)
        gen_layout.addWidget(self.autostart_cb)

        layout.addWidget(gen_card)

        # 3. Actions & About Card
        about_card = QFrame()
        about_card.setObjectName("TaskCard")
        about_layout = QVBoxLayout(about_card)
        about_layout.setContentsMargins(14, 12, 14, 12)
        about_layout.setSpacing(10)

        about_title = QLabel("💡 快捷技巧与操作")
        about_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        about_layout.addWidget(about_title)

        tips_lbl = QLabel(
            "• 点击顶部胶囊可展开灵动中心\n"
            "• 按 ESC 键或点击右上角收起按钮即可收起\n"
            "• 系统托盘常驻，可随时右键唤出或退出"
        )
        tips_lbl.setStyleSheet(f"font-size: 11px; color: {THEME['text_secondary']}; line-height: 1.4;")
        about_layout.addWidget(tips_lbl)

        btn_row = QHBoxLayout()
        self.reset_data_btn = QPushButton("恢复初始示例数据")
        self.reset_data_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_data_btn.clicked.connect(self._reset_sample_data)
        btn_row.addWidget(self.reset_data_btn)

        self.quit_btn = QPushButton("退出灵动岛")
        self.quit_btn.setObjectName("DangerButton")
        self.quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quit_btn.clicked.connect(QApplication.instance().quit)
        btn_row.addWidget(self.quit_btn)

        about_layout.addLayout(btn_row)
        layout.addWidget(about_card)

        layout.addStretch()

    def _on_pos_changed(self):
        mode = self.pos_combo.currentData()
        storage.update_setting("position_mode", mode)
        self.reposition_requested.emit(mode)

    def _update_setting(self, key, value):
        storage.update_setting(key, value)
        self.settings_changed.emit()

    def _on_autostart_toggled(self, checked: bool):
        ok = storage.set_autostart(checked)
        if not ok:
            self.autostart_cb.blockSignals(True)
            self.autostart_cb.setChecked(not checked)
            self.autostart_cb.blockSignals(False)
            QMessageBox.warning(self, "设置失败", "无法修改系统开机启动注册表，请检查权限。")
        else:
            self.settings_changed.emit()

    def _reset_sample_data(self):
        storage._ensure_files()
        self.settings_changed.emit()
        QMessageBox.information(self, "提示", "已重置示例代办数据！")
