# reminder_service.py - Unified Reminder Engine for Todos and Recurring Alarms
import sys
from datetime import datetime, timedelta
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from storage import storage, calculate_next_occurrence

try:
    import winsound
except ImportError:
    winsound = None


class ReminderService(QObject):
    reminder_triggered = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_alerted_alarm_keys = set()  # (alarm_id, minute_str)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._check_reminders)
        self.timer.start()

    def _play_chime(self):
        settings = storage.get_settings()
        if not settings.get("sound_enabled", True) or not winsound:
            return
        try:
            # Dual-tone pleasant alert sound (A5 then D6)
            winsound.Beep(880, 150)
            winsound.Beep(1174, 250)
        except Exception:
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass

    def _check_reminders(self):
        now = datetime.now()
        now_minute_str = now.strftime("%Y-%m-%d %H:%M")

        # 1. Check Alarms (Recurring alarms & active snoozes)
        alarms = storage.get_alarms()
        for alarm in alarms:
            if not alarm.get("enabled", True):
                continue

            target_trigger = alarm.get("snooze_until") or alarm.get("next_trigger")
            if not target_trigger:
                continue

            alarm_key = (alarm["id"], target_trigger)
            if alarm_key in self._last_alerted_alarm_keys:
                continue

            try:
                trig_dt = datetime.strptime(target_trigger, "%Y-%m-%d %H:%M")
                if now >= trig_dt:
                    self._last_alerted_alarm_keys.add(alarm_key)
                    self._play_chime()
                    self.reminder_triggered.emit({
                        "type": "alarm",
                        "id": alarm["id"],
                        "title": alarm.get("title", "周期闹钟"),
                        "time": alarm.get("time", ""),
                        "alarm": alarm
                    })
                    return  # Trigger one per second to prevent clutter
            except Exception as e:
                pass

        # 2. Check Tasks (One-off Todos)
        todos = storage.get_todos()
        for todo in todos:
            if (todo.get("reminder_enabled")
                    and not todo.get("completed")
                    and not todo.get("reminded")
                    and todo.get("due_time")):
                try:
                    due_dt = datetime.strptime(todo["due_time"], "%Y-%m-%d %H:%M")
                    if now >= due_dt:
                        todo["reminded"] = True
                        storage.save_todos(todos)
                        self._play_chime()
                        self.reminder_triggered.emit({
                            "type": "todo",
                            "id": todo["id"],
                            "title": todo.get("title", "待办事项"),
                            "time": todo.get("due_time", "").split(" ")[-1],
                            "todo": todo
                        })
                        return
                except Exception as e:
                    pass

        # 3. Check Habits (Interval Reminders: Water, Stretch, Health)
        habits = storage.get_habits()
        for habit in habits:
            if not habit.get("enabled", True):
                continue

            target_trigger = habit.get("snooze_until") or habit.get("next_trigger")
            if not target_trigger:
                continue

            habit_key = (habit["id"], target_trigger)
            if habit_key in self._last_alerted_alarm_keys:
                continue

            try:
                trig_dt = datetime.strptime(target_trigger, "%Y-%m-%d %H:%M")
                if now >= trig_dt:
                    self._last_alerted_alarm_keys.add(habit_key)
                    self._play_chime()
                    self.reminder_triggered.emit({
                        "type": "habit",
                        "id": habit["id"],
                        "title": habit.get("title", "定时喝水打卡"),
                        "time": habit.get("next_trigger", "").split(" ")[-1],
                        "habit": habit
                    })
                    return
            except Exception:
                pass
