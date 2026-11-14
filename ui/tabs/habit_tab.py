# ui/tabs/habit_tab.py - Dedicated Habits & Interval Reminders Manager
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFrame, QComboBox, QMenu,
    QProgressBar, QSizePolicy, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from storage import storage, get_habit_presentation
from ui.styles import THEME
from ui.components.toggle_switch import ToggleSwitch
from ui.tabs.habit_edit_dialog import HabitEditDialog
from ui.components.custom_interval_dialog import CustomIntervalDialog


class HabitCard(QFrame):
    toggled = pyqtSignal(str)              # habit_id
    checkin = pyqtSignal(str, int)         # habit_id, next_interval_minutes
    edited = pyqtSignal(str)               # habit_id
    deleted = pyqtSignal(str)              # habit_id

    def __init__(self, habit: dict, parent=None):
        super().__init__(parent)
        self.habit = habit
        self.setObjectName("HabitCard")
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        is_enabled = self.habit.get("enabled", True)
        habit_info = get_habit_presentation(self.habit)
        icon = habit_info["icon"]
        unit = habit_info["unit"]
        now = datetime.now()
        now_time_str = now.strftime("%H:%M")
        start_t = self.habit.get("start_time", "09:00")
        end_t = self.habit.get("end_time", "18:00")
        in_window = start_t <= now_time_str <= end_t

        # 1. Left iOS Toggle Switch
        switch_box = QVBoxLayout()
        switch_box.setAlignment(Qt.AlignmentFlag.AlignTop)
        switch_box.setContentsMargins(0, 2, 0, 0)

        self.toggle_switch = ToggleSwitch(checked=is_enabled)
        self.toggle_switch.setToolTip("开启或暂停该循环提醒")
        self.toggle_switch.toggled.connect(lambda chk: self.toggled.emit(self.habit["id"]))
        switch_box.addWidget(self.toggle_switch)
        layout.addLayout(switch_box)

        # 2. Middle Content
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        # Row 1: Time Range + Title + Status Badge
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        range_badge = QLabel(f"{start_t} ~ {end_t}")
        range_badge.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 700;
            color: {'#38BDF8' if is_enabled else '#64748B'};
            background: {'rgba(56, 189, 248, 0.15)' if is_enabled else 'rgba(255, 255, 255, 0.05)'};
            border: 1px solid {'rgba(56, 189, 248, 0.35)' if is_enabled else 'rgba(255, 255, 255, 0.1)'};
            padding: 2px 7px;
            border-radius: 6px;
        """)
        title_row.addWidget(range_badge)

        self.title_lbl = QLabel(self.habit.get("title", ""))
        self.title_lbl.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {'#FFFFFF' if is_enabled else '#94A3B8'};
        """)
        self.title_lbl.setWordWrap(True)
        title_row.addWidget(self.title_lbl, 1)

        # Status badge
        if not is_enabled:
            status_badge = QLabel("⏸️ 已暂停")
            status_badge.setStyleSheet("color: #94A3B8; background: rgba(255,255,255,0.06); font-size: 11px; padding: 2px 7px; border-radius: 6px;")
        elif not in_window:
            status_badge = QLabel("🌙 时段外休眠")
            status_badge.setStyleSheet("color: #A78BFA; background: rgba(167, 139, 250, 0.15); font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 6px;")
        else:
            status_badge = QLabel("🟢 循环运行中")
            status_badge.setStyleSheet("color: #34D399; background: rgba(52, 211, 153, 0.18); font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 6px;")
        title_row.addWidget(status_badge)

        info_layout.addLayout(title_row)

        # Row 2: Next Trigger + Progress + Default interval
        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)
        meta_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        next_trig = self.habit.get("next_trigger")
        if next_trig and is_enabled:
            next_t_str = next_trig.split(" ")[-1]
            next_lbl = QLabel(f"⏰ 下次: {next_t_str}")
            next_lbl.setStyleSheet("color: #FBBF24; font-size: 11px; font-weight: 700; background: rgba(251, 191, 36, 0.15); padding: 2px 6px; border-radius: 5px;")
            meta_row.addWidget(next_lbl)

        interval = self.habit.get("default_interval", 45)
        int_lbl = QLabel(f"🔄 默认每 {interval} 分钟")
        int_lbl.setStyleSheet("color: #CBD5E1; font-size: 11px; background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 5px;")
        meta_row.addWidget(int_lbl)

        # Progress badge
        c = self.habit.get("today_count", 0)
        target = self.habit.get("target_count", 8)
        prog_badge = QLabel(f"{icon} 今日 {c}/{target} {unit}")
        prog_badge.setStyleSheet(f"""
            color: {habit_info['color']};
            background: rgba(56, 189, 248, 0.15);
            font-size: 11px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 5px;
        """)
        meta_row.addWidget(prog_badge)

        last_c = self.habit.get("last_checkin_at")
        if last_c:
            last_t = last_c.split(" ")[-1]
            last_lbl = QLabel(f"上次: {last_t[:5]}")
            last_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
            meta_row.addWidget(last_lbl)

        meta_row.addStretch()
        info_layout.addLayout(meta_row)

        layout.addLayout(info_layout, 1)

        # 3. Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Dynamic Checkin Button
        self.checkin_btn = QPushButton(f"{icon} 打卡 +1")
        self.checkin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkin_btn.setToolTip("记录打卡，并自选下一次提醒间隔")
        self.checkin_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(56, 189, 248, 0.18);
                color: {habit_info['color']};
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 7px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 700;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background: {habit_info['color']};
                color: #000000;
            }}
        """)
        self.checkin_btn.clicked.connect(self._show_checkin_menu)
        btn_layout.addWidget(self.checkin_btn)

        # Edit button
        edit_btn = QPushButton("✏️")
        edit_btn.setFixedSize(30, 30)
        edit_btn.setToolTip("编辑提醒时段与目标")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet("border-radius: 6px; padding: 0;")
        edit_btn.clicked.connect(lambda: self.edited.emit(self.habit["id"]))
        btn_layout.addWidget(edit_btn)

        # Delete button
        del_btn = QPushButton("🗑️")
        del_btn.setFixedSize(30, 30)
        del_btn.setToolTip("删除循环提醒")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("border-radius: 6px; padding: 0;")
        del_btn.clicked.connect(lambda: self.deleted.emit(self.habit["id"]))
        btn_layout.addWidget(del_btn)

        layout.addLayout(btn_layout)

        self.setStyleSheet(f"""
            QFrame#HabitCard {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border_light']};
                border-radius: 12px;
            }}
            QFrame#HabitCard:hover {{
                border-color: rgba(56, 189, 248, 0.4);
                background-color: {THEME['bg_card_hover']};
            }}
        """)

    def _show_checkin_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1A1D27;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 4px;
                color: #FFFFFF;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0A84FF;
            }
        """)

        menu.addAction("💧 已完成！选择下次提醒时间:").setEnabled(False)
        menu.addSeparator()

        durations = [
            ("⚡ 30 分钟后提醒我", 30),
            ("⏰ 45 分钟后提醒我", 45),
            ("⏳ 60 分钟 (1小时) 后提醒", 60),
            ("☕ 90 分钟 (1.5小时) 后提醒", 90),
            ("🔄 按默认间隔提醒", self.habit.get("default_interval", 45)),
        ]
        for label, mins in durations:
            action = menu.addAction(label)
            action.triggered.connect(lambda chk, m=mins: self.checkin.emit(self.habit["id"], m))

        menu.addSeparator()
        custom_act = menu.addAction("⚙️ 自定义提醒间隔...")
        custom_act.triggered.connect(self._prompt_custom_interval)

        menu.exec(self.cursor().pos())

    def _prompt_custom_interval(self):
        val, ok = CustomIntervalDialog.get_interval(
            parent=self.window(),
            title="自定义下次提醒时间",
            prompt="请输入下次提醒间隔 (分钟):",
            default_val=self.habit.get("default_interval", 30),
            min_val=1,
            max_val=720
        )
        if ok and val > 0:
            self.checkin.emit(self.habit["id"], val)


