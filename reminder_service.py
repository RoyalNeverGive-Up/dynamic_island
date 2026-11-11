import sys
from datetime import datetime
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from storage import storage

try:
    import winsound
except ImportError:
    winsound = None

class ReminderService(QObject):
    reminder_triggered = pyqtSignal(dict)  # Emits the todo dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)  # Check every 1 second
        self.timer.timeout.connect(self._check_reminders)
        self.timer.start()

    def _play_chime(self):
        settings = storage.get_settings()
        if not settings.get("sound_enabled", True) or not winsound:
            return
        try:
            # Play a pleasant dual-tone chime (A5 then D6)
            winsound.Beep(880, 150)
            winsound.Beep(1174, 250)
        except Exception:
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass

    def _check_reminders(self):
        todos = storage.get_todos()
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M")

        for todo in todos:
            if (todo.get("reminder_enabled")
                    and not todo.get("completed")
                    and not todo.get("reminded")
                    and todo.get("due_time")):
                try:
                    due_dt = datetime.strptime(todo["due_time"], "%Y-%m-%d %H:%M")
                    # If due time has arrived or passed (within reasonable 24hr window)
                    if now >= due_dt:
                        # Mark as reminded
                        todo["reminded"] = True
                        storage.save_todos(todos)
                        self._play_chime()
                        self.reminder_triggered.emit(todo)
                        break  # Trigger one reminder per tick to avoid clutter
                except Exception as e:
                    print(f"Error parsing due_time for todo '{todo.get('title')}': {e}")
