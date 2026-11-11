from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import (
    Qt, QRect, QPropertyAnimation, QEasingCurve, QPoint, QTimer, pyqtSignal
)
from PyQt6.QtGui import QColor, QKeyEvent, QMouseEvent, QResizeEvent

from config import (
    SHADOW_MARGIN,
    COMPACT_WIDTH, COMPACT_HEIGHT, COMPACT_RADIUS,
    ALERT_WIDTH, ALERT_HEIGHT, ALERT_RADIUS,
    EXPANDED_WIDTH, EXPANDED_HEIGHT, EXPANDED_RADIUS
)
from storage import storage
from ui.styles import THEME, MAIN_STYLE
from ui.compact_island import CompactIsland
from ui.alert_island import AlertIsland
from ui.dashboard import Dashboard
from ui.screen_utils import get_screen_at_point, clamp_window_to_edges
from pomodoro_service import PomodoroService
from system_monitor import SystemMonitor
from music_service import MusicService

class IslandWindow(QWidget):
    STATE_COMPACT = "compact"
    STATE_ALERT = "alert"
    STATE_EXPANDED = "expanded"

    def __init__(self, pomodoro_service: PomodoroService, system_monitor: SystemMonitor, music_service: MusicService, parent=None):
        super().__init__(parent)
        self.pomodoro_service = pomodoro_service
        self.system_monitor = system_monitor
        self.music_service = music_service

        self.state = self.STATE_COMPACT
        self.drag_position = None
        self.is_dragging = False

        self._init_window()
        self._init_ui()
        self._setup_animation()
        self._setup_mouse_leave_timer()
        self._setup_service_connections()

        # Initial layout position
        self.reposition(storage.get_settings().get("position_mode", "top_center"), animate=False)

    def _init_window(self):
        # Frameless, Always on Top, Tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(MAIN_STYLE)

    def _init_ui(self):
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(SHADOW_MARGIN, SHADOW_MARGIN, SHADOW_MARGIN, SHADOW_MARGIN)

        self.container = QWidget(self)
        self.container.setObjectName("IslandContainer")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)

        # Drop Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 190))
        shadow.setOffset(0, 8)
        self.container.setGraphicsEffect(shadow)

        # 1. Compact View
        self.compact_view = CompactIsland(self)
        self.compact_view.expand_requested.connect(self.expand_to_dashboard)
        self.compact_view.play_pause_requested.connect(self.music_service.toggle_play)

        # 2. Alert View
        self.alert_view = AlertIsland(self)
        self.alert_view.action_dismissed.connect(self.collapse_to_compact)
        self.alert_view.action_completed.connect(self._on_alert_action)
        self.alert_view.action_snoozed.connect(self._on_alert_action)

        # 3. Dashboard View
        self.dashboard_view = Dashboard(self.pomodoro_service, self.system_monitor, self.music_service, self)
        self.dashboard_view.collapse_requested.connect(self.collapse_to_compact)
        self.dashboard_view.todos_changed.connect(self.compact_view.update_content)
        self.dashboard_view.reposition_requested.connect(lambda mode: self.reposition(mode, animate=True))

        self.container_layout.addWidget(self.compact_view)
        self.container_layout.addWidget(self.alert_view)
        self.container_layout.addWidget(self.dashboard_view)

        master_layout.addWidget(self.container)

        self._show_state_widget(self.STATE_COMPACT)

    def _setup_animation(self):
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(320)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _setup_mouse_leave_timer(self):
        self.leave_timer = QTimer(self)
        self.leave_timer.setSingleShot(True)
        self.leave_timer.setInterval(3000)
        self.leave_timer.timeout.connect(self._on_auto_collapse)

    def _setup_service_connections(self):
        # Pomodoro updates
        self.pomodoro_service.tick.connect(
            lambda rem, tot, mode: self.compact_view.set_pomodoro_status(rem, tot, mode, self.pomodoro_service.is_running)
        )
        self.pomodoro_service.state_changed.connect(
            lambda running: self.compact_view.set_pomodoro_status(
                self.pomodoro_service.remaining_seconds,
                self.pomodoro_service.total_seconds,
                self.pomodoro_service.current_mode,
                running
            )
        )

        # System monitor updates
        self.system_monitor.stats_updated.connect(
            lambda stats: self.compact_view.set_cpu_stat(stats.get("cpu", 0.0))
        )

        # Music updates
        def update_compact_music():
            title = self.music_service.current_track.get("title", "") if self.music_service.current_track else ""
            self.compact_view.set_music_status(self.music_service.is_playing, title)

        self.music_service.playback_state_changed.connect(lambda is_p: update_compact_music())
        self.music_service.track_changed.connect(lambda t: update_compact_music())

    def _show_state_widget(self, state: str):
        self.state = state
        self.compact_view.setVisible(state == self.STATE_COMPACT)
        self.alert_view.setVisible(state == self.STATE_ALERT)
        self.dashboard_view.setVisible(state == self.STATE_EXPANDED)

        radius = COMPACT_RADIUS if state == self.STATE_COMPACT else (
            ALERT_RADIUS if state == self.STATE_ALERT else EXPANDED_RADIUS
        )
        self.container.setStyleSheet(f"""
            #IslandContainer {{
                background-color: {THEME['bg_island']};
                border: 1px solid {THEME['border_light']};
                border-radius: {radius}px;
            }}
        """)

    def get_target_geometry(self, state: str, mode: str = None) -> QRect:
        if mode is None:
            mode = storage.get_settings().get("position_mode", "top_center")

        margin = SHADOW_MARGIN
        compact_content_w = COMPACT_WIDTH
        if hasattr(self, "compact_view") and self.compact_view:
            hint_w = self.compact_view.sizeHint().width()
            if hint_w > compact_content_w:
                compact_content_w = hint_w
        compact_w = compact_content_w + 2 * margin

        if state == self.STATE_COMPACT:
            w, h = compact_w, COMPACT_HEIGHT + 2 * margin
        elif state == self.STATE_ALERT:
            w, h = ALERT_WIDTH + 2 * margin, ALERT_HEIGHT + 2 * margin
        else:
            w, h = EXPANDED_WIDTH + 2 * margin, EXPANDED_HEIGHT + 2 * margin

        if mode == "custom":
            settings = storage.get_settings()
            saved_x = settings.get("custom_pos_x")
            saved_y = settings.get("custom_pos_y")
            if saved_x is not None and saved_x != -1:
                center_x = saved_x + compact_w // 2
                center_y = saved_y + 20
                screen = get_screen_at_point(QPoint(center_x, center_y))
                s_geom = screen.geometry()
                s_avail = screen.availableGeometry()

                x = center_x - w // 2
                y = saved_y

                # Clamp visual pill to screen edges (allowing 0px gap to borders)
                min_x = s_geom.left() - margin
                max_x = s_geom.right() + 1 - w + margin
                min_y = s_geom.top() - margin
                max_y = max(min_y, s_avail.bottom() + 1 - h + margin)

                x = max(min_x, min(max_x, x))
                y = max(min_y, min(max_y, y))
                return QRect(x, y, w, h)

        # Fallback or preset modes (top_center, top_left, top_right)
        win_center = self.geometry().center()
        screen = get_screen_at_point(win_center)
        s_geom = screen.geometry()
        s_avail = screen.availableGeometry()

        # Preset Y: visual pill is 12px below screen top
        preset_y = s_geom.top() + 12 - margin

        if mode == "top_left":
            x = s_geom.left() + 30 - margin
            y = preset_y
        elif mode == "top_right":
            x = s_geom.right() + 1 - w - 30 + margin
            y = preset_y
        else:  # top_center
            x = s_geom.left() + (s_geom.width() - w) // 2
            y = preset_y

        min_x = s_geom.left() - margin
        max_x = s_geom.right() + 1 - w + margin
        min_y = s_geom.top() - margin
        max_y = max(min_y, s_avail.bottom() + 1 - h + margin)

        x = max(min_x, min(max_x, x))
        y = max(min_y, min(max_y, y))

        return QRect(x, y, w, h)

    def morph_to(self, new_state: str):
        target_geom = self.get_target_geometry(new_state)

        if self.state == new_state and self.geometry() == target_geom:
            return

        self._show_state_widget(new_state)

        self.anim.stop()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(target_geom)
        self.anim.start()

    def expand_to_dashboard(self):
        self.dashboard_view.todo_tab.load_todos()
        self.morph_to(self.STATE_EXPANDED)

    def collapse_to_compact(self):
        if hasattr(self, "_active_reminder_dlg") and self._active_reminder_dlg:
            try:
                self._active_reminder_dlg.close()
            except Exception:
                pass
            self._active_reminder_dlg = None
        self.compact_view.update_content()
        self.morph_to(self.STATE_COMPACT)

    def show_alert(self, todo: dict):
        # 1. Morph capsule to AlertIsland banner
        self.alert_view.trigger_alert(todo)
        self.morph_to(self.STATE_ALERT)
        # 2. Open dedicated always-on-top, glowing Reminder Dialog popup
        self.show_reminder_popup(todo)

    def show_reminder_popup(self, todo: dict):
        from ui.components.reminder_dialog import ReminderDialog
        if hasattr(self, "_active_reminder_dlg") and self._active_reminder_dlg:
            try:
                self._active_reminder_dlg.close()
            except Exception:
                pass
        self._active_reminder_dlg = ReminderDialog(todo, None)
        self._active_reminder_dlg.action_completed.connect(self._on_alert_action)
        self._active_reminder_dlg.action_snoozed.connect(self._on_alert_action)
        self._active_reminder_dlg.action_dismissed.connect(self.collapse_to_compact)
        self._active_reminder_dlg.show()
        self._active_reminder_dlg.raise_()
        self._active_reminder_dlg.activateWindow()

    def _on_alert_action(self, todo_id: str = ""):
        if hasattr(self, "_active_reminder_dlg") and self._active_reminder_dlg:
            try:
                self._active_reminder_dlg.close()
            except Exception:
                pass
            self._active_reminder_dlg = None
        self.compact_view.update_content()
        self.dashboard_view.todo_tab.load_todos()
        self.collapse_to_compact()

    def reposition(self, mode: str, animate: bool = True):
        target_geom = self.get_target_geometry(self.state, mode)
        if animate:
            self.anim.stop()
            self.anim.setStartValue(self.geometry())
            self.anim.setEndValue(target_geom)
            self.anim.start()
        else:
            self.setGeometry(target_geom)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            settings = storage.get_settings()
            if settings.get("position_mode") == "custom" or self.state == self.STATE_COMPACT:
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.is_dragging = True
                event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_dragging and self.drag_position:
            cursor_pos = event.globalPosition().toPoint()
            new_pos = cursor_pos - self.drag_position
            clamped_pos = clamp_window_to_edges(
                new_pos, self.width(), self.height(), cursor_pos, snap_distance=16, strict_contain=False
            )
            self.move(clamped_pos)
            if storage.get_settings().get("position_mode") == "custom":
                storage.update_setting("custom_pos_x", clamped_pos.x())
                storage.update_setting("custom_pos_y", clamped_pos.y())
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.is_dragging:
            cursor_pos = event.globalPosition().toPoint()
            final_pos = clamp_window_to_edges(
                self.pos(), self.width(), self.height(), cursor_pos, strict_contain=True
            )
            self.move(final_pos)
            if storage.get_settings().get("position_mode") == "custom":
                storage.update_setting("custom_pos_x", final_pos.x())
                storage.update_setting("custom_pos_y", final_pos.y())
            self.is_dragging = False
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        # Protect against runaway mixed-DPI OS scaling loops when dragging across monitors
        if self.state == self.STATE_COMPACT and self.anim.state() != QPropertyAnimation.State.Running:
            expected = self.get_target_geometry(self.STATE_COMPACT)
            if self.height() != expected.height() or self.width() > expected.width() + 30 or self.width() < expected.width() - 30:
                self.resize(expected.width(), expected.height())

    def enterEvent(self, event):
        self.leave_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        settings = storage.get_settings()
        if (self.state == self.STATE_EXPANDED
                and settings.get("auto_collapse", False)
                and not self.dashboard_view.is_pinned):
            self.leave_timer.start()
        super().leaveEvent(event)

    def _on_auto_collapse(self):
        if self.state == self.STATE_EXPANDED and not self.dashboard_view.is_pinned:
            self.collapse_to_compact()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            if self.state != self.STATE_COMPACT:
                self.collapse_to_compact()
                event.accept()
                return
        super().keyPressEvent(event)
