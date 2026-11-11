from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from ui.styles import THEME
from ui.components.icons import make_pin_icon, make_collapse_icon
from ui.tabs.todo_tab import TodoTab
from ui.tabs.music_tab import MusicTab
from ui.tabs.pomodoro_tab import PomodoroTab
from ui.tabs.system_tab import SystemTab
from ui.tabs.memo_tab import MemoTab
from ui.tabs.settings_tab import SettingsTab
from pomodoro_service import PomodoroService
from system_monitor import SystemMonitor
from music_service import MusicService

class Dashboard(QWidget):
    collapse_requested = pyqtSignal()
    todos_changed = pyqtSignal()
    reposition_requested = pyqtSignal(str)

    def __init__(self, pomodoro_service: PomodoroService, system_monitor: SystemMonitor, music_service: MusicService, parent=None):
        super().__init__(parent)
        self.pomodoro_service = pomodoro_service
        self.system_monitor = system_monitor
        self.music_service = music_service
        self.is_pinned = False

        self._init_ui()

        # Clock timer for header (1s)
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start()
        self._update_clock()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 14)
        main_layout.setSpacing(10)

        # 1. Top Header with Clear & Prominent Clock
        header = QHBoxLayout()
        header.setSpacing(10)

        # Title & Date/Clock box
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title_lbl = QLabel("灵动中心 · Dynamic Island")
        title_lbl.setStyleSheet("""
            font-size: 15px;
            font-weight: 800;
            color: #FFFFFF;
            background: transparent;
        """)
        title_box.addWidget(title_lbl)

        # Enlarge & brighten header clock
        self.clock_lbl = QLabel("")
        self.clock_lbl.setStyleSheet("""
            font-size: 13px;
            font-weight: 700;
            color: #38BDF8;
            background: transparent;
        """)
        title_box.addWidget(self.clock_lbl)
        header.addLayout(title_box, 1)

        # Pin Button
        self.pin_btn = QPushButton()
        self.pin_btn.setObjectName("IconButton")
        self.pin_btn.setFixedSize(30, 30)
        self.pin_btn.setIcon(make_pin_icon(18, pinned=False))
        self.pin_btn.setIconSize(QSize(18, 18))
        self.pin_btn.setToolTip("固定面板（防止失焦自动收起）")
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.clicked.connect(self._toggle_pin)
        header.addWidget(self.pin_btn)

        # Collapse Button
        self.collapse_btn = QPushButton()
        self.collapse_btn.setObjectName("IconButton")
        self.collapse_btn.setFixedSize(30, 30)
        self.collapse_btn.setIcon(make_collapse_icon(18))
        self.collapse_btn.setIconSize(QSize(18, 18))
        self.collapse_btn.setToolTip("收起灵动岛 (ESC)")
        self.collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_btn.clicked.connect(self.collapse_requested.emit)
        header.addWidget(self.collapse_btn)

        main_layout.addLayout(header)

        # 2. Navigation Tabs Bar
        nav_frame = QFrame()
        nav_frame.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 2px;
        """)
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(3, 3, 3, 3)
        nav_layout.setSpacing(3)

        self.nav_buttons = []
        tabs_info = [
            ("📋 待办", 0),
            ("🎵 音乐", 1),
            ("🍅 专注", 2),
            ("⚡ 监控", 3),
            ("📝 便签", 4),
            ("⚙️ 设置", 5),
        ]

        for text, idx in tabs_info:
            btn = QPushButton(text)
            btn.setObjectName("NavTabButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=idx: self.switch_tab(i))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        main_layout.addWidget(nav_frame)

        # 3. Stacked Pages
        self.stack = QStackedWidget()

        # Tab 0: Todo
        self.todo_tab = TodoTab()
        self.todo_tab.todos_changed.connect(self.todos_changed.emit)
        self.stack.addWidget(self.todo_tab)

        # Tab 1: Music
        self.music_tab = MusicTab(self.music_service)
        self.stack.addWidget(self.music_tab)

        # Tab 2: Pomodoro
        self.pomodoro_tab = PomodoroTab(self.pomodoro_service)
        self.stack.addWidget(self.pomodoro_tab)

        # Tab 3: System
        self.system_tab = SystemTab(self.system_monitor)
        self.stack.addWidget(self.system_tab)

        # Tab 4: Memo
        self.memo_tab = MemoTab()
        self.stack.addWidget(self.memo_tab)

        # Tab 5: Settings
        self.settings_tab = SettingsTab()
        self.settings_tab.reposition_requested.connect(self.reposition_requested.emit)
        self.settings_tab.settings_changed.connect(self.todos_changed.emit)
        self.stack.addWidget(self.settings_tab)

        main_layout.addWidget(self.stack, 1)

        self.switch_tab(0)

    def switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setProperty("active", "true" if i == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.pin_btn.setIcon(make_pin_icon(18, pinned=self.is_pinned))
        if self.is_pinned:
            self.pin_btn.setStyleSheet(f"""
                QPushButton#IconButton {{
                    background-color: {THEME['accent_blue']};
                    border: 1px solid #38BDF8;
                }}
            """)
            self.pin_btn.setToolTip("已固定面板（点击解除固定）")
        else:
            self.pin_btn.setStyleSheet("")
            self.pin_btn.setToolTip("固定面板（防止失焦自动收起）")

    def _update_clock(self):
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        now = datetime.now()
        wk = weekdays[now.weekday()]
        # High contrast formatting: Date in cyan, Time in bold bright white
        self.clock_lbl.setText(
            f"<span style='color: #94A3B8;'>{now.strftime('%m月%d日')} {wk}</span>  "
            f"<span style='color: #FFFFFF; font-size: 14px; font-weight: 800;'>{now.strftime('%H:%M:%S')}</span>"
        )
