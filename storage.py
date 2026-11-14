import json
import uuid
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from config import (
    TODOS_FILE, ALARMS_FILE, HABITS_FILE, SETTINGS_FILE, MEMO_FILE, PLAYLIST_FILE,
    DEFAULT_SETTINGS, REPEAT_NONE, REPEAT_DAILY, REPEAT_WEEKLY, REPEAT_WORKDAY,
    WEEKDAY_NAMES
)

def calculate_next_occurrence(repeat_type: str, repeat_days: List[int], repeat_time: str, base_dt: Optional[datetime] = None) -> Optional[str]:
    """
    Calculate the next occurrence datetime string (YYYY-MM-DD HH:MM).
    repeat_days: list of integers from 1 to 7 (1=Monday, 7=Sunday).
    repeat_time: 'HH:MM'.
    """
    if not repeat_type or repeat_type == REPEAT_NONE or not repeat_time:
        return None

    if base_dt is None:
        base_dt = datetime.now()

    try:
        parts = repeat_time.strip().split(":")
        hour, minute = int(parts[0]), int(parts[1])
    except Exception:
        hour, minute = 9, 0

    if repeat_type == REPEAT_DAILY:
        target_days = [1, 2, 3, 4, 5, 6, 7]
    elif repeat_type == REPEAT_WORKDAY:
        target_days = [1, 2, 3, 4, 5]
    elif repeat_type == REPEAT_WEEKLY:
        target_days = repeat_days if repeat_days else [1]
    else:
        return None

    # Search for the next matching day starting from today up to 8 days
    for offset in range(8):
        cand_date = base_dt.date() + timedelta(days=offset)
        if cand_date.isoweekday() in target_days:
            cand_dt = datetime(cand_date.year, cand_date.month, cand_date.day, hour, minute)
            if cand_dt > base_dt:
                return cand_dt.strftime("%Y-%m-%d %H:%M")

    # Fallback to 7 days later
    fallback_dt = (base_dt + timedelta(days=7)).replace(hour=hour, minute=minute)
    return fallback_dt.strftime("%Y-%m-%d %H:%M")


def parse_natural_time(text: str):
    """
    Intelligently parses natural time expressions from text.
    Returns:
        cleaned_title: str
        due_time: str ('YYYY-MM-DD HH:MM' or '')
        repeat_type: str ('none', 'daily', 'weekly', 'workday')
        repeat_days: list of int
        repeat_time: str ('HH:MM' or '')
    """
    now = datetime.now()
    cleaned_title = text.strip()
    repeat_type = REPEAT_NONE
    repeat_days = []
    repeat_time = ""
    due_time = ""

    week_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '日': 7, '天': 7}

    # 1. Match repetition keywords
    m_weekly = re.search(r'每[周星期]([一二三四五六日天])', text)
    if m_weekly:
        repeat_type = REPEAT_WEEKLY
        repeat_days = [week_map[m_weekly.group(1)]]
        cleaned_title = re.sub(r'每[周星期][一二三四五六日天]', '', cleaned_title)
    elif '每个工作日' in text or '工作日' in text:
        repeat_type = REPEAT_WORKDAY
        repeat_days = [1, 2, 3, 4, 5]
        cleaned_title = re.sub(r'(每个)?工作日', '', cleaned_title)
    elif '每天' in text:
        repeat_type = REPEAT_DAILY
        repeat_days = [1, 2, 3, 4, 5, 6, 7]
        cleaned_title = cleaned_title.replace('每天', '')

    # 2. Match time expression: e.g. 15:30 or 下午3点半
    time_str = ""
    m_time = re.search(r'(\d{1,2})[:：](\d{2})', cleaned_title)
    if m_time:
        h, m = int(m_time.group(1)), int(m_time.group(2))
        time_str = f"{h:02d}:{m:02d}"
        cleaned_title = cleaned_title.replace(m_time.group(0), "")
    else:
        m_cn = re.search(r'(上午|下午|晚上|中午|早上)?(\d{1,2})点(半|(\d{1,2})分)?', cleaned_title)
        if m_cn:
            period, h_val, half, m_val = m_cn.group(1), int(m_cn.group(2)), m_cn.group(3), m_cn.group(4)
            h = h_val
            if period in ['下午', '晚上'] and h < 12:
                h += 12
            minute = 30 if half == '半' else (int(m_val) if m_val else 0)
            time_str = f"{h:02d}:{minute:02d}"
            cleaned_title = cleaned_title.replace(m_cn.group(0), "")

    # 3. Match relative dates: 今天, 明天, 后天, or specific weekday
    target_date = now.date()
    if '明天' in cleaned_title:
        target_date = now.date() + timedelta(days=1)
        cleaned_title = cleaned_title.replace('明天', '')
    elif '后天' in cleaned_title:
        target_date = now.date() + timedelta(days=2)
        cleaned_title = cleaned_title.replace('后天', '')
    elif '今天' in cleaned_title:
        target_date = now.date()
        cleaned_title = cleaned_title.replace('今天', '')
    elif repeat_type == REPEAT_NONE:
        # Check single weekday, e.g. "周三开会", "星期五"
        m_single_week = re.search(r'[周星期]([一二三四五六日天])', cleaned_title)
        if m_single_week:
            target_iso = week_map[m_single_week.group(1)]
            for off in range(1, 8):
                c_date = now.date() + timedelta(days=off)
                if c_date.isoweekday() == target_iso:
                    target_date = c_date
                    break
            cleaned_title = re.sub(r'[周星期][一二三四五六日天]', '', cleaned_title)

    cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()

    if repeat_type != REPEAT_NONE:
        repeat_time = time_str if time_str else "09:00"
        due_time = calculate_next_occurrence(repeat_type, repeat_days, repeat_time, now) or ""
    elif time_str:
        due_time = f"{target_date.strftime('%Y-%m-%d')} {time_str}"

    return cleaned_title, due_time, repeat_type, repeat_days, repeat_time


