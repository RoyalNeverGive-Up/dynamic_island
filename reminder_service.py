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
        self._start_time = datetime.now()
        self._last_alerted_alarm_keys = set()  # (alarm_id, minute_str)
        self._catchup_overdue_on_startup()
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._check_reminders)
        self.timer.start()

    def _catchup_overdue_on_startup(self):
        """
        When the application launches, do not fire overdue alarms/habits immediately.
        Instead, roll overdue recurring alarms and interval habits forward to their
        next legitimate occurrence from startup time, so reminders only trigger going forward.
        """
        now = self._start_time
        # 1. Alarms: if next_trigger is already in the past, roll forward to next cycle
        alarms = storage.get_alarms()
        alarms_modified = False
        for a in alarms:
            trig_str = a.get("next_trigger")
            if trig_str:
                try:
                    dt = datetime.strptime(trig_str, "%Y-%m-%d %H:%M")
                    if dt < now:
                        new_t = calculate_next_occurrence(
                            a.get("repeat_type", "weekly"),
                            a.get("repeat_days", []),
                            a.get("time", "09:30"),
                            now
                        )
                        a["next_trigger"] = new_t
                        a["snooze_until"] = None
                        alarms_modified = True
                except Exception:
                    pass
        if alarms_modified:
            storage.save_alarms(alarms)

        # 2. Habits: calculate fresh next_trigger starting from now
        habits = storage.get_habits()
        habits_modified = False
        for h in habits:
            trig_str = h.get("next_trigger")
            if trig_str:
                try:
                    dt = datetime.strptime(trig_str, "%Y-%m-%d %H:%M")
                    if dt < now:
                        next_dt = storage._calculate_next_habit_time(
                            h.get("start_time", "09:00"),
                            h.get("end_time", "18:00"),
                            h.get("default_interval", 45),
                            now
                        )
                        h["next_trigger"] = next_dt.strftime("%Y-%m-%d %H:%M") if next_dt else None
                        h["snooze_until"] = None
                        habits_modified = True
                except Exception:
                    pass
        if habits_modified:
            storage.save_habits(habits)

        # 3. Mark old already-past one-off todos as reminded so they don't ring on launch
        todos = storage.get_todos()
        todos_modified = False
        for t in todos:
            if t.get("reminder_enabled") and not t.get("completed") and not t.get("reminded") and t.get("due_time"):
                try:
                    due_dt = datetime.strptime(t["due_time"], "%Y-%m-%d %H:%M")
                    if due_dt < now:
                        t["reminded"] = True
                        todos_modified = True
                except Exception:
                    pass
        if todos_modified:
            storage.save_todos(todos)

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
        alarm_candidates = []
        for alarm in alarms:
            if not alarm.get("enabled", True):
                continue
            target_trigger = alarm.get("snooze_until") or alarm.get("next_trigger")
            if not target_trigger:
                continue
            try:
                trig_dt = datetime.strptime(target_trigger, "%Y-%m-%d %H:%M")
                alarm_candidates.append((trig_dt, target_trigger, alarm))
            except Exception:
                pass

        alarm_candidates.sort(key=lambda x: x[0])
        for trig_dt, target_trigger, alarm in alarm_candidates:
            alarm_key = (alarm["id"], target_trigger)
            if alarm_key in self._last_alerted_alarm_keys:
                continue

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
        habit_candidates = []
        for habit in habits:
            if not habit.get("enabled", True):
                continue

            target_trigger = habit.get("snooze_until") or habit.get("next_trigger")
            if not target_trigger:
                continue

            try:
                trig_dt = datetime.strptime(target_trigger, "%Y-%m-%d %H:%M")
                habit_candidates.append((trig_dt, target_trigger, habit))
            except Exception:
                pass

        habit_candidates.sort(key=lambda x: x[0])
        for trig_dt, target_trigger, habit in habit_candidates:
            habit_key = (habit["id"], target_trigger)
            if habit_key in self._last_alerted_alarm_keys:
                continue

            if now >= trig_dt:
                self._last_alerted_alarm_keys.add(habit_key)
                self._play_chime()
                self.reminder_triggered.emit({
                    "type": "habit",
                    "id": habit["id"],
                    "title": habit.get("title", "习惯提醒"),
                    "time": target_trigger.split(" ")[-1],
                    "habit": habit
                })
                return
