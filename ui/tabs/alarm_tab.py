# ui/tabs/alarm_tab.py - Dedicated Alarm & Habit Routine Manager for Windows Dynamic Island
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFrame, QComboBox, QMenu,
    QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from storage import storage, format_alarm_repeat, calculate_next_occurrence
from config import (
    WEEKDAY_NAMES, REPEAT_DAILY, REPEAT_WEEKLY, REPEAT_WORKDAY
)
from ui.styles import THEME
from ui.components.toggle_switch import ToggleSwitch
from ui.tabs.alarm_edit_dialog import AlarmEditDialog


class AlarmCard(QFrame):
    toggled = pyqtSignal(str)     # alarm_id
    checkin = pyqtSignal(str)     # alarm_id
    snooze = pyqtSignal(str, int) # alarm_id, minutes
    cancel_snooze = pyqtSignal(str) # alarm_id
    edited = pyqtSignal(str)      # alarm_id
    deleted = pyqtSignal(str)     # alarm_id

    def __init__(self, alarm: dict, parent=None):
        super().__init__(parent)
        self.alarm = alarm
        self.setObjectName("AlarmCard")
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        is_enabled = self.alarm.get("enabled", True)
        is_snoozed = bool(self.alarm.get("snooze_until"))

        # 1. Left iOS-style Toggle Switch
        switch_box = QVBoxLayout()
        switch_box.setAlignment(Qt.AlignmentFlag.AlignTop)
        switch_box.setContentsMargins(0, 2, 0, 0)

        self.toggle_switch = ToggleSwitch(checked=is_enabled)
        self.toggle_switch.setToolTip("开启或暂停该周期闹钟")
        self.toggle_switch.toggled.connect(lambda chk: self.toggled.emit(self.alarm["id"]))
        switch_box.addWidget(self.toggle_switch)
        layout.addLayout(switch_box)

        # 2. Main Content
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        # Row 1: Time Banner + Alarm Title + Status Badge
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Crisp High-Contrast Alarm Time
        time_badge = QLabel(self.alarm.get("time", "09:30"))
        time_badge.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 800;
            color: {'#38BDF8' if is_enabled else '#64748B'};
            background: {'rgba(56, 189, 248, 0.15)' if is_enabled else 'rgba(255, 255, 255, 0.05)'};
            border: 1px solid {'rgba(56, 189, 248, 0.35)' if is_enabled else 'rgba(255, 255, 255, 0.1)'};
            padding: 2px 8px;
            border-radius: 6px;
            letter-spacing: 0.5px;
        """)
        title_row.addWidget(time_badge)

        self.title_lbl = QLabel(self.alarm.get("title", ""))
        self.title_lbl.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {'#FFFFFF' if is_enabled else '#94A3B8'};
        """)
        self.title_lbl.setWordWrap(True)
        title_row.addWidget(self.title_lbl, 1)

        # Status badge (Active / Paused / Snoozed)
        if is_snoozed:
            snooze_lbl = QLabel(f"⏳ 延时至 {self.alarm.get('snooze_until').split(' ')[-1]}")
            snooze_lbl.setStyleSheet("""
                color: #FBBF24;
                background: rgba(251, 191, 36, 0.2);
                border: 1px solid rgba(251, 191, 36, 0.4);
                font-size: 11px;
                font-weight: 700;
                padding: 2px 7px;
                border-radius: 6px;
            """)
            title_row.addWidget(snooze_lbl)
        elif is_enabled:
            status_badge = QLabel("🔔 运行中")
            status_badge.setStyleSheet("""
                color: #34D399;
                background: rgba(52, 211, 153, 0.18);
                border: 1px solid rgba(52, 211, 153, 0.35);
                font-size: 11px;
                font-weight: 700;
                padding: 2px 7px;
                border-radius: 6px;
            """)
            title_row.addWidget(status_badge)
        else:
            paused_badge = QLabel("⏸️ 已暂停")
            paused_badge.setStyleSheet("""
                color: #94A3B8;
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                font-size: 11px;
                font-weight: 600;
                padding: 2px 7px;
                border-radius: 6px;
            """)
            title_row.addWidget(paused_badge)

        info_layout.addLayout(title_row)

        # Row 2: Recurrence pill + Next trigger prediction + Note
        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        meta_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        rep_text = format_alarm_repeat(self.alarm)
        rep_lbl = QLabel(rep_text)
        rep_lbl.setStyleSheet("""
            color: #A7F3D0;
            background: rgba(16, 185, 129, 0.15);
            font-size: 11px;
            font-weight: 600;
            padding: 2px 7px;
            border-radius: 6px;
        """)
        meta_row.addWidget(rep_lbl)

        next_trig = self.alarm.get("next_trigger")
        if next_trig and is_enabled:
            next_lbl = QLabel(f"⏰ 下次: {next_trig}")
            next_lbl.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 600;")
            meta_row.addWidget(next_lbl)

        desc = self.alarm.get("description", "")
        if desc:
            desc_lbl = QLabel(f"📝 {desc[:18]}")
            desc_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
            meta_row.addWidget(desc_lbl)

        meta_row.addStretch()
        info_layout.addLayout(meta_row)

        # Row 3: Check-in streak badge & last checkin record
        checkin_row = QHBoxLayout()
        checkin_row.setSpacing(8)
        checkin_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        c_count = self.alarm.get("checkin_count", 0)
        c_badge = QLabel(f"🎯 已打卡 {c_count} 次")
        c_badge.setStyleSheet("""
            color: #F472B6;
            background: rgba(244, 114, 182, 0.15);
            border: 1px solid rgba(244, 114, 182, 0.3);
            font-size: 11px;
            font-weight: 700;
            padding: 1px 6px;
            border-radius: 5px;
        """)
        checkin_row.addWidget(c_badge)

        last_c = self.alarm.get("last_checkin_at")
        if last_c:
            last_lbl = QLabel(f"上次打卡: {last_c.split(' ')[0]}")
            last_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
            checkin_row.addWidget(last_lbl)

        checkin_row.addStretch()
        info_layout.addLayout(checkin_row)

        layout.addLayout(info_layout, 1)

        # 3. Action Buttons (Check-in, Snooze, Edit, Delete)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Prominent Check-in Button
        self.checkin_btn = QPushButton("🎯 打卡")
        self.checkin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkin_btn.setToolTip("完成本期打卡，并自动推进到下期响铃")
        self.checkin_btn.setStyleSheet("""
            QPushButton {
                background: rgba(48, 209, 88, 0.2);
                color: #30D158;
                border: 1px solid rgba(48, 209, 88, 0.4);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #30D158;
                color: #FFFFFF;
            }
        """)
        self.checkin_btn.clicked.connect(lambda: self.checkin.emit(self.alarm["id"]))
        btn_layout.addWidget(self.checkin_btn)

        # Snooze Button / Cancel Snooze Button
        if is_snoozed:
            cancel_snooze_btn = QPushButton("✕ 恢复")
            cancel_snooze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            cancel_snooze_btn.setToolTip("取消延时状态，恢复正常周期")
            cancel_snooze_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(239, 68, 68, 0.2);
                    color: #EF4444;
                    border: 1px solid rgba(239, 68, 68, 0.4);
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 700;
                }
            """)
            cancel_snooze_btn.clicked.connect(lambda: self.cancel_snooze.emit(self.alarm["id"]))
            btn_layout.addWidget(cancel_snooze_btn)
        else:
            snooze_btn = QPushButton("⏳ 延时")
            snooze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            snooze_btn.setToolTip("延时贪睡提醒")
            snooze_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(251, 191, 36, 0.15);
                    color: #FBBF24;
                    border: 1px solid rgba(251, 191, 36, 0.35);
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #FBBF24;
                    color: #000000;
                }
            """)
            snooze_btn.clicked.connect(self._show_snooze_menu)
            btn_layout.addWidget(snooze_btn)

        # Edit button
        edit_btn = QPushButton("✏️")
        edit_btn.setFixedSize(28, 28)
        edit_btn.setToolTip("编辑闹钟")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet("border-radius: 6px; padding: 0;")
        edit_btn.clicked.connect(lambda: self.edited.emit(self.alarm["id"]))
        btn_layout.addWidget(edit_btn)

        # Delete button
        del_btn = QPushButton("🗑️")
        del_btn.setFixedSize(28, 28)
        del_btn.setToolTip("删除闹钟")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("border-radius: 6px; padding: 0;")
        del_btn.clicked.connect(lambda: self.deleted.emit(self.alarm["id"]))
        btn_layout.addWidget(del_btn)

        layout.addLayout(btn_layout)

        # Card appearance styling
        self.setStyleSheet(f"""
            QFrame#AlarmCard {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border_light']};
                border-radius: 12px;
            }}
            QFrame#AlarmCard:hover {{
                border-color: rgba(56, 189, 248, 0.4);
                background-color: {THEME['bg_card_hover']};
            }}
        """)

    def _show_snooze_menu(self):
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
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0A84FF;
            }
        """)

        durations = [("稍后 5 分钟", 5), ("稍后 10 分钟", 10), ("稍后 30 分钟", 30), ("稍后 1 小时", 60)]
        for label, mins in durations:
            action = menu.addAction(label)
            action.triggered.connect(lambda chk, m=mins: self.snooze.emit(self.alarm["id"], m))

        menu.exec(self.cursor().pos())


class AlarmTab(QWidget):
    alarms_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_repeat_type = REPEAT_WEEKLY
        self._init_ui()
        self.load_alarms()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(10)

        # 1. Quick Add Alarm Box
        add_box = QFrame()
        add_box.setStyleSheet(f"""
            background-color: {THEME['bg_card']};
            border-radius: 12px;
            border: 1px solid {THEME['border_light']};
            padding: 2px;
        """)
        add_layout = QVBoxLayout(add_box)
        add_layout.setContentsMargins(10, 10, 10, 10)
        add_layout.setSpacing(8)

        # Row 1: Title input + Add Button
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("➕ 新建周期闹钟与习惯 (如: 每周一例会、每天15:00喝水打卡)...")
        self.input_edit.setStyleSheet("font-size: 13px; font-weight: 500; color: #FFFFFF;")
        self.input_edit.returnPressed.connect(self._on_add_alarm)
        input_row.addWidget(self.input_edit, 1)

        self.add_btn = QPushButton("添加闹钟")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_alarm)
        input_row.addWidget(self.add_btn)

        add_layout.addLayout(input_row)

        # Row 2: Time Picker + Repeat Mode Pills
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)
        controls_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        controls_row.addWidget(QLabel("时间:"))
        self.hour_combo = QComboBox()
        for h in range(24):
            self.hour_combo.addItem(f"{h:02d} 时", f"{h:02d}")
        self.hour_combo.setCurrentIndex(9)
        self.hour_combo.setFixedWidth(75)
        controls_row.addWidget(self.hour_combo)

        self.min_combo = QComboBox()
        for m in range(0, 60, 5):
            self.min_combo.addItem(f"{m:02d} 分", f"{m:02d}")
        self.min_combo.setCurrentIndex(6)  # 30分
        self.min_combo.setFixedWidth(75)
        controls_row.addWidget(self.min_combo)

        controls_row.addSpacing(6)
        controls_row.addWidget(QLabel("周期:"))

        self.btn_daily = QPushButton("每天")
        self.btn_workday = QPushButton("工作日")
        self.btn_weekly = QPushButton("每周自定义")

        self.rep_buttons = {
            REPEAT_DAILY: self.btn_daily,
            REPEAT_WORKDAY: self.btn_workday,
            REPEAT_WEEKLY: self.btn_weekly,
        }

        for k, btn in self.rep_buttons.items():
            btn.setObjectName("FilterTag")
            btn.setFixedHeight(26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda chk, m=k: self._select_repeat(m))
            controls_row.addWidget(btn)

        controls_row.addStretch()
        add_layout.addLayout(controls_row)

        # Row 3: Weekday check capsules for weekly mode
        self.weekdays_bar = QFrame()
        self.weekdays_bar.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 8px; padding: 4px;")
        weekdays_layout = QHBoxLayout(self.weekdays_bar)
        weekdays_layout.setContentsMargins(4, 2, 4, 2)
        weekdays_layout.setSpacing(6)

        self.day_capsules = []
        for idx, name in enumerate(WEEKDAY_NAMES, start=1):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setChecked(idx == 1)  # Default Monday
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(self._update_weekday_styles)
            weekdays_layout.addWidget(btn)
            self.day_capsules.append((idx, btn))

        add_layout.addWidget(self.weekdays_bar)
        main_layout.addWidget(add_box)

        # 2. Scrollable Alarm List Area
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

        # 3. Bottom Summary Status Bar
        bottom_bar = QHBoxLayout()
        self.summary_lbl = QLabel("共有 0 个周期闹钟 · 0 个运行中")
        self.summary_lbl.setStyleSheet("color: #CBD5E1; font-size: 12px; font-weight: 600;")
        bottom_bar.addWidget(self.summary_lbl)

        bottom_bar.addStretch()
        main_layout.addLayout(bottom_bar)

        self._select_repeat(REPEAT_WEEKLY)

    def _select_repeat(self, mode: str):
        self.current_repeat_type = mode
        for k, btn in self.rep_buttons.items():
            btn.setProperty("active", "true" if k == mode else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self.weekdays_bar.setVisible(mode == REPEAT_WEEKLY)
        self._update_weekday_styles()

    def _update_weekday_styles(self):
        for idx, btn in self.day_capsules:
            if btn.isChecked():
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(56, 189, 248, 0.25);
                        color: #38BDF8;
                        border: 1.5px solid #38BDF8;
                        border-radius: 6px;
                        font-size: 11px;
                        font-weight: 700;
                        padding: 3px 6px;
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
                        padding: 3px 6px;
                    }
                """)

    def _on_add_alarm(self):
        title = self.input_edit.text().strip()
        if not title:
            return

        h = self.hour_combo.currentData()
        m = self.min_combo.currentData()
        time_str = f"{h}:{m}"

        repeat_type = self.current_repeat_type
        repeat_days = []
        if repeat_type == REPEAT_WEEKLY:
            repeat_days = [idx for idx, btn in self.day_capsules if btn.isChecked()]
            if not repeat_days:
                repeat_days = [1]
        elif repeat_type == REPEAT_DAILY:
            repeat_days = [1, 2, 3, 4, 5, 6, 7]
        elif repeat_type == REPEAT_WORKDAY:
            repeat_days = [1, 2, 3, 4, 5]

        storage.add_alarm(
            title=title,
            time=time_str,
            repeat_type=repeat_type,
            repeat_days=repeat_days,
            enabled=True
        )

        self.input_edit.clear()
        self.load_alarms()
        self.alarms_changed.emit()

    def load_alarms(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        alarms = storage.get_alarms()
        total_count = len(alarms)
        active_count = sum(1 for a in alarms if a.get("enabled", True))
        total_checkins = sum(a.get("checkin_count", 0) for a in alarms)

        self.summary_lbl.setText(f"共有 {total_count} 个周期闹钟 · {active_count} 个运行中 · 累计打卡 {total_checkins} 次")

        if not alarms:
            empty_lbl = QLabel("⏰ 暂无周期闹钟\n在上方输入标题与时间即可添加每周、每天或工作日提醒！")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #94A3B8; padding: 40px; font-size: 13px; font-weight: 500; line-height: 1.5;")
            self.list_layout.insertWidget(0, empty_lbl)
            return

        for alarm in alarms:
            card = AlarmCard(alarm)
            card.toggled.connect(self._on_toggle_alarm)
            card.checkin.connect(self._on_checkin_alarm)
            card.snooze.connect(self._on_snooze_alarm)
            card.cancel_snooze.connect(self._on_cancel_snooze)
            card.edited.connect(self._on_edit_alarm)
            card.deleted.connect(self._on_delete_alarm)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

    def _on_toggle_alarm(self, alarm_id: str):
        storage.toggle_alarm_enabled(alarm_id)
        self.load_alarms()
        self.alarms_changed.emit()

    def _on_checkin_alarm(self, alarm_id: str):
        alarm = storage.checkin_alarm(alarm_id)
        self.load_alarms()
        self.alarms_changed.emit()

    def _on_snooze_alarm(self, alarm_id: str, minutes: int):
        storage.snooze_alarm(alarm_id, minutes)
        self.load_alarms()
        self.alarms_changed.emit()

    def _on_cancel_snooze(self, alarm_id: str):
        storage.cancel_alarm_snooze(alarm_id)
        self.load_alarms()
        self.alarms_changed.emit()

    def _on_edit_alarm(self, alarm_id: str):
        alarms = storage.get_alarms()
        alarm = next((a for a in alarms if a["id"] == alarm_id), None)
        if not alarm:
            return

        dialog = AlarmEditDialog(alarm, self.window())
        dialog.raise_()
        dialog.activateWindow()
        if dialog.exec():
            if dialog.updated_data:
                storage.update_alarm(alarm_id, dialog.updated_data)
                self.load_alarms()
                self.alarms_changed.emit()

    def _on_delete_alarm(self, alarm_id: str):
        storage.delete_alarm(alarm_id)
        self.load_alarms()
        self.alarms_changed.emit()