def format_repeat_display(todo: Dict[str, Any]) -> str:
    """Return friendly text description of the recurrence."""
    rtype = todo.get("repeat_type", REPEAT_NONE)
    rtime = todo.get("repeat_time", "")
    if rtype == REPEAT_NONE or not rtype:
        return ""

    time_str = f" {rtime}" if rtime else ""
    if rtype == REPEAT_DAILY:
        return f"🔁 每天{time_str}"
    elif rtype == REPEAT_WORKDAY:
        return f"🔁 工作日{time_str}"
    elif rtype == REPEAT_WEEKLY:
        rdays = todo.get("repeat_days", [])
        if not rdays:
            return f"🔁 每周{time_str}"
        day_labels = [WEEKDAY_NAMES[d - 1] for d in sorted(rdays) if 1 <= d <= 7]
        days_str = "、".join(day_labels)
        return f"🔁 每{days_str}{time_str}"
    return ""


def format_alarm_repeat(alarm: dict) -> str:
    """Format alarm recurrence into a human-readable badge label."""
    rtype = alarm.get("repeat_type", REPEAT_WEEKLY)
    t = alarm.get("time", "")
    time_str = f" {t}" if t else ""

    if rtype == REPEAT_DAILY:
        return f"🔁 每天{time_str}"
    elif rtype == REPEAT_WORKDAY:
        return f"🔁 工作日{time_str}"
    elif rtype == REPEAT_WEEKLY:
        rdays = alarm.get("repeat_days", [])
        if not rdays:
            return f"🔁 每周{time_str}"
        day_labels = [WEEKDAY_NAMES[d - 1] for d in sorted(rdays) if 1 <= d <= 7]
        days_str = "、".join(day_labels)
        return f"🔁 每{days_str}{time_str}"
    return f"⏰ {t}" if t else "⏰ 提醒"


