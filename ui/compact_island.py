from datetime import datetime
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QFont, QMouseEvent
from storage import storage, format_repeat_display
from ui.styles import THEME
from ui.screen_utils import clamp_window_to_edges
from ui.components.icons import make_play_icon, make_pause_icon

class CompactIsland(QWidget):
    expand_requested = pyqtSignal()
    play_pause_requested = pyqtSignal()
    next_track_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cpu_pct = 0.0

        # Music status
        self.music_playing = False
        self.music_title = ""

        self._init_ui()

        # Timer to refresh ticker & clock every 1s
        self.ticker_timer = QTimer(self)
        self.ticker_timer.setInterval(1000)
        self.ticker_timer.timeout.connect(self.update_content)
        self.ticker_timer.start()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        # 1. High-Contrast Live Clock Pill (Clear & bold)
        self.clock_pill = QLabel("12:00")
        self.clock_pill.setStyleSheet("""
            font-size: 13px;
            font-weight: 800;
            color: #FFFFFF;
            background: rgba(255, 255, 255, 0.16);
            padding: 3px 8px;
            border-radius: 9px;
            border: 1px solid rgba(255, 255, 255, 0.22);
            letter-spacing: 0.5px;
        """)
        layout.addWidget(self.clock_pill)

        # 2. Dynamic Status Icon (Music / Habit / Alarm / Task)
        self.icon_label = QLabel("📋")
        self.icon_label.setStyleSheet("font-size: 14px; background: transparent;")
        layout.addWidget(self.icon_label)

        # 3. Center High-Contrast Ticker
        self.ticker_label = QLabel("灵动岛准备就绪")
        self.ticker_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 12px;
            font-weight: 600;
            background: transparent;
        """)
        self.ticker_label.setTextFormat(Qt.TextFormat.RichText)
        self.ticker_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.ticker_label, 1)

        # 4. Music Mini Controls (Visible when music is loaded)
        self.mini_play_btn = QPushButton("▶")
        self.mini_play_btn.setFixedSize(22, 22)
        self.mini_play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mini_play_btn.setStyleSheet("""
            QPushButton {
                background: rgba(10, 132, 255, 0.35);
                color: #FFFFFF;
                border: 1px solid #0A84FF;
                border-radius: 11px;
                font-size: 10px;
                padding: 0;
            }
            QPushButton:hover {
                background: #0A84FF;
            }
        """)
        self.mini_play_btn.clicked.connect(self.play_pause_requested.emit)
        self.mini_play_btn.setVisible(False)
        layout.addWidget(self.mini_play_btn)

        # 5. CPU meter badge
        self.cpu_badge = QLabel("⚡ 0%")
        self.cpu_badge.setStyleSheet("""
            color: #38BDF8;
            font-size: 11px;
            font-weight: 700;
            background: rgba(56, 189, 248, 0.15);
            padding: 2px 7px;
            border-radius: 9px;
            border: 1px solid rgba(56, 189, 248, 0.35);
        """)
        layout.addWidget(self.cpu_badge)

        # 6. Todo count badge
        self.badge_label = QLabel("0 待办")
        self.badge_label.setStyleSheet("""
            color: #E2E8F0;
            font-size: 11px;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.12);
            padding: 2px 8px;
            border-radius: 9px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        """)
        layout.addWidget(self.badge_label)

        # 7. Expand indicator arrow
        self.arrow_label = QLabel("⌄")
        self.arrow_label.setStyleSheet("""
            color: #94A3B8;
            font-size: 14px;
            font-weight: bold;
            background: transparent;
        """)
        layout.addWidget(self.arrow_label)

        # Allow smooth click and drag anywhere on the capsule
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        for w in (self.clock_pill, self.icon_label, self.ticker_label,
                  self.cpu_badge, self.badge_label, self.arrow_label):
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._drag_start_pos = None
        self._window_start_pos = None
        self._is_dragging = False

        self.update_content()

    def set_music_status(self, is_playing: bool, track_title: str):
        self.music_playing = is_playing
        self.music_title = track_title
        self.mini_play_btn.setVisible(bool(track_title))
        self.mini_play_btn.setIcon(make_pause_icon(10, "#FFFFFF") if is_playing else make_play_icon(11, "#FFFFFF"))
        self.mini_play_btn.setText("")
        self.mini_play_btn.setToolTip(f"{'点击暂停' if is_playing else '点击播放'}: {track_title}")
        self.update_content()

    def set_cpu_stat(self, cpu_pct: float):
        self.cpu_pct = cpu_pct
        self.cpu_badge.setText(f"⚡ {int(cpu_pct)}%")
        if cpu_pct > 80:
            self.cpu_badge.setStyleSheet("""
                color: #FF4D4F;
                font-size: 11px;
                font-weight: 700;
                background: rgba(255, 77, 79, 0.22);
                padding: 2px 7px;
                border-radius: 9px;
                border: 1px solid #FF4D4F;
            """)
        elif cpu_pct > 50:
            self.cpu_badge.setStyleSheet("""
                color: #FB923C;
                font-size: 11px;
                font-weight: 700;
                background: rgba(251, 146, 60, 0.2);
                padding: 2px 7px;
                border-radius: 9px;
                border: 1px solid #FB923C;
            """)
        else:
            self.cpu_badge.setStyleSheet("""
                color: #38BDF8;
                font-size: 11px;
                font-weight: 700;
                background: rgba(56, 189, 248, 0.15);
                padding: 2px 7px;
                border-radius: 9px;
                border: 1px solid rgba(56, 189, 248, 0.35);
            """)

    def update_content(self):
        now = datetime.now()
        # High contrast clock update
        self.clock_pill.setText(now.strftime("%H:%M"))

        settings = storage.get_settings()
        self.cpu_badge.setVisible(settings.get("compact_show_cpu", True))

        todos = storage.get_todos()
        pending = [t for t in todos if not t.get("completed", False)]
        self.badge_label.setText(f"{len(pending)} 待办")

        # 1. If Music is playing, display dynamic waveform and track title!
        if self.music_playing and self.music_title:
            self.icon_label.setText("🎵")
            title = self.music_title
            if len(title) > 16:
                title = title[:15] + "..."
            self.ticker_label.setText(f"<span style='color: #38BDF8; font-weight: bold;'>正在播放:</span> {title}")
            return

        # 2. Check for active habit reminder (e.g. water drinking)
        next_habit = storage.get_next_habit()
        if next_habit and next_habit.get("next_trigger"):
            h_time = next_habit["next_trigger"].split(" ")[-1]
            now_h = now.strftime("%H:%M")
            if next_habit.get("start_time", "09:00") <= now_h <= next_habit.get("end_time", "18:00"):
                cnt = next_habit.get("today_count", 0)
                tgt = next_habit.get("target_count", 8)
                self.icon_label.setText("💧")
                self.ticker_label.setText(
                    f"<span style='color: #38BDF8; font-weight: bold;'>💧 喝水: {cnt}/{tgt}杯</span> "
                    f"<span style='color: #94A3B8; font-size: 11px;'>下次 {h_time}</span>"
                )
                return

        # 3. Check for active snoozed alarm or urgent alarm
        next_alarm = storage.get_next_alarm()
        if next_alarm and next_alarm.get("snooze_until"):
            self.icon_label.setText("⏳")
            s_time = next_alarm["snooze_until"].split(" ")[-1]
            title = next_alarm.get("title", "")
            if len(title) > 13:
                title = title[:12] + "..."
            self.ticker_label.setText(
                f"<span style='color: #FBBF24; font-weight: bold; background: rgba(251, 191, 36, 0.2); padding: 1px 5px; border-radius: 4px;'>延时至 {s_time}</span> "
                f"<span style='color: #FFFFFF;'>{title}</span>"
            )
            return

        # 4. Next pending task (with high contrast time highlight)
        next_todo = storage.get_next_pending()
        if next_todo:
            self.icon_label.setText("📋")
            time_part = ""
            if next_todo.get("due_time"):
                t_str = next_todo['due_time'].split(' ')[-1]
                time_part = f"<span style='color: #FBBF24; font-weight: bold; background: rgba(251, 191, 36, 0.2); padding: 1px 5px; border-radius: 4px;'>{t_str}</span> "

            title = next_todo.get("title", "")
            if len(title) > 14:
                title = title[:13] + "..."
            self.ticker_label.setText(f"{time_part}<span style='color: #FFFFFF;'>{title}</span>")
        elif next_alarm and next_alarm.get("next_trigger"):
            self.icon_label.setText("⏰")
            trig_time = next_alarm["next_trigger"].split(" ")[-1]
            title = next_alarm.get("title", "")
            if len(title) > 13:
                title = title[:12] + "..."
            self.ticker_label.setText(
                f"<span style='color: #38BDF8; font-weight: bold; background: rgba(56, 189, 248, 0.2); padding: 1px 5px; border-radius: 4px;'>闹钟 {trig_time}</span> "
                f"<span style='color: #FFFFFF;'>{title}</span>"
            )
        else:
            self.icon_label.setText("✨")
            self.ticker_label.setText("<span style='color: #34D399; font-weight: bold;'>今日待办已全部完成！</span>")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicked on mini play button
            child = self.childAt(event.pos())
            if child == self.mini_play_btn:
                super().mousePressEvent(event)
                return

            self._drag_start_pos = event.globalPosition().toPoint()
            self._window_start_pos = self.window().pos()
            self._is_dragging = False
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_start_pos and (event.buttons() & Qt.MouseButton.LeftButton):
            cursor_pos = event.globalPosition().toPoint()
            delta = cursor_pos - self._drag_start_pos
            if not self._is_dragging:
                if delta.manhattanLength() >= 5:
                    self._is_dragging = True
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)

            if self._is_dragging:
                win = self.window()
                new_pos = self._window_start_pos + delta
                clamped_pos = clamp_window_to_edges(
                    new_pos, win.width(), win.height(), cursor_pos, snap_distance=16, strict_contain=False
                )
                win.move(clamped_pos)
                event.accept()
                return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            if self._is_dragging:
                # Finished dragging! Ensure strictly inside active screen edges & save position
                win = self.window()
                cursor_pos = event.globalPosition().toPoint()
                final_pos = clamp_window_to_edges(
                    win.pos(), win.width(), win.height(), cursor_pos, strict_contain=True
                )
                win.move(final_pos)
                storage.update_setting("position_mode", "custom")
                storage.update_setting("custom_pos_x", final_pos.x())
                storage.update_setting("custom_pos_y", final_pos.y())
                self._is_dragging = False
                self._drag_start_pos = None
                event.accept()
                return
            else:
                # Simple click without dragging! Expand to dashboard
                self._drag_start_pos = None
                child = self.childAt(event.pos())
                if child == self.mini_play_btn:
                    super().mouseReleaseEvent(event)
                    return
                self.expand_requested.emit()
                event.accept()
                return

        super().mouseReleaseEvent(event)
