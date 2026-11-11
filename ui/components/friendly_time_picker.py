from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QDateEdit, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from config import (
    WEEKDAY_NAMES, REPEAT_NONE, REPEAT_DAILY, REPEAT_WEEKLY, REPEAT_WORKDAY
)
from storage import calculate_next_occurrence
from ui.styles import THEME

class FriendlyTimePicker(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._setup_defaults()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Outer Card Container
        self.card = QFrame()
        self.card.setObjectName("TaskCard")
        self.card.setStyleSheet(f"""
            background: rgba(22, 25, 36, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 12px;
            padding: 2px;
        """)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(8)

        # 1. Top Control Bar: Checkbox + Repeat Mode Selector
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.enable_cb = QCheckBox("⏰ 启用时间提醒")
        self.enable_cb.setChecked(True)
        self.enable_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.enable_cb.setStyleSheet("""
            QCheckBox {
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
            }
        """)
        self.enable_cb.toggled.connect(self._on_enable_toggled)
        top_row.addWidget(self.enable_cb)

        top_row.addStretch()

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("单次到期提醒", REPEAT_NONE)
        self.mode_combo.addItem("每周指定星期", REPEAT_WEEKLY)
        self.mode_combo.addItem("工作日 (周一至五)", REPEAT_WORKDAY)
        self.mode_combo.addItem("每天重复", REPEAT_DAILY)
        self.mode_combo.setMinimumWidth(165)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        top_row.addWidget(self.mode_combo)

        card_layout.addLayout(top_row)

        # 2. Picker Body (Hidden when enable_cb is unchecked)
        self.body_widget = QWidget()
        body_layout = QVBoxLayout(self.body_widget)
        body_layout.setContentsMargins(0, 2, 0, 0)
        body_layout.setSpacing(8)

        # --- Sub-Widget A: Single-Time Mode (Date) ---
        self.single_widget = QWidget()
        single_layout = QVBoxLayout(self.single_widget)
        single_layout.setContentsMargins(0, 0, 0, 0)
        single_layout.setSpacing(6)

        # Date Row
        date_row = QHBoxLayout()
        date_row.setSpacing(6)

        date_lbl = QLabel("📅 日期:")
        date_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600; min-width: 48px;")
        date_row.addWidget(date_lbl)

        # Quick Date Pills
        self.btn_today = QPushButton("今天")
        self.btn_tomorrow = QPushButton("明天")
        self.btn_day_after = QPushButton("后天")

        for b in (self.btn_today, self.btn_tomorrow, self.btn_day_after):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    color: #FFFFFF;
                    border: 1px solid rgba(255, 255, 255, 0.14);
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background: rgba(10, 132, 255, 0.28);
                    border-color: #0A84FF;
                }
            """)

        self.btn_today.clicked.connect(lambda: self._set_quick_date(0))
        self.btn_tomorrow.clicked.connect(lambda: self._set_quick_date(1))
        self.btn_day_after.clicked.connect(lambda: self._set_quick_date(2))

        date_row.addWidget(self.btn_today)
        date_row.addWidget(self.btn_tomorrow)
        date_row.addWidget(self.btn_day_after)

        # Calendar Date Picker
        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setMinimumWidth(115)
        self.date_edit.setToolTip("点击日历选择任意日期")
        self.date_edit.dateChanged.connect(self._on_value_changed)
        date_row.addWidget(self.date_edit, 1)

        single_layout.addLayout(date_row)
        body_layout.addWidget(self.single_widget)

        # --- Sub-Widget B: Weekly Repeat (Weekdays Selector) ---
        self.weekly_widget = QWidget()
        weekly_layout = QHBoxLayout(self.weekly_widget)
        weekly_layout.setContentsMargins(0, 0, 0, 0)
        weekly_layout.setSpacing(5)

        w_lbl = QLabel("🔁 星期:")
        w_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600; min-width: 48px;")
        weekly_layout.addWidget(w_lbl)

        self.weekday_buttons = []
        for i, name in enumerate(WEEKDAY_NAMES, start=1):
            btn = QPushButton(name[-1])  # '一', '二', ...
            btn.setCheckable(True)
            btn.setChecked(i == 1)  # Default Monday
            btn.setFixedSize(36, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    color: #94A3B8;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 0;
                }
                QPushButton:checked {
                    background: #0A84FF;
                    color: #FFFFFF;
                    border: 1px solid #38BDF8;
                }
            """)
            btn.toggled.connect(self._on_value_changed)
            weekly_layout.addWidget(btn)
            self.weekday_buttons.append((i, btn))

        weekly_layout.addStretch()
        self.weekly_widget.setVisible(False)
        body_layout.addWidget(self.weekly_widget)

        # --- Common Time Section (Split into 2 spacious sub-rows) ---
        time_container = QVBoxLayout()
        time_container.setSpacing(6)

        # Line 1: Exact Hour & Minute Selection
        time_exact_row = QHBoxLayout()
        time_exact_row.setSpacing(6)

        time_lbl = QLabel("⏰ 时刻:")
        time_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600; min-width: 48px;")
        time_exact_row.addWidget(time_lbl)

        # Hour Combo (00 to 23)
        self.hour_combo = QComboBox()
        self.hour_combo.setFixedWidth(64)
        for h in range(24):
            self.hour_combo.addItem(f"{h:02d}", f"{h:02d}")
        self.hour_combo.currentIndexChanged.connect(self._on_value_changed)
        time_exact_row.addWidget(self.hour_combo)

        hour_tag = QLabel("时")
        hour_tag.setStyleSheet("color: #CBD5E1; font-size: 12px;")
        time_exact_row.addWidget(hour_tag)

        # Minute Combo (00, 05, 10, ... 55)
        self.min_combo = QComboBox()
        self.min_combo.setEditable(True)
        self.min_combo.setFixedWidth(64)
        for m in range(0, 60, 5):
            self.min_combo.addItem(f"{m:02d}", f"{m:02d}")
        self.min_combo.currentIndexChanged.connect(self._on_value_changed)
        self.min_combo.editTextChanged.connect(self._on_value_changed)
        time_exact_row.addWidget(self.min_combo)

        min_tag = QLabel("分")
        min_tag.setStyleSheet("color: #CBD5E1; font-size: 12px;")
        time_exact_row.addWidget(min_tag)

        time_exact_row.addStretch()
        time_container.addLayout(time_exact_row)

        # Line 2: Quick Time Chips (Has entire row, zero squeezing!)
        quick_time_row = QHBoxLayout()
        quick_time_row.setSpacing(6)

        quick_lbl = QLabel("快捷:")
        quick_lbl.setStyleSheet("color: #64748B; font-size: 11px; min-width: 48px;")
        quick_time_row.addWidget(quick_lbl)

        self.quick_time_btns = []
        for t_val, label in [("09:00", "09:00"), ("12:00", "12:00"), ("15:00", "15:00"), ("18:00", "18:00"), ("21:00", "21:00")]:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.06);
                    color: #CBD5E1;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 3px 8px;
                }
                QPushButton:hover {
                    background: rgba(10, 132, 255, 0.25);
                    color: #FFFFFF;
                    border-color: #0A84FF;
                }
            """)
            btn.clicked.connect(lambda checked, val=t_val: self._set_quick_time(val))
            quick_time_row.addWidget(btn)
            self.quick_time_btns.append(btn)

        quick_time_row.addStretch()
        time_container.addLayout(quick_time_row)

        body_layout.addLayout(time_container)

        # 3. Live High-Contrast Human Preview (with WordWrap so no text is ever clipped!)
        self.preview_lbl = QLabel("")
        self.preview_lbl.setWordWrap(True)
        self.preview_lbl.setStyleSheet("""
            background: rgba(56, 189, 248, 0.12);
            color: #38BDF8;
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 12px;
            font-weight: 600;
            line-height: 1.3;
        """)
        self.preview_lbl.setTextFormat(Qt.TextFormat.RichText)
        body_layout.addWidget(self.preview_lbl)

        card_layout.addWidget(self.body_widget)
        main_layout.addWidget(self.card)

    def _setup_defaults(self):
        now = datetime.now()
        next_hour = (now + timedelta(hours=1)).hour
        self.hour_combo.setCurrentIndex(next_hour)
        self.min_combo.setCurrentText("00")
        self._update_preview()

    def _on_enable_toggled(self, checked: bool):
        self.body_widget.setVisible(checked)
        self.mode_combo.setEnabled(checked)
        self._update_preview()
        self.changed.emit()

    def _on_mode_changed(self):
        mode = self.mode_combo.currentData()
        is_weekly = (mode == REPEAT_WEEKLY)
        is_single = (mode == REPEAT_NONE)

        self.single_widget.setVisible(is_single)
        self.weekly_widget.setVisible(is_weekly)
        self._update_preview()
        self.changed.emit()

    def _set_quick_date(self, day_offset: int):
        target = datetime.now().date() + timedelta(days=day_offset)
        self.date_edit.setDate(QDate(target.year, target.month, target.day))
        self._update_preview()

    def _set_quick_time(self, time_str: str):
        parts = time_str.split(":")
        if len(parts) == 2:
            h, m = int(parts[0]), parts[1]
            self.hour_combo.setCurrentIndex(h)
            self.min_combo.setCurrentText(m)
        self._update_preview()

    def _on_value_changed(self):
        self._update_preview()
        self.changed.emit()

    def _get_time_str(self) -> str:
        h = self.hour_combo.currentText().strip()
        m = self.min_combo.currentText().strip()
        try:
            h_int = max(0, min(23, int(h)))
            m_int = max(0, min(59, int(m)))
            return f"{h_int:02d}:{m_int:02d}"
        except Exception:
            return "09:00"

    def _update_preview(self):
        if not self.enable_cb.isChecked():
            self.preview_lbl.setText("💡 <span style='color: #94A3B8;'>未设置时间提醒 (纯日程备忘)</span>")
            return

        mode = self.mode_combo.currentData()
        time_str = self._get_time_str()

        if mode == REPEAT_NONE:
            qdate = self.date_edit.date()
            dt_str = f"{qdate.year():04d}-{qdate.month():02d}-{qdate.day():02d} {time_str}"
            try:
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                now = datetime.now()
                diff = dt - now
                if diff.total_seconds() < 0:
                    diff_desc = "<span style='color: #FF4D4F;'>已超时</span>"
                elif diff.total_seconds() < 3600:
                    mins = max(1, int(diff.total_seconds() // 60))
                    diff_desc = f"<span style='color: #FBBF24;'>仅剩 {mins} 分钟</span>"
                elif diff.days == 0:
                    hours = max(1, int(diff.total_seconds() // 3600))
                    diff_desc = f"今天内 (约 {hours} 小时后)"
                elif diff.days == 1:
                    diff_desc = "明天到期"
                else:
                    diff_desc = f"{diff.days} 天后"

                self.preview_lbl.setText(
                    f"⏰ 提醒时间: <span style='color: #FFFFFF; font-weight: bold;'>{dt_str}</span> ({diff_desc})"
                )
            except Exception:
                self.preview_lbl.setText(f"⏰ 提醒时间: {dt_str}")

        elif mode == REPEAT_WEEKLY:
            selected_days = [d for d, btn in self.weekday_buttons if btn.isChecked()]
            if not selected_days:
                selected_days = [1]
            day_names = [WEEKDAY_NAMES[d - 1] for d in sorted(selected_days)]
            days_desc = "、".join(day_names)
            next_due = calculate_next_occurrence(REPEAT_WEEKLY, selected_days, time_str)
            next_part = f" · 下次: <span style='color: #FFFFFF;'>{next_due}</span>" if next_due else ""
            self.preview_lbl.setText(
                f"🔁 每周重复: <span style='color: #34D399; font-weight: bold;'>每{days_desc} {time_str}</span>{next_part}"
            )

        elif mode == REPEAT_WORKDAY:
            next_due = calculate_next_occurrence(REPEAT_WORKDAY, [1, 2, 3, 4, 5], time_str)
            next_part = f" · 下次: <span style='color: #FFFFFF;'>{next_due}</span>" if next_due else ""
            self.preview_lbl.setText(
                f"🔁 工作日重复: <span style='color: #34D399; font-weight: bold;'>周一至周五 {time_str}</span>{next_part}"
            )

        elif mode == REPEAT_DAILY:
            next_due = calculate_next_occurrence(REPEAT_DAILY, [1, 2, 3, 4, 5, 6, 7], time_str)
            next_part = f" · 下次: <span style='color: #FFFFFF;'>{next_due}</span>" if next_due else ""
            self.preview_lbl.setText(
                f"🔁 每天重复: <span style='color: #34D399; font-weight: bold;'>每天 {time_str}</span>{next_part}"
            )

    # --- Public Accessors & Mutators ---
    def is_reminder_enabled(self) -> bool:
        return self.enable_cb.isChecked()

    def get_summary_text(self) -> str:
        """Returns a concise human-readable summary string for the collapsed badge."""
        if not self.enable_cb.isChecked():
            return "未设提醒"

        mode = self.mode_combo.currentData()
        time_str = self._get_time_str()

        if mode == REPEAT_NONE:
            qd = self.date_edit.date()
            today = QDate.currentDate()
            if qd == today:
                return f"今天 {time_str}"
            elif qd == today.addDays(1):
                return f"明天 {time_str}"
            else:
                return f"{qd.month():02d}-{qd.day():02d} {time_str}"
        elif mode == REPEAT_WEEKLY:
            selected_days = [d for d, btn in self.weekday_buttons if btn.isChecked()]
            if not selected_days:
                selected_days = [1]
            day_names = [WEEKDAY_NAMES[d - 1][-1] for d in sorted(selected_days)]
            return f"周{'、'.join(day_names)} {time_str}"
        elif mode == REPEAT_WORKDAY:
            return f"工作日 {time_str}"
        elif mode == REPEAT_DAILY:
            return f"每天 {time_str}"
        return time_str

    def get_repeat_type(self) -> str:
        if not self.enable_cb.isChecked():
            return REPEAT_NONE
        return self.mode_combo.currentData()

    def get_repeat_days(self) -> list:
        if self.get_repeat_type() == REPEAT_WEEKLY:
            days = [d for d, btn in self.weekday_buttons if btn.isChecked()]
            return days if days else [1]
        elif self.get_repeat_type() == REPEAT_WORKDAY:
            return [1, 2, 3, 4, 5]
        elif self.get_repeat_type() == REPEAT_DAILY:
            return [1, 2, 3, 4, 5, 6, 7]
        return []

    def get_repeat_time(self) -> str:
        return self._get_time_str()

    def get_due_time(self) -> str:
        if not self.enable_cb.isChecked():
            return ""

        mode = self.mode_combo.currentData()
        time_str = self._get_time_str()

        if mode == REPEAT_NONE:
            qd = self.date_edit.date()
            return f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d} {time_str}"
        else:
            days = self.get_repeat_days()
            calculated = calculate_next_occurrence(mode, days, time_str)
            return calculated or ""

    def set_data(self, due_time: str, repeat_type: str = REPEAT_NONE, repeat_days: list = None, repeat_time: str = ""):
        repeat_type = repeat_type or REPEAT_NONE
        repeat_days = repeat_days or []

        has_reminder = bool(due_time or (repeat_type != REPEAT_NONE and repeat_time))
        self.enable_cb.setChecked(has_reminder)

        # Set Mode
        r_map = {REPEAT_NONE: 0, REPEAT_WEEKLY: 1, REPEAT_WORKDAY: 2, REPEAT_DAILY: 3}
        self.mode_combo.setCurrentIndex(r_map.get(repeat_type, 0))

        # Set Repeat Days
        if repeat_type == REPEAT_WEEKLY and repeat_days:
            for day_idx, btn in self.weekday_buttons:
                btn.setChecked(day_idx in repeat_days)

        # Set Time
        effective_time = repeat_time
        if not effective_time and due_time:
            parts = due_time.split(" ")
            if len(parts) == 2:
                effective_time = parts[1]

        if effective_time:
            self._set_quick_time(effective_time)

        # Set Date (if single-time)
        if due_time:
            try:
                dt = datetime.strptime(due_time, "%Y-%m-%d %H:%M")
                self.date_edit.setDate(QDate(dt.year, dt.month, dt.day))
            except Exception:
                pass

        self._update_preview()
