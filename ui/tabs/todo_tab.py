from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFrame, QCheckBox, QComboBox,
    QMenu, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from storage import (
    storage, format_repeat_display, calculate_next_occurrence, parse_natural_time
)
from config import (
    PRIORITY_CONFIG, CATEGORIES, WEEKDAY_NAMES,
    REPEAT_NONE, REPEAT_DAILY, REPEAT_WEEKLY, REPEAT_WORKDAY
)
from ui.styles import THEME
from ui.tabs.todo_edit_dialog import TodoEditDialog
from ui.components.friendly_time_picker import FriendlyTimePicker

class TaskCard(QFrame):
    toggled = pyqtSignal(str)   # todo_id
    edited = pyqtSignal(str)    # todo_id
    deleted = pyqtSignal(str)   # todo_id
    expanded_changed = pyqtSignal(str, bool) # todo_id, is_expanded

    def __init__(self, todo: dict, parent=None):
        super().__init__(parent)
        self.todo = todo
        self.is_expanded = False
        self.setObjectName("TaskCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._init_ui()

    def _init_ui(self):
        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)

        is_completed = self.todo.get("completed", False)

        # --- 1. Header Row (Always visible) ---
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        # 1. Circular Checkbox
        self.cb = QCheckBox()
        self.cb.setChecked(is_completed)
        self.cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cb.setStyleSheet("margin-top: 2px;")
        self.cb.toggled.connect(lambda: self.toggled.emit(self.todo["id"]))
        header_layout.addWidget(self.cb, 0, Qt.AlignmentFlag.AlignTop)

        # 2. Main Content
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        # Row 1: Priority badge + Task Title
        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        prio = self.todo.get("priority", "medium")
        prio_info = PRIORITY_CONFIG.get(prio, PRIORITY_CONFIG["medium"])
        prio_badge = QLabel(prio_info["label"])
        prio_badge.setStyleSheet(f"""
            color: {prio_info['color']};
            background-color: {prio_info['bg']};
            font-size: 11px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 6px;
            min-height: 20px;
        """)
        title_row.addWidget(prio_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        self.title_lbl = QLabel(self.todo.get("title", ""))
        self.title_lbl.setWordWrap(False)
        self.title_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._apply_title_style()
        title_row.addWidget(self.title_lbl, 1, Qt.AlignmentFlag.AlignVCenter)

        info_layout.addLayout(title_row)

        # Row 2: Badges (Category + Due Time / Countdown + Recurrence)
        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)

        # Category badge
        cat = self.todo.get("category", "默认")
        cat_badge = QLabel(cat)
        cat_badge.setStyleSheet("""
            color: #CBD5E1;
            background-color: rgba(255, 255, 255, 0.08);
            font-size: 11px;
            font-weight: 600;
            padding: 2px 7px;
            border-radius: 6px;
            min-height: 20px;
        """)
        meta_row.addWidget(cat_badge)

        # Due time & Countdown badge
        due = self.todo.get("due_time")
        if due:
            try:
                due_dt = datetime.strptime(due, "%Y-%m-%d %H:%M")
                diff = due_dt - datetime.now()

                if is_completed:
                    time_badge = QLabel(f"⏰ {due} (已完成)")
                    time_badge.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500; min-height: 20px;")
                elif diff.total_seconds() < 0:
                    mins_over = int(abs(diff.total_seconds()) // 60)
                    time_badge = QLabel(f"⚠️ 超时 {mins_over}分 · {due}")
                    time_badge.setStyleSheet("""
                        color: #FF4D4F;
                        background: rgba(255, 77, 79, 0.2);
                        border: 1px solid rgba(255, 77, 79, 0.4);
                        font-size: 11px;
                        font-weight: 700;
                        padding: 2px 7px;
                        border-radius: 6px;
                        min-height: 20px;
                    """)
                elif diff.total_seconds() < 3600:
                    mins_left = max(1, int(diff.total_seconds() // 60))
                    time_badge = QLabel(f"⏳ 仅剩 {mins_left}分钟 · {due}")
                    time_badge.setStyleSheet("""
                        color: #FBBF24;
                        background: rgba(251, 191, 36, 0.2);
                        border: 1px solid rgba(251, 191, 36, 0.4);
                        font-size: 11px;
                        font-weight: 700;
                        padding: 2px 7px;
                        border-radius: 6px;
                        min-height: 20px;
                    """)
                else:
                    time_badge = QLabel(f"⏰ {due}")
                    time_badge.setStyleSheet("""
                        color: #38BDF8;
                        background: rgba(56, 189, 248, 0.15);
                        border: 1px solid rgba(56, 189, 248, 0.3);
                        font-size: 11px;
                        font-weight: 700;
                        padding: 2px 7px;
                        border-radius: 6px;
                        min-height: 20px;
                    """)
                meta_row.addWidget(time_badge)
            except Exception:
                pass

        # Recurrence badge
        rep_desc = format_repeat_display(self.todo)
        if rep_desc:
            rep_badge = QLabel(rep_desc)
            rep_badge.setStyleSheet("""
                color: #34D399;
                background-color: rgba(52, 211, 153, 0.18);
                border: 1px solid rgba(52, 211, 153, 0.35);
                font-size: 11px;
                font-weight: 700;
                padding: 2px 7px;
                border-radius: 6px;
                min-height: 20px;
            """)
            meta_row.addWidget(rep_badge)

        meta_row.addStretch()
        info_layout.addLayout(meta_row)

        header_layout.addLayout(info_layout, 1)

        # 3. Right Expand Indicator Pill
        self.expand_btn = QPushButton("展开 ∨")
        self.expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(56, 189, 248, 0.18);
                color: #38BDF8;
                border-color: rgba(56, 189, 248, 0.4);
            }
        """)
        self.expand_btn.clicked.connect(self.toggle_expanded)
        header_layout.addWidget(self.expand_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        card_layout.addWidget(header_widget)

        # --- 2. Expanded Detail Panel (Hidden by default) ---
        self.detail_widget = QWidget()
        self.detail_widget.setVisible(False)
        detail_layout = QVBoxLayout(self.detail_widget)
        detail_layout.setContentsMargins(0, 4, 0, 0)
        detail_layout.setSpacing(8)

        # Details Box
        details_box = QFrame()
        details_box.setStyleSheet("""
            QFrame {
                background: rgba(0, 0, 0, 0.28);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
        """)
        box_layout = QVBoxLayout(details_box)
        box_layout.setContentsMargins(10, 8, 10, 8)
        box_layout.setSpacing(6)

        # Row 1: Attributes
        attr_row = QHBoxLayout()
        attr_row.setSpacing(12)

        cat_lbl = QLabel(f"📁 分类: {cat}")
        cat_lbl.setStyleSheet("color: #CBD5E1; font-size: 11px; font-weight: 600;")
        attr_row.addWidget(cat_lbl)

        due_lbl = QLabel(f"⏰ 截止: {due if due else '无指定时间'}")
        due_lbl.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 600;")
        attr_row.addWidget(due_lbl)

        prio_detail_lbl = QLabel(f"📌 级别: {prio_info['label']}")
        prio_detail_lbl.setStyleSheet(f"color: {prio_info['color']}; font-size: 11px; font-weight: 700;")
        attr_row.addWidget(prio_detail_lbl)

        attr_row.addStretch()
        box_layout.addLayout(attr_row)

        if rep_desc:
            rep_row = QHBoxLayout()
            rep_full_lbl = QLabel(f"🔁 重复周期: {rep_desc}")
            rep_full_lbl.setStyleSheet("color: #34D399; font-size: 11px; font-weight: 600;")
            rep_row.addWidget(rep_full_lbl)
            rep_row.addStretch()
            box_layout.addLayout(rep_row)

        # Row 2: Full Note / Description if present
        desc = self.todo.get("description", "").strip()
        if desc:
            desc_lbl = QLabel(f"📝 待办备注: {desc}")
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet("color: #CBD5E1; font-size: 11px; line-height: 1.4;")
            box_layout.addWidget(desc_lbl)

        detail_layout.addWidget(details_box)

        # Dedicated Action Button Row
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 4, 0, 0)
        action_row.setSpacing(8)

        # Complete / Reopen button
        status_action_btn = QPushButton("↺ 设为待办" if is_completed else "✓ 标记完成")
        status_action_btn.setFixedHeight(30)
        status_action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        status_action_btn.setStyleSheet("""
            QPushButton {
                background: rgba(48, 209, 88, 0.2);
                color: #30D158;
                border: 1px solid rgba(48, 209, 88, 0.45);
                border-radius: 6px;
                padding: 4px 14px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #30D158;
                color: #FFFFFF;
            }
        """)
        status_action_btn.clicked.connect(lambda: self.toggled.emit(self.todo["id"]))
        action_row.addWidget(status_action_btn)

        action_row.addStretch()

        # Edit button
        edit_btn = QPushButton("✏️ 修改")
        edit_btn.setFixedHeight(30)
        edit_btn.setToolTip("编辑待办标题、时间与分类")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(56, 189, 248, 0.18);
                color: #38BDF8;
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #38BDF8;
                color: #000000;
            }
        """)
        edit_btn.clicked.connect(lambda: self.edited.emit(self.todo["id"]))
        action_row.addWidget(edit_btn)

        # Delete button
        del_btn = QPushButton("🗑️ 删除")
        del_btn.setFixedHeight(30)
        del_btn.setToolTip("删除此待办事项")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.18);
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #EF4444;
                color: #FFFFFF;
            }
        """)
        del_btn.clicked.connect(lambda: self.deleted.emit(self.todo["id"]))
        action_row.addWidget(del_btn)

        detail_layout.addLayout(action_row)
        card_layout.addWidget(self.detail_widget)

        self._update_card_style()

    def toggle_expanded(self):
        self.set_expanded(not self.is_expanded)

    def set_expanded(self, expanded: bool):
        if self.is_expanded == expanded:
            return
        self.is_expanded = expanded
        self.detail_widget.setVisible(expanded)
        self.expand_btn.setText("收起 ∧" if expanded else "展开 ∨")
        self._update_card_style()
        self.expanded_changed.emit(self.todo["id"], expanded)

    def _update_card_style(self):
        if self.is_expanded:
            self.setStyleSheet(f"""
                QFrame#TaskCard {{
                    background-color: #1A2135;
                    border: 1.5px solid #38BDF8;
                    border-radius: 12px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#TaskCard {{
                    background-color: {THEME['bg_card']};
                    border: 1px solid {THEME['border_light']};
                    border-radius: 12px;
                }}
                QFrame#TaskCard:hover {{
                    border-color: rgba(56, 189, 248, 0.4);
                    background-color: {THEME['bg_card_hover']};
                }}
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            child = self.childAt(pos)
            if child and child not in (self, self.expand_btn):
                if isinstance(child, QCheckBox):
                    super().mousePressEvent(event)
                    return
                if self.is_expanded and isinstance(child, (QPushButton, QComboBox)):
                    super().mousePressEvent(event)
                    return
            self.toggle_expanded()
            event.accept()
            return
        super().mousePressEvent(event)

    def _apply_title_style(self):
        if self.todo.get("completed"):
            self.title_lbl.setStyleSheet("color: #64748B; font-size: 14px; text-decoration: line-through; min-height: 24px; padding: 1px 0px;")
        else:
            self.title_lbl.setStyleSheet("color: #FFFFFF; font-weight: 600; font-size: 14px; text-decoration: none; min-height: 24px; padding: 1px 0px;")


