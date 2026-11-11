from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from storage import storage

try:
    import winsound
except ImportError:
    winsound = None

class PomodoroService(QObject):
    tick = pyqtSignal(int, int, str)  # remaining_seconds, total_seconds, mode_name
    state_changed = pyqtSignal(bool)   # is_running
    completed = pyqtSignal(str)        # mode_name

    MODE_WORK = "专注工作"
    MODE_SHORT_BREAK = "小憩休息"
    MODE_LONG_BREAK = "深度休息"

    DURATIONS = {
        MODE_WORK: 25 * 60,
        MODE_SHORT_BREAK: 5 * 60,
        MODE_LONG_BREAK: 15 * 60,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_mode = self.MODE_WORK
        self.total_seconds = self.DURATIONS[self.MODE_WORK]
        self.remaining_seconds = self.total_seconds
        self.is_running = False
        self.completed_count = 0

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_tick)

    def set_mode(self, mode: str):
        if mode in self.DURATIONS:
            self.stop()
            self.current_mode = mode
            self.total_seconds = self.DURATIONS[mode]
            self.remaining_seconds = self.total_seconds
            self.tick.emit(self.remaining_seconds, self.total_seconds, self.current_mode)

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.timer.start()
            self.state_changed.emit(True)

    def pause(self):
        if self.is_running:
            self.is_running = False
            self.timer.stop()
            self.state_changed.emit(False)

    def toggle(self):
        if self.is_running:
            self.pause()
        else:
            self.start()

    def stop(self):
        self.is_running = False
        self.timer.stop()
        self.remaining_seconds = self.total_seconds
        self.state_changed.emit(False)
        self.tick.emit(self.remaining_seconds, self.total_seconds, self.current_mode)

    def reset(self):
        self.stop()

    def _on_tick(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.tick.emit(self.remaining_seconds, self.total_seconds, self.current_mode)
        else:
            self._handle_completed()

    def _handle_completed(self):
        self.stop()
        if self.current_mode == self.MODE_WORK:
            self.completed_count += 1

        # Chime
        settings = storage.get_settings()
        if settings.get("sound_enabled", True) and winsound:
            try:
                winsound.Beep(1046, 200) # C6
                winsound.Beep(1318, 200) # E6
                winsound.Beep(1568, 300) # G6
            except Exception:
                pass

        self.completed.emit(self.current_mode)

        # Auto transition mode
        if self.current_mode == self.MODE_WORK:
            if self.completed_count % 4 == 0:
                self.set_mode(self.MODE_LONG_BREAK)
            else:
                self.set_mode(self.MODE_SHORT_BREAK)
        else:
            self.set_mode(self.MODE_WORK)
