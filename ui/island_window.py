import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsDropShadowEffect, QApplication, QDialog
)
from PyQt6.QtCore import (
    Qt, QRect, QPropertyAnimation, QEasingCurve, QPoint, QTimer, pyqtSignal
)
from PyQt6.QtGui import QColor, QKeyEvent, QMouseEvent, QResizeEvent, QCursor

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
from system_monitor import SystemMonitor
from music_service import MusicService

class IslandWindow(QWidget):
    STATE_COMPACT = "compact"
    STATE_ALERT = "alert"
    STATE_EXPANDED = "expanded"

    def __init__(self, system_monitor: SystemMonitor, music_service: MusicService, parent=None):
        super().__init__(parent)
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

        # Register for Windows Session Lock/Unlock Notifications
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                ctypes.windll.wtsapi32.WTSRegisterSessionNotification(hwnd, 0)
            except Exception:
                pass

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
        self.dashboard_view = Dashboard(self.system_monitor, self.music_service, self)
        self.dashboard_view.setFixedWidth(EXPANDED_WIDTH)
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
        # System monitor updates
        self.system_monitor.stats_updated.connect(
            lambda stats: self.compact_view.set_cpu_stat(stats.get("cpu", 0.0))
        )

        # Music updates
        def update_compact_music():
            title = self.music_service.current_track.get("title", "") if self.music_service.current_track else ""
            cover_bytes = self.music_service.get_current_cover_bytes()
            self.compact_view.set_music_status(self.music_service.is_playing, title, cover_bytes)

        self.music_service.playback_state_changed.connect(lambda is_p: update_compact_music())
        self.music_service.track_changed.connect(lambda t: update_compact_music())
        self.music_service.cover_changed.connect(lambda b: update_compact_music())

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
        compact_h = COMPACT_HEIGHT + 2 * margin

        exp_content_w = EXPANDED_WIDTH
        exp_content_h = EXPANDED_HEIGHT
        if hasattr(self, "dashboard_view") and self.dashboard_view:
            exp_min_h = self.dashboard_view.minimumSizeHint().height()
            if exp_min_h > exp_content_h:
                exp_content_h = exp_min_h
        exp_w = exp_content_w + 2 * margin
        exp_h = exp_content_h + 2 * margin

        if state == self.STATE_COMPACT:
            w, h = compact_w, compact_h
        elif state == self.STATE_ALERT:
            w, h = ALERT_WIDTH + 2 * margin, ALERT_HEIGHT + 2 * margin
        else:
            w, h = exp_w, exp_h

        if mode == "custom":
            settings = storage.get_settings()
            saved_x = settings.get("custom_pos_x")
            saved_y = settings.get("custom_pos_y")
            if saved_x is not None and saved_x != -1:
                screen = get_screen_at_point(QPoint(saved_x + margin + 10, saved_y + margin + 10))
                s_geom = screen.geometry()
                s_avail = screen.availableGeometry()

                # Horizontal positioning:
                # If placed in the right half of the screen, anchor to the capsule's right edge!
                # This ensures that when expanding/collapsing on the right side of the screen,
                # the window expands to the left and collapses back to the exact right edge without shifting.
                if (saved_x + compact_w // 2) > (s_geom.left() + s_geom.width() // 2):
                    x = saved_x + compact_w - w
                else:
                    x = saved_x

                # Vertical positioning:
                # If placed in the bottom half of the screen, expand upward from the capsule's bottom edge!
                # This ensures the capsule stays firmly in place without jumping to the top of screen.
                if (saved_y + compact_h // 2) > (s_geom.top() + s_geom.height() // 2) and state != self.STATE_COMPACT:
                    y = saved_y + compact_h - h
                else:
                    y = saved_y

                # Clamp visual window to stay strictly within active screen boundaries
                min_x = s_geom.left() - margin
                max_x = s_geom.right() + 1 - w + margin
                min_y = s_geom.top() - margin

                max_screen_y = s_geom.bottom() + 1 - h + margin
                max_avail_y = max(min_y, s_avail.bottom() + 1 - h + margin)
                # If capsule itself was placed below available work area (e.g. in taskbar zone), allow window to touch screen bottom
                if (saved_y + compact_h - margin) > s_avail.bottom() or state == self.STATE_COMPACT:
                    max_y = max_screen_y
                else:
                    max_y = max_avail_y

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
        # If user is interacting with an active reminder popup dialog, do not forcefully kill it
        if hasattr(self, "_active_reminder_dlg") and self._active_reminder_dlg:
            if not self._active_reminder_dlg.isVisible():
                self._active_reminder_dlg = None
            else:
                # Dialog is still being interacted with by user; only morph main island back to compact
                self.compact_view.update_content()
                self.morph_to(self.STATE_COMPACT)
                return

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
        # Cancel alert banner auto_dismiss_timer so it doesn't fire auto_snooze after user handled popup!
        if hasattr(self, "alert_view") and self.alert_view:
            self.alert_view.auto_dismiss_timer.stop()

        if hasattr(self, "_active_reminder_dlg") and self._active_reminder_dlg:
            try:
                self._active_reminder_dlg.close()
            except Exception:
                pass
            self._active_reminder_dlg = None
        self.compact_view.update_content()
        self.dashboard_view.todo_tab.load_todos()
        if hasattr(self.dashboard_view, "alarm_tab"):
            self.dashboard_view.alarm_tab.load_alarms()
        if hasattr(self.dashboard_view, "habit_tab"):
            self.dashboard_view.habit_tab.load_habits()
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
            self.resize(target_geom.size())

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Allow dragging in COMPACT mode anywhere on capsule
            # In EXPANDED mode, allow dragging exclusively on the top header bar (Y < 75px)
            can_drag = (self.state == self.STATE_COMPACT) or (self.state == self.STATE_EXPANDED and event.position().y() <= 75)
            if can_drag:
                self.drag_start_pos = event.globalPosition().toPoint()
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.is_dragging = False
                event.accept()
                return
        super().mousePressEvent(event)

    def _save_dragged_position(self, final_pos: QPoint):
        margin = SHADOW_MARGIN
        compact_content_w = COMPACT_WIDTH
        if hasattr(self, "compact_view") and self.compact_view:
            hint_w = self.compact_view.sizeHint().width()
            if hint_w > compact_content_w:
                compact_content_w = hint_w
        compact_w = compact_content_w + 2 * margin
        compact_h = COMPACT_HEIGHT + 2 * margin

        screen = get_screen_at_point(QPoint(final_pos.x() + margin + 10, final_pos.y() + margin + 10))
        s_geom = screen.geometry()

        save_x = final_pos.x()
        save_y = final_pos.y()

        # If user dragged the EXPANDED window, convert anchors back to compact capsule state
        if self.state == self.STATE_EXPANDED:
            if (final_pos.x() + self.width() // 2) > (s_geom.left() + s_geom.width() // 2):
                save_x = final_pos.x() + self.width() - compact_w
            if (final_pos.y() + self.height() // 2) > (s_geom.top() + s_geom.height() // 2):
                save_y = final_pos.y() + self.height() - compact_h

        storage.update_setting("position_mode", "custom")
        storage.update_setting("custom_pos_x", save_x)
        storage.update_setting("custom_pos_y", save_y)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.drag_position and (event.buttons() & Qt.MouseButton.LeftButton):
            cursor_pos = event.globalPosition().toPoint()
            if not self.is_dragging and hasattr(self, "drag_start_pos") and self.drag_start_pos:
                delta = cursor_pos - self.drag_start_pos
                if delta.manhattanLength() >= 5:
                    self.is_dragging = True

            if self.is_dragging:
                new_pos = cursor_pos - self.drag_position
                clamped_pos = clamp_window_to_edges(
                    new_pos, self.width(), self.height(), cursor_pos, snap_distance=16, strict_contain=False
                )
                self.move(clamped_pos)
                self._save_dragged_position(clamped_pos)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_dragging:
                cursor_pos = event.globalPosition().toPoint()
                final_pos = clamp_window_to_edges(
                    self.pos(), self.width(), self.height(), cursor_pos, strict_contain=True
                )
                self.move(final_pos)
                self._save_dragged_position(final_pos)
                self.is_dragging = False
                self.drag_position = None
                self.drag_start_pos = None
                event.accept()
                return
            self.is_dragging = False
            self.drag_position = None
            self.drag_start_pos = None
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        # Protect against runaway mixed-DPI OS scaling loops when dragging across monitors
        if self.anim.state() != QPropertyAnimation.State.Running:
            if self.state == self.STATE_COMPACT:
                expected = self.get_target_geometry(self.STATE_COMPACT)
                if self.height() != expected.height() or self.width() > expected.width() + 30 or self.width() < expected.width() - 30:
                    self.resize(expected.width(), expected.height())
            elif self.state == self.STATE_EXPANDED:
                expected = self.get_target_geometry(self.STATE_EXPANDED)
                if self.width() > expected.width():
                    self.resize(expected.width(), self.height())

    def enterEvent(self, event):
        self.leave_timer.stop()
        super().enterEvent(event)

    def _is_cursor_over_island_or_dialogs(self) -> bool:
        cursor_pos = QCursor.pos()
        for w in QApplication.topLevelWidgets():
            if w.isVisible() and w.frameGeometry().contains(cursor_pos):
                return True
        return False

    def _has_visible_dialogs(self) -> bool:
        for w in QApplication.topLevelWidgets():
            if isinstance(w, QDialog) and w.isVisible():
                return True
        return False

    def leaveEvent(self, event):
        settings = storage.get_settings()
        if (self.state == self.STATE_EXPANDED
                and settings.get("auto_collapse", False)
                and not self.dashboard_view.is_pinned):
            # If an edit dialog or reminder popup is open, or cursor is still on an island dialog, do not collapse
            if not self._has_visible_dialogs() and not self._is_cursor_over_island_or_dialogs():
                self.leave_timer.start()
        super().leaveEvent(event)

    def _on_auto_collapse(self):
        if self.state == self.STATE_EXPANDED and not self.dashboard_view.is_pinned:
            if self._has_visible_dialogs() or self._is_cursor_over_island_or_dialogs():
                return
            self.collapse_to_compact()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            if self.state != self.STATE_COMPACT:
                self.collapse_to_compact()
                event.accept()
                return
        super().keyPressEvent(event)

    def set_reminder_service(self, service):
        self.reminder_service = service

    def nativeEvent(self, eventType, message):
        if eventType == b"windows_generic_MSG" and sys.platform == "win32":
            try:
                import ctypes
                import ctypes.wintypes
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == 0x02B1:  # WM_WTSSESSION_CHANGE
                    # WTS_SESSION_LOCK (0x7) or WTS_SESSION_LOGOFF (0x6)
                    if msg.wParam in (0x7, 0x6):
                        if hasattr(self, "reminder_service") and self.reminder_service:
                            self.reminder_service.set_screen_locked(True)
                        if hasattr(self, "_active_reminder_dlg") and self._active_reminder_dlg:
                            try:
                                self._active_reminder_dlg._on_auto_timeout()
                            except Exception:
                                pass
                    # WTS_SESSION_UNLOCK (0x8) or WTS_SESSION_LOGON (0x5)
                    elif msg.wParam in (0x8, 0x5):
                        if hasattr(self, "reminder_service") and self.reminder_service:
                            self.reminder_service.set_screen_locked(False)
                            self.reminder_service._check_reminders()
            except Exception:
                pass
        return False, 0

    def closeEvent(self, event):
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                ctypes.windll.wtsapi32.WTSUnRegisterSessionNotification(hwnd)
            except Exception:
                pass
        super().closeEvent(event)