class TodoTab(QWidget):
    todos_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_status_filter = "all"
        self.current_category_filter = "全部"
        self.search_query = ""

        self._init_ui()
        self.load_todos()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(8)

        # 1. Add Task Section (Compact by default, expandable on demand)
        add_box = QFrame()
        add_box.setStyleSheet(f"""
            background-color: {THEME['bg_card']};
            border-radius: 12px;
            border: 1px solid {THEME['border_light']};
            padding: 2px;
        """)
        add_layout = QVBoxLayout(add_box)
        add_layout.setContentsMargins(10, 8, 10, 8)
        add_layout.setSpacing(6)

        # Row 1: Title input & Add button
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("➕ 输入待办事项... (输入如“明天15:30开会”可智能识别)")
        self.input_edit.setStyleSheet("font-size: 13px; font-weight: 500; color: #FFFFFF;")
        self.input_edit.returnPressed.connect(self._on_add_task)
        self.input_edit.textChanged.connect(self._on_title_typed)
        input_row.addWidget(self.input_edit, 1)

        self.add_btn = QPushButton("添加待办")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_task)
        input_row.addWidget(self.add_btn)

        add_layout.addLayout(input_row)

        # Row 2: Priority + Category + Time Toggle Button
        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)
        meta_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        meta_row.addWidget(QLabel("优先级:"))
        self.prio_combo = QComboBox()
        self.prio_combo.addItem("🟡 重要", "medium")
        self.prio_combo.addItem("🔴 紧急", "high")
        self.prio_combo.addItem("🟢 普通", "low")
        self.prio_combo.setFixedWidth(85)
        meta_row.addWidget(self.prio_combo)

        meta_row.addWidget(QLabel("分类:"))
        self.cat_combo = QComboBox()
        for cat in CATEGORIES:
            self.cat_combo.addItem(cat, cat)
        self.cat_combo.setFixedWidth(75)
        meta_row.addWidget(self.cat_combo)

        meta_row.addStretch()

        # Toggle Button for Time & Recurrence Panel
        self.toggle_time_btn = QPushButton("⏰ 设置提醒 ▾")
        self.toggle_time_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_time_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #CBD5E1;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 3px 10px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
                border-color: #38BDF8;
            }
        """)
        self.toggle_time_btn.clicked.connect(self._toggle_time_picker)
        meta_row.addWidget(self.toggle_time_btn)

        add_layout.addLayout(meta_row)

        # Row 3: Friendly Time Picker Component (Hidden by default to give massive space to task list!)
        self.time_picker = FriendlyTimePicker(self)
        self.time_picker.setVisible(False)
        self.time_picker.changed.connect(self._on_picker_changed)
        add_layout.addWidget(self.time_picker)

        main_layout.addWidget(add_box)

        # 2. Search & Status Filter Bar
        filter_box = QHBoxLayout()
        filter_box.setSpacing(6)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 搜索待办...")
        self.search_edit.setFixedHeight(28)
        self.search_edit.textChanged.connect(self._on_search_changed)
        filter_box.addWidget(self.search_edit, 1)

        self.btn_filter_all = QPushButton("全部")
        self.btn_filter_pending = QPushButton("待办")
        self.btn_filter_today = QPushButton("今日")
        self.btn_filter_done = QPushButton("已完成")

        self.status_buttons = {
            "all": self.btn_filter_all,
            "pending": self.btn_filter_pending,
            "today": self.btn_filter_today,
            "completed": self.btn_filter_done,
        }

        for key, btn in self.status_buttons.items():
            btn.setObjectName("FilterTag")
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._set_status_filter(k))
            filter_box.addWidget(btn)

        self._update_filter_button_styles()
        main_layout.addLayout(filter_box)

        # 3. Category Filter Bar (Compact scrollable chips)
        self.cat_scroll = QScrollArea()
        self.cat_scroll.setFixedHeight(30)
        self.cat_scroll.setWidgetResizable(True)
        self.cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cat_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        cat_container = QWidget()
        cat_container.setStyleSheet("background: transparent;")
        cat_filter_row = QHBoxLayout(cat_container)
        cat_filter_row.setContentsMargins(0, 0, 0, 0)
        cat_filter_row.setSpacing(4)

        cat_lbl = QLabel("分类:")
        cat_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        cat_filter_row.addWidget(cat_lbl)

        self.cat_filter_btns = {}
        for cat in ["全部"] + CATEGORIES:
            btn = QPushButton(cat)
            btn.setObjectName("FilterTag")
            btn.setFixedHeight(24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, c=cat: self._set_cat_filter(c))
            cat_filter_row.addWidget(btn)
            self.cat_filter_btns[cat] = btn

        cat_filter_row.addStretch()
        self._update_cat_button_styles()
        self.cat_scroll.setWidget(cat_container)
        main_layout.addWidget(self.cat_scroll)

        # 4. Scrollable List Area (Now gets 380px+ vertical height!)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch()

        self.scroll_area.setWidget(self.list_container)
        main_layout.addWidget(self.scroll_area, 1)

        # 5. Bottom Status Bar
        bottom_bar = QHBoxLayout()
        self.status_summary = QLabel("共 0 项待办")
        self.status_summary.setStyleSheet("color: #CBD5E1; font-size: 12px; font-weight: 600;")
        bottom_bar.addWidget(self.status_summary)

        bottom_bar.addStretch()

        self.clear_done_btn = QPushButton("清空已完成")
        self.clear_done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_done_btn.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #94A3B8;
            background: transparent;
            border: none;
        """)
        self.clear_done_btn.clicked.connect(self._clear_completed)
        bottom_bar.addWidget(self.clear_done_btn)

        main_layout.addLayout(bottom_bar)

    def _toggle_time_picker(self):
        new_vis = not self.time_picker.isVisible()
        self._set_time_picker_visible(new_vis)

    def _set_time_picker_visible(self, visible: bool):
        self.time_picker.setVisible(visible)
        if visible:
            self.toggle_time_btn.setText("⏰ 收起时间面板 ▴")
            self.toggle_time_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(56, 189, 248, 0.2);
                    color: #38BDF8;
                    border: 1px solid #38BDF8;
                    border-radius: 6px;
                    padding: 3px 10px;
                    font-size: 12px;
                    font-weight: 700;
                }
            """)
        else:
            self._update_toggle_btn_text()

    def _on_picker_changed(self):
        if not self.time_picker.isVisible():
            self._update_toggle_btn_text()

    def _update_toggle_btn_text(self):
        if self.time_picker.is_reminder_enabled():
            summary = self.time_picker.get_summary_text()
            self.toggle_time_btn.setText(f"⏰ {summary} ▾")
            self.toggle_time_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(56, 189, 248, 0.15);
                    color: #38BDF8;
                    border: 1px solid rgba(56, 189, 248, 0.4);
                    border-radius: 6px;
                    padding: 3px 10px;
                    font-size: 12px;
                    font-weight: 600;
                }
            """)
        else:
            self.toggle_time_btn.setText("⏰ 设置提醒 ▾")
            self.toggle_time_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    color: #CBD5E1;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 6px;
                    padding: 3px 10px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.15);
                    color: #FFFFFF;
                    border-color: #38BDF8;
                }
            """)

    def _on_title_typed(self, text: str):
        """Auto-detect natural language time and prefill the friendly picker."""
        if not text.strip():
            return
        _, parsed_due, rep_type, rep_days, rep_time = parse_natural_time(text)

        if parsed_due or rep_type != REPEAT_NONE:
            self.time_picker.set_data(parsed_due, rep_type, rep_days, rep_time)
            self.time_picker.enable_cb.setChecked(True)
            self._set_time_picker_visible(True)

    def _on_add_task(self):
        raw_text = self.input_edit.text().strip()
        if not raw_text:
            return

        cleaned_title, parsed_due, parsed_rep, parsed_days, parsed_time = parse_natural_time(raw_text)
        title = cleaned_title if cleaned_title else raw_text

        prio = self.prio_combo.currentData()
        cat = self.cat_combo.currentData()

        due_time = self.time_picker.get_due_time()
        repeat_type = self.time_picker.get_repeat_type()
        repeat_days = self.time_picker.get_repeat_days()
        repeat_time = self.time_picker.get_repeat_time()
        reminder_enabled = self.time_picker.is_reminder_enabled()

        storage.add_todo(
            title=title,
            priority=prio,
            category=cat,
            due_time=due_time,
            reminder_enabled=reminder_enabled,
            repeat_type=repeat_type,
            repeat_days=repeat_days,
            repeat_time=repeat_time
        )

        self.input_edit.clear()
        self.time_picker._setup_defaults()
        self._set_time_picker_visible(False)
        self.load_todos()
        self.todos_changed.emit()

    def _on_search_changed(self, text):
        self.search_query = text.strip().lower()
        self.load_todos()

    def _set_status_filter(self, key):
        self.current_status_filter = key
        self._update_filter_button_styles()
        self.load_todos()

    def _set_cat_filter(self, cat):
        self.current_category_filter = cat
        self._update_cat_button_styles()
        self.load_todos()

    def _update_filter_button_styles(self):
        for key, btn in self.status_buttons.items():
            btn.setProperty("active", "true" if key == self.current_status_filter else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _update_cat_button_styles(self):
        for cat, btn in self.cat_filter_btns.items():
            btn.setProperty("active", "true" if cat == self.current_category_filter else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def load_todos(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        todos = storage.get_todos()
        total_count = len(todos)
        completed_count = sum(1 for t in todos if t.get("completed"))
        pending_count = total_count - completed_count

        self.status_summary.setText(f"待办 {pending_count} 项 · 已完成 {completed_count} 项")

        today_str = datetime.now().strftime("%Y-%m-%d")
        filtered = []
        for t in todos:
            is_comp = t.get("completed", False)
            if self.current_status_filter == "pending" and is_comp:
                continue
            if self.current_status_filter == "completed" and not is_comp:
                continue
            if self.current_status_filter == "today":
                due = t.get("due_time", "")
                if not due.startswith(today_str) and not is_comp:
                    continue

            if self.current_category_filter != "全部" and t.get("category") != self.current_category_filter:
                continue

            if self.search_query:
                title = t.get("title", "").lower()
                desc = t.get("description", "").lower()
                if self.search_query not in title and self.search_query not in desc:
                    continue

            filtered.append(t)

        if not filtered:
            empty_lbl = QLabel("✨ 暂无符合条件的待办事项")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #94A3B8; padding: 40px; font-size: 13px; font-weight: 500;")
            self.list_layout.insertWidget(0, empty_lbl)
            return

        for todo in filtered:
            card = TaskCard(todo)
            card.toggled.connect(self._on_toggle_todo)
            card.edited.connect(self._on_edit_todo)
            card.deleted.connect(self._on_delete_todo)
            card.expanded_changed.connect(self._on_card_expanded)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

    def _on_card_expanded(self, todo_id: str, is_expanded: bool):
        if is_expanded:
            for i in range(self.list_layout.count()):
                item = self.list_layout.itemAt(i)
                w = item.widget() if item else None
                if isinstance(w, TaskCard) and w.todo.get("id") != todo_id:
                    w.set_expanded(False)

    def _on_toggle_todo(self, todo_id: str):
        storage.toggle_todo(todo_id)
        self.load_todos()
        self.todos_changed.emit()

    def _on_edit_todo(self, todo_id: str):
        todos = storage.get_todos()
        todo = next((t for t in todos if t["id"] == todo_id), None)
        if not todo:
            return

        dialog = TodoEditDialog(todo, self.window())
        dialog.raise_()
        dialog.activateWindow()
        if dialog.exec():
            if dialog.updated_data:
                storage.update_todo(todo_id, dialog.updated_data)
                self.load_todos()
                self.todos_changed.emit()

    def _on_delete_todo(self, todo_id: str):
        storage.delete_todo(todo_id)
        self.load_todos()
        self.todos_changed.emit()

    def _clear_completed(self):
        removed = storage.clear_completed()
        if removed > 0:
            self.load_todos()
            self.todos_changed.emit()