class StorageManager:
    def __init__(self):
        self._ensure_files()

    def _ensure_files(self):
        if not SETTINGS_FILE.exists():
            self.save_settings(DEFAULT_SETTINGS)

        now = datetime.now()

        # Migrate recurring items from todos.json to alarms.json if needed
        existing_todos = []
        if TODOS_FILE.exists():
            existing_todos = self.get_todos()

        # Initialize or migrate ALARMS_FILE
        if not ALARMS_FILE.exists():
            alarms_to_save = []
            todos_remaining = []

            # Extract repeating items from todos
            for t in existing_todos:
                rtype = t.get("repeat_type")
                if rtype and rtype != REPEAT_NONE:
                    alarm_time = t.get("repeat_time") or (t.get("due_time", "").split(" ")[-1] if t.get("due_time") else "09:30")
                    alarm_days = t.get("repeat_days") or ([1] if rtype == REPEAT_WEEKLY else [1, 2, 3, 4, 5, 6, 7])
                    next_t = calculate_next_occurrence(rtype, alarm_days, alarm_time, now) or t.get("due_time", "")
                    alarms_to_save.append({
                        "id": t.get("id", str(uuid.uuid4())),
                        "title": t.get("title", "周期提醒"),
                        "description": t.get("description", ""),
                        "enabled": t.get("reminder_enabled", True),
                        "repeat_type": rtype,
                        "repeat_days": alarm_days,
                        "time": alarm_time,
                        "next_trigger": next_t,
                        "snooze_until": None,
                        "checkin_count": 0,
                        "last_checkin_at": None,
                        "created_at": t.get("created_at", now.strftime("%Y-%m-%d %H:%M:%S")),
                    })
                else:
                    todos_remaining.append(t)

            # If no alarms were extracted from existing todos, provide initial sample alarms
            if not alarms_to_save:
                alarms_to_save = [
                    {
                        "id": str(uuid.uuid4()),
                        "title": "每周一项目周会 🚀",
                        "description": "整理更新日志，同步本周迭代目标",
                        "enabled": True,
                        "repeat_type": REPEAT_WEEKLY,
                        "repeat_days": [1],
                        "time": "09:30",
                        "next_trigger": calculate_next_occurrence(REPEAT_WEEKLY, [1], "09:30", now),
                        "snooze_until": None,
                        "checkin_count": 3,
                        "last_checkin_at": (now - timedelta(days=7)).strftime("%Y-%m-%d 09:30:00"),
                        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "title": "每天下午喝水与拉伸 💧",
                        "description": "保持充沛精力，劳逸结合",
                        "enabled": True,
                        "repeat_type": REPEAT_DAILY,
                        "repeat_days": [1, 2, 3, 4, 5, 6, 7],
                        "time": "15:00",
                        "next_trigger": calculate_next_occurrence(REPEAT_DAILY, [1, 2, 3, 4, 5, 6, 7], "15:00", now),
                        "snooze_until": None,
                        "checkin_count": 12,
                        "last_checkin_at": (now - timedelta(days=1)).strftime("%Y-%m-%d 15:01:00"),
                        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                ]

            self.save_alarms(alarms_to_save)

            # If we extracted alarms from todos, update todos.json to remove recurring items
            if existing_todos and len(todos_remaining) != len(existing_todos):
                self.save_todos(todos_remaining)

        # Initialize pure TODOS_FILE if still empty or not existing
        if not TODOS_FILE.exists() or len(self.get_todos()) == 0:
            sample_todos = [
                {
                    "id": str(uuid.uuid4()),
                    "title": "欢迎体验 Windows 灵动岛！✨",
                    "description": "点击左侧圆圈标记完成，体验丝滑打卡与纯粹待办",
                    "priority": "medium",
                    "category": "工作",
                    "due_time": (now + timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M"),
                    "reminder_enabled": True,
                    "repeat_type": REPEAT_NONE,
                    "repeat_days": [],
                    "repeat_time": "",
                    "reminded": False,
                    "completed": False,
                    "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "completed_at": None,
                },
                {
                    "id": str(uuid.uuid4()),
                    "title": "整理下周采购预算清单 📋",
                    "description": "核对财务明细与报销凭据",
                    "priority": "high",
                    "category": "工作",
                    "due_time": (now + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"),
                    "reminder_enabled": True,
                    "repeat_type": REPEAT_NONE,
                    "repeat_days": [],
                    "repeat_time": "",
                    "reminded": False,
                    "completed": False,
                    "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "completed_at": None,
                }
            ]
            self.save_todos(sample_todos)

        # Initialize HABITS_FILE
        if not HABITS_FILE.exists():
            habits_to_save = [
                {
                    "id": str(uuid.uuid4()),
                    "title": "定时喝水打卡 💧",
                    "type": "water",
                    "start_time": "09:00",
                    "end_time": "18:00",
                    "default_interval": 45,
                    "target_count": 8,
                    "today_count": 3,
                    "last_date": now.strftime("%Y-%m-%d"),
                    "last_checkin_at": (now - timedelta(minutes=40)).strftime("%Y-%m-%d %H:%M:%S"),
                    "next_trigger": (now + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M"),
                    "snooze_until": None,
                    "enabled": True,
                    "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                },
                {
                    "id": str(uuid.uuid4()),
                    "title": "久坐起身拉伸 🚶",
                    "type": "stretch",
                    "start_time": "10:00",
                    "end_time": "18:00",
                    "default_interval": 60,
                    "target_count": 6,
                    "today_count": 2,
                    "last_date": now.strftime("%Y-%m-%d"),
                    "last_checkin_at": (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                    "next_trigger": (now + timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M"),
                    "snooze_until": None,
                    "enabled": True,
                    "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                }
            ]
            self.save_habits(habits_to_save)

            # Clean up water tasks from alarms.json if present
            alarms = self.get_alarms()
            cleaned_alarms = [a for a in alarms if "喝水" not in a.get("title", "")]
            if len(cleaned_alarms) != len(alarms):
                self.save_alarms(cleaned_alarms)

        if not MEMO_FILE.exists():
            self.save_memo("💡 灵动便签：随手记录你的灵感、常用链接或备忘信息...\n- 支持实时自动保存\n- 随取随用")

        if not PLAYLIST_FILE.exists():
            self.save_playlist([])

    # --- Todo Operations (Pure Task Management, zero confusion) ---
    def get_todos(self) -> List[Dict[str, Any]]:
        try:
            if TODOS_FILE.exists():
                with open(TODOS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading todos: {e}")
        return []

    def save_todos(self, todos: List[Dict[str, Any]]) -> bool:
        try:
            with open(TODOS_FILE, "w", encoding="utf-8") as f:
                json.dump(todos, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving todos: {e}")
            return False

    def add_todo(self, title: str, description: str = "", priority: str = "medium",
                 category: str = "工作", due_time: str = "", reminder_enabled: bool = True,
                 repeat_type: str = REPEAT_NONE, repeat_days: Optional[List[int]] = None,
                 repeat_time: str = "") -> Dict[str, Any]:
        todos = self.get_todos()
        now = datetime.now()

        new_todo = {
            "id": str(uuid.uuid4()),
            "title": title.strip(),
            "description": description.strip(),
            "priority": priority,
            "category": category,
            "due_time": due_time.strip(),
            "reminder_enabled": reminder_enabled if due_time.strip() else False,
            "repeat_type": repeat_type or REPEAT_NONE,
            "repeat_days": repeat_days if repeat_days is not None else [],
            "repeat_time": repeat_time.strip() if repeat_time else "",
            "reminded": False,
            "completed": False,
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "completed_at": None,
        }
        todos.insert(0, new_todo)
        self.save_todos(todos)
        return new_todo

    def update_todo(self, todo_id: str, updates: Dict[str, Any]) -> bool:
        todos = self.get_todos()
        updated = False
        for todo in todos:
            if todo["id"] == todo_id:
                for k, v in updates.items():
                    todo[k] = v
                updated = True
                break
        if updated:
            self.save_todos(todos)
        return updated

    def toggle_todo(self, todo_id: str) -> bool:
        """
        Pure task completion toggle.
        Clicking the checkbox ALWAYS marks the task completed/uncompleted,
        crossing out the title and saving completed_at timestamp!
        """
        todos = self.get_todos()
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        for todo in todos:
            if todo["id"] == todo_id:
                todo["completed"] = not todo.get("completed", False)
                todo["completed_at"] = now_str if todo["completed"] else None
                self.save_todos(todos)
                return todo["completed"]
        return False

    def delete_todo(self, todo_id: str) -> bool:
        todos = self.get_todos()
        initial_len = len(todos)
        todos = [t for t in todos if t["id"] != todo_id]
        if len(todos) != initial_len:
            self.save_todos(todos)
            return True
        return False

    def clear_completed(self) -> int:
        todos = self.get_todos()
        pending = [t for t in todos if not t.get("completed", False)]
        removed = len(todos) - len(pending)
        self.save_todos(pending)
        return removed

    def snooze_todo(self, todo_id: str, minutes: int = 5) -> bool:
        todos = self.get_todos()
        for todo in todos:
            if todo["id"] == todo_id:
                new_due = datetime.now() + timedelta(minutes=minutes)
                todo["due_time"] = new_due.strftime("%Y-%m-%d %H:%M")
                todo["reminded"] = False
                todo["reminder_enabled"] = True
                self.save_todos(todos)
                return True
        return False

    # --- Alarm Operations (Recurring Reminders, Check-in & Snooze) ---
    def get_alarms(self) -> List[Dict[str, Any]]:
        try:
            if ALARMS_FILE.exists():
                with open(ALARMS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading alarms: {e}")
        return []

    def save_alarms(self, alarms: List[Dict[str, Any]]) -> bool:
        try:
            with open(ALARMS_FILE, "w", encoding="utf-8") as f:
                json.dump(alarms, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving alarms: {e}")
            return False

    def add_alarm(self, title: str, time: str, repeat_type: str = REPEAT_WEEKLY,
                  repeat_days: Optional[List[int]] = None, description: str = "",
                  enabled: bool = True) -> Dict[str, Any]:
        alarms = self.get_alarms()
        now = datetime.now()
        days = repeat_days if repeat_days is not None else ([1] if repeat_type == REPEAT_WEEKLY else [])
        next_t = calculate_next_occurrence(repeat_type, days, time, now)

        new_alarm = {
            "id": str(uuid.uuid4()),
            "title": title.strip(),
            "description": description.strip(),
            "enabled": enabled,
            "repeat_type": repeat_type,
            "repeat_days": sorted(days),
            "time": time.strip(),
            "next_trigger": next_t,
            "snooze_until": None,
            "checkin_count": 0,
            "last_checkin_at": None,
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        }
        alarms.insert(0, new_alarm)
        self.save_alarms(alarms)
        return new_alarm

    def update_alarm(self, alarm_id: str, updates: Dict[str, Any]) -> bool:
        alarms = self.get_alarms()
        updated = False
        now = datetime.now()
        for a in alarms:
            if a["id"] == alarm_id:
                for k, v in updates.items():
                    a[k] = v
                # Recalculate next occurrence if time or recurrence rules changed
                if "time" in updates or "repeat_type" in updates or "repeat_days" in updates:
                    a["next_trigger"] = calculate_next_occurrence(
                        a.get("repeat_type", REPEAT_WEEKLY),
                        a.get("repeat_days", []),
                        a.get("time", "09:30"),
                        now
                    )
                    a["snooze_until"] = None
                updated = True
                break
        if updated:
            self.save_alarms(alarms)
        return updated

    def delete_alarm(self, alarm_id: str) -> bool:
        alarms = self.get_alarms()
        initial_len = len(alarms)
        alarms = [a for a in alarms if a["id"] != alarm_id]
        if len(alarms) != initial_len:
            self.save_alarms(alarms)
            return True
        return False

    def toggle_alarm_enabled(self, alarm_id: str) -> bool:
        """Toggle an alarm's enabled/paused state with iOS style switch."""
        alarms = self.get_alarms()
        now = datetime.now()
        for a in alarms:
            if a["id"] == alarm_id:
                a["enabled"] = not a.get("enabled", True)
                if a["enabled"]:
                    # Recalculate next trigger on re-enable
                    a["next_trigger"] = calculate_next_occurrence(
                        a.get("repeat_type", REPEAT_WEEKLY),
                        a.get("repeat_days", []),
                        a.get("time", "09:30"),
                        now
                    )
                self.save_alarms(alarms)
                return a["enabled"]
        return False

    def checkin_alarm(self, alarm_id: str) -> Optional[Dict[str, Any]]:
        """
        Check in for the current alarm cycle.
        Increments checkin count, records timestamp, clears snooze,
        and rolls next_trigger forward to the next cycle.
        """
        alarms = self.get_alarms()
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        for a in alarms:
            if a["id"] == alarm_id:
                a["checkin_count"] = a.get("checkin_count", 0) + 1
                a["last_checkin_at"] = now_str
                a["snooze_until"] = None

                # Advance to next cycle
                next_t = calculate_next_occurrence(
                    a.get("repeat_type", REPEAT_WEEKLY),
                    a.get("repeat_days", []),
                    a.get("time", "09:30"),
                    now
                )
                a["next_trigger"] = next_t
                self.save_alarms(alarms)
                return a
        return None

    def snooze_alarm(self, alarm_id: str, minutes: int = 5) -> Optional[Dict[str, Any]]:
        """
        Delay / snooze alarm by N minutes.
        Sets snooze_until so reminder engine alerts again after N minutes.
        """
        alarms = self.get_alarms()
        target_dt = datetime.now() + timedelta(minutes=minutes)
        target_str = target_dt.strftime("%Y-%m-%d %H:%M")

        for a in alarms:
            if a["id"] == alarm_id:
                a["snooze_until"] = target_str
                self.save_alarms(alarms)
                return a
        return None

    def cancel_alarm_snooze(self, alarm_id: str) -> bool:
        """Cancel an active snooze, reverting to normal cycle next_trigger."""
        alarms = self.get_alarms()
        for a in alarms:
            if a["id"] == alarm_id:
                a["snooze_until"] = None
                self.save_alarms(alarms)
                return True
        return False

    def get_next_alarm(self) -> Optional[Dict[str, Any]]:
        """Find the earliest upcoming active alarm."""
        alarms = self.get_alarms()
        active = [a for a in alarms if a.get("enabled", True)]
        if not active:
            return None

        candidates = []
        for a in active:
            trigger_time = a.get("snooze_until") or a.get("next_trigger")
            if trigger_time:
                try:
                    dt = datetime.strptime(trigger_time, "%Y-%m-%d %H:%M")
                    candidates.append((dt, a))
                except Exception:
                    pass
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
        return active[0]

    # --- Habit Operations (Interval Reminders: Water, Stretch, Health) ---
    def get_habits(self) -> List[Dict[str, Any]]:
        try:
            if HABITS_FILE.exists():
                with open(HABITS_FILE, "r", encoding="utf-8") as f:
                    habits = json.load(f)
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    modified = False
                    for h in habits:
                        if h.get("last_date") != today_str:
                            h["today_count"] = 0
                            h["last_date"] = today_str
                            modified = True
                    if modified:
                        self.save_habits(habits)
                    return habits
        except Exception as e:
            print(f"Error loading habits: {e}")
        return []

    def save_habits(self, habits: List[Dict[str, Any]]) -> bool:
        try:
            with open(HABITS_FILE, "w", encoding="utf-8") as f:
                json.dump(habits, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving habits: {e}")
            return False

    def _calculate_next_habit_time(self, start_t: str, end_t: str, interval_mins: int, base_dt: datetime) -> Optional[datetime]:
        """Calculate next trigger datetime considering start_time and end_time range."""
        try:
            sh, sm = map(int, start_t.split(":"))
            eh, em = map(int, end_t.split(":"))
        except Exception:
            sh, sm, eh, em = 9, 0, 18, 0

        today = base_dt.date()
        start_dt = datetime(today.year, today.month, today.day, sh, sm)
        end_dt = datetime(today.year, today.month, today.day, eh, em)

        if base_dt < start_dt:
            return start_dt

        target_dt = base_dt + timedelta(minutes=interval_mins)
        if target_dt <= end_dt:
            return target_dt

        # Roll over to tomorrow's start_time
        tomorrow = today + timedelta(days=1)
        return datetime(tomorrow.year, tomorrow.month, tomorrow.day, sh, sm)

    def add_habit(self, title: str, start_time: str = "09:00", end_time: str = "18:00",
                  default_interval: int = 45, target_count: int = 8, habit_type: str = "water",
                  enabled: bool = True) -> Dict[str, Any]:
        habits = self.get_habits()
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        next_dt = self._calculate_next_habit_time(start_time, end_time, default_interval, now)

        new_h = {
            "id": str(uuid.uuid4()),
            "title": title.strip(),
            "type": habit_type,
            "start_time": start_time.strip(),
            "end_time": end_time.strip(),
            "default_interval": default_interval,
            "target_count": target_count,
            "today_count": 0,
            "last_date": today_str,
            "last_checkin_at": None,
            "next_trigger": next_dt.strftime("%Y-%m-%d %H:%M") if next_dt else None,
            "snooze_until": None,
            "enabled": enabled,
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        }
        habits.insert(0, new_h)
        self.save_habits(habits)
        return new_h

    def checkin_habit(self, habit_id: str, next_interval_minutes: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Check in habit, increments today_count,
        and dynamically sets next trigger to user's selected minutes (or default).
        """
        habits = self.get_habits()
        now = datetime.now()
        for h in habits:
            if h["id"] == habit_id:
                h["today_count"] = h.get("today_count", 0) + 1
                h["last_checkin_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
                h["snooze_until"] = None

                interval = next_interval_minutes if next_interval_minutes is not None else h.get("default_interval", 45)
                next_dt = self._calculate_next_habit_time(
                    h.get("start_time", "09:00"),
                    h.get("end_time", "18:00"),
                    interval,
                    now
                )
                h["next_trigger"] = next_dt.strftime("%Y-%m-%d %H:%M") if next_dt else None
                self.save_habits(habits)
                return h
        return None

    def snooze_habit(self, habit_id: str, minutes: int = 15) -> Optional[Dict[str, Any]]:
        habits = self.get_habits()
        target_dt = datetime.now() + timedelta(minutes=minutes)
        for h in habits:
            if h["id"] == habit_id:
                h["snooze_until"] = target_dt.strftime("%Y-%m-%d %H:%M")
                self.save_habits(habits)
                return h
        return None

    def toggle_habit_enabled(self, habit_id: str) -> bool:
        habits = self.get_habits()
        now = datetime.now()
        for h in habits:
            if h["id"] == habit_id:
                h["enabled"] = not h.get("enabled", True)
                if h["enabled"]:
                    next_dt = self._calculate_next_habit_time(
                        h.get("start_time", "09:00"),
                        h.get("end_time", "18:00"),
                        h.get("default_interval", 45),
                        now
                    )
                    h["next_trigger"] = next_dt.strftime("%Y-%m-%d %H:%M") if next_dt else None
                self.save_habits(habits)
                return h["enabled"]
        return False

    def delete_habit(self, habit_id: str) -> bool:
        habits = self.get_habits()
        initial_len = len(habits)
        habits = [h for h in habits if h["id"] != habit_id]
        if len(habits) != initial_len:
            self.save_habits(habits)
            return True
        return False

    def update_habit(self, habit_id: str, updates: Dict[str, Any]) -> bool:
        habits = self.get_habits()
        now = datetime.now()
        for h in habits:
            if h["id"] == habit_id:
                for k, v in updates.items():
                    h[k] = v
                next_dt = self._calculate_next_habit_time(
                    h.get("start_time", "09:00"),
                    h.get("end_time", "18:00"),
                    h.get("default_interval", 45),
                    now
                )
                h["next_trigger"] = next_dt.strftime("%Y-%m-%d %H:%M") if next_dt else None
                h["snooze_until"] = None
                self.save_habits(habits)
                return True
        return False

    def get_next_habit(self) -> Optional[Dict[str, Any]]:
        habits = self.get_habits()
        active = [h for h in habits if h.get("enabled", True)]
        if not active:
            return None
        candidates = []
        for h in active:
            t_str = h.get("snooze_until") or h.get("next_trigger")
            if t_str:
                try:
                    dt = datetime.strptime(t_str, "%Y-%m-%d %H:%M")
                    candidates.append((dt, h))
                except Exception:
                    pass
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
        return active[0]

    def get_next_pending(self) -> Optional[Dict[str, Any]]:
        """Find the earliest pending task with a due time, or the top pending task."""
        todos = self.get_todos()
        pending = [t for t in todos if not t.get("completed", False)]
        if not pending:
            return None

        # Prefer tasks with due_time
        timed_pending = []
        for t in pending:
            if t.get("due_time"):
                try:
                    dt = datetime.strptime(t["due_time"], "%Y-%m-%d %H:%M")
                    timed_pending.append((dt, t))
                except Exception:
                    pass

        if timed_pending:
            timed_pending.sort(key=lambda x: x[0])
            return timed_pending[0][1]

        return pending[0]

    # --- Settings Operations ---
    def get_settings(self) -> Dict[str, Any]:
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    res = DEFAULT_SETTINGS.copy()
                    res.update(data)
                    return res
        except Exception as e:
            print(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS.copy()

    def save_settings(self, settings: Dict[str, Any]) -> bool:
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def update_setting(self, key: str, value: Any) -> bool:
        settings = self.get_settings()
        settings[key] = value
        return self.save_settings(settings)

    # --- Windows Autostart Operations ---
    def is_autostart_enabled(self) -> bool:
        """Check if Windows auto-start on boot is enabled via HKCU Run registry."""
        import sys
        if sys.platform != "win32":
            return bool(self.get_settings().get("autostart", False))
        try:
            import winreg
            reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, "WindowsDynamicIsland")
                return bool(val)
        except Exception:
            return bool(self.get_settings().get("autostart", False))

    def set_autostart(self, enable: bool) -> bool:
        """Enable or disable Windows auto-start on boot via HKCU Run registry."""
        import sys
        if sys.platform != "win32":
            return self.update_setting("autostart", enable)

        try:
            import winreg
            from pathlib import Path
            reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            reg_name = "WindowsDynamicIsland"

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE) as key:
                if enable:
                    python_dir = Path(sys.executable).parent
                    pythonw = python_dir / "pythonw.exe"
                    if not pythonw.exists():
                        pythonw = Path(sys.executable)

                    base_dir = Path(__file__).resolve().parent
                    target_file = base_dir / "main.pyw"
                    if not target_file.exists():
                        target_file = base_dir / "main.py"

                    cmd = f'"{pythonw}" "{target_file}"'
                    winreg.SetValueEx(key, reg_name, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(key, reg_name)
                    except FileNotFoundError:
                        pass
            self.update_setting("autostart", enable)
            return True
        except Exception as e:
            print(f"Error setting autostart registry: {e}")
            return False

    # --- Memo Operations ---
    def get_memo(self) -> str:
        try:
            if MEMO_FILE.exists():
                with open(MEMO_FILE, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            print(f"Error loading memo: {e}")
        return ""

    def save_memo(self, text: str) -> bool:
        try:
            with open(MEMO_FILE, "w", encoding="utf-8") as f:
                f.write(text)
            return True
        except Exception as e:
            print(f"Error saving memo: {e}")
            return False

    # --- Music Playlist Operations ---
    def get_playlist(self) -> List[Dict[str, Any]]:
        try:
            if PLAYLIST_FILE.exists():
                with open(PLAYLIST_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading playlist: {e}")
        return []

    def save_playlist(self, playlist: List[Dict[str, Any]]) -> bool:
        try:
            with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(playlist, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving playlist: {e}")
            return False

# Global instance
storage = StorageManager()


def get_habit_presentation(habit_data: dict) -> dict:
    """
    Returns presentation details for any habit:
    - icon: emoji (💧, 🚶, 👀, 🏃, 💊, 🍎, 🌙, 🎯, etc.)
    - unit: '杯' for water, '次' for others
    - action_text: '喝了一杯', '完成拉伸', '完成打卡', etc.
    - title: habit title string
    - color: theme accent color (#38BDF8 for water, #34D399 for stretch, etc.)
    """
    if not isinstance(habit_data, dict):
        return {
            "icon": "🎯",
            "unit": "次",
            "action_text": "打卡完成",
            "title": "健康习惯打卡",
            "color": "#38BDF8",
        }

    title = habit_data.get("title", "习惯提醒")
    h_type = str(habit_data.get("type", "")).lower()

    if h_type == "water" or "水" in title:
        icon = "💧"
        unit = "杯"
        action_text = "喝了一杯"
        color = "#38BDF8"
    elif h_type in ("stretch", "walk", "break") or any(k in title for k in ("拉伸", "起身", "活动", "走动", "散步", "站立")):
        icon = "🚶"
        unit = "次"
        action_text = "完成拉伸"
        color = "#34D399"
    elif h_type in ("eye", "vision") or any(k in title for k in ("眼", "视力", "眺望")):
        icon = "👀"
        unit = "次"
        action_text = "眺望休息"
        color = "#60A5FA"
    elif h_type in ("med", "pill") or any(k in title for k in ("药", "吃药")):
        icon = "💊"
        unit = "次"
        action_text = "服药打卡"
        color = "#F472B6"
    elif h_type in ("run", "sport", "fitness") or any(k in title for k in ("跑", "运动", "健身", "锻炼")):
        icon = "🏃"
        unit = "次"
        action_text = "完成锻炼"
        color = "#FB923C"
    elif any(k in title for k in ("睡", "休息", "午休")):
        icon = "🌙"
        unit = "次"
        action_text = "打卡休息"
        color = "#A78BFA"
    else:
        found_emoji = None
        for ch in title:
            if ord(ch) > 0x1F300:
                found_emoji = ch
                break
        icon = found_emoji or "🎯"
        unit = "次"
        action_text = "打卡完成"
        color = "#38BDF8"

    return {
        "icon": icon,
        "unit": unit,
        "action_text": action_text,
        "title": title,
        "color": color,
    }