class HabitTab(QWidget):
    habits_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_habits()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(10)

        # 1. Today's Overview Banner Card
        self.overview_card = QFrame()
        self.overview_card.setStyleSheet("""
            background: linear-gradient(135deg, rgba(14, 165, 233, 0.15) 0%, rgba(30, 27, 75, 0.4) 100%);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 12px;
            padding: 2px;
        """)
        overview_layout = QVBoxLayout(self.overview_card)
        overview_layout.setContentsMargins(14, 12, 14, 12)
        overview_layout.setSpacing(8)

        top_stats = QHBoxLayout()
        self.today_title = QLabel("💧 今日喝水与健康习惯")
        self.today_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #FFFFFF;")
        top_stats.addWidget(self.today_title)
        top_stats.addStretch()

        self.today_score = QLabel("今日饮水: 0 / 8 杯 (0%)")
        self.today_score.setStyleSheet("font-size: 12px; font-weight: 700; color: #38BDF8;")
        top_stats.addWidget(self.today_score)
        overview_layout.addLayout(top_stats)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #38BDF8);
                border-radius: 4px;
            }
        """)
        overview_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.overview_card)

        # 2. Quick Add Habit Card
        add_box = QFrame()
        add_box.setStyleSheet(f"""
            background-color: {THEME['bg_card']};
            border-radius: 12px;
            border: 1px solid {THEME['border_light']};
            padding: 2px;
        """)
        add_layout = QVBoxLayout(add_box)
        add_layout.setContentsMargins(10, 8, 10, 8)
        add_layout.setSpacing(8)

        # Title input + Add btn
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("➕ 添加习惯循环提醒 (例如: 定时喝水打卡 💧、起身活动 🚶)...")
        self.input_edit.setStyleSheet("font-size: 13px; font-weight: 500; color: #FFFFFF;")
        self.input_edit.returnPressed.connect(self._on_add_habit)
        input_row.addWidget(self.input_edit, 1)

        self.add_btn = QPushButton("添加提醒")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_habit)
        input_row.addWidget(self.add_btn)
        add_layout.addLayout(input_row)

        # Time range & interval row
        config_row = QHBoxLayout()
        config_row.setSpacing(8)
        config_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        config_row.addWidget(QLabel("时段:"))
        self.start_combo = QComboBox()
        for h in range(6, 24):
            self.start_combo.addItem(f"{h:02d}:00", f"{h:02d}:00")
        self.start_combo.setCurrentIndex(3)  # 09:00
        self.start_combo.setFixedWidth(85)
        config_row.addWidget(self.start_combo)

        config_row.addWidget(QLabel("至"))

        self.end_combo = QComboBox()
        for h in range(7, 24):
            self.end_combo.addItem(f"{h:02d}:00", f"{h:02d}:00")
        self.end_combo.setCurrentIndex(11)  # 18:00
        self.end_combo.setFixedWidth(85)
        config_row.addWidget(self.end_combo)

        config_row.addSpacing(6)
        config_row.addWidget(QLabel("间隔:"))

        self.interval_combo = QComboBox()
        for m in (15, 20, 30, 45, 60, 90, 120):
            self.interval_combo.addItem(f"{m}分钟", m)
        self.interval_combo.addItem("自定义...", -1)
        self.interval_combo.setCurrentIndex(3)  # 45分钟
        self.interval_combo.setFixedWidth(100)
        self.interval_combo.currentIndexChanged.connect(self._on_interval_combo_changed)
        config_row.addWidget(self.interval_combo)

        config_row.addStretch()
        add_layout.addLayout(config_row)

        main_layout.addWidget(add_box)

        # 3. Scrollable Habits List Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()

        self.scroll_area.setWidget(self.list_container)
        main_layout.addWidget(self.scroll_area, 1)

        # 4. Bottom status
        bottom_bar = QHBoxLayout()
        self.summary_lbl = QLabel("共有 0 个循环习惯 · 运行中")
        self.summary_lbl.setStyleSheet("color: #CBD5E1; font-size: 12px; font-weight: 600;")
        bottom_bar.addWidget(self.summary_lbl)
        bottom_bar.addStretch()
        main_layout.addLayout(bottom_bar)

    def _on_interval_combo_changed(self, idx: int):
        if self.interval_combo.itemData(idx) == -1:
            val, ok = CustomIntervalDialog.get_interval(
                parent=self.window(),
                title="自定义习惯间隔",
                prompt="请输入默认提醒间隔 (分钟):",
                default_val=45,
                min_val=1,
                max_val=720
            )
            if ok and val > 0:
                text = f"{val}分钟"
                existing = self.interval_combo.findData(val)
                if existing >= 0:
                    self.interval_combo.setCurrentIndex(existing)
                else:
                    self.interval_combo.insertItem(self.interval_combo.count() - 1, text, val)
                    self.interval_combo.setCurrentIndex(self.interval_combo.count() - 2)
            else:
                self.interval_combo.setCurrentIndex(3)

    def _on_add_habit(self):
        title = self.input_edit.text().strip()
        if not title:
            return

        start_t = self.start_combo.currentData()
        end_t = self.end_combo.currentData()
        interval = self.interval_combo.currentData()

        storage.add_habit(
            title=title,
            start_time=start_t,
            end_time=end_t,
            default_interval=interval,
            target_count=8,
            habit_type="water" if "水" in title else "custom",
            enabled=True
        )

        self.input_edit.clear()
        self.load_habits()
        self.habits_changed.emit()

    def load_habits(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        habits = storage.get_habits()
        total_count = len(habits)
        active_count = sum(1 for h in habits if h.get("enabled", True))

        # Calculate water tracker stats
        water_habits = [h for h in habits if "水" in h.get("title", "") or h.get("type") == "water"]
        if water_habits:
            wh = water_habits[0]
            cnt = wh.get("today_count", 0)
            tgt = max(1, wh.get("target_count", 8))
            pct = min(100, int((cnt / tgt) * 100))
            self.today_score.setText(f"今日已喝: {cnt} / {tgt} 杯 ({pct}%)")
            self.progress_bar.setValue(pct)
            self.overview_card.setVisible(True)
        else:
            self.overview_card.setVisible(False)

        self.summary_lbl.setText(f"共有 {total_count} 个习惯提醒 · {active_count} 个运行中")

        if not habits:
            empty_lbl = QLabel("💧 暂无循环习惯提醒\n在上方设定开始与结束时间，即可开启贴心的循环喝水与健康提醒！")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #94A3B8; padding: 40px; font-size: 13px; font-weight: 500; line-height: 1.5;")
            self.list_layout.insertWidget(0, empty_lbl)
            return

        for habit in habits:
            card = HabitCard(habit)
            card.toggled.connect(self._on_toggle_habit)
            card.checkin.connect(self._on_checkin_habit)
            card.edited.connect(self._on_edit_habit)
            card.deleted.connect(self._on_delete_habit)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

    def _on_toggle_habit(self, habit_id: str):
        storage.toggle_habit_enabled(habit_id)
        self.load_habits()
        self.habits_changed.emit()

    def _on_checkin_habit(self, habit_id: str, next_interval_minutes: int):
        storage.checkin_habit(habit_id, next_interval_minutes=next_interval_minutes)
        self.load_habits()
        self.habits_changed.emit()

    def _on_edit_habit(self, habit_id: str):
        habits = storage.get_habits()
        h = next((x for x in habits if x["id"] == habit_id), None)
        if not h:
            return

        dialog = HabitEditDialog(h, self.window())
        dialog.raise_()
        dialog.activateWindow()
        if dialog.exec():
            if dialog.updated_data:
                storage.update_habit(habit_id, dialog.updated_data)
                self.load_habits()
                self.habits_changed.emit()

    def _on_delete_habit(self, habit_id: str):
        storage.delete_habit(habit_id)
        self.load_habits()
        self.habits_changed.emit()
