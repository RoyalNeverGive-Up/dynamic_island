import json
import uuid
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from config import (
    TODOS_FILE, SETTINGS_FILE, MEMO_FILE, PLAYLIST_FILE,
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


class StorageManager:
    def __init__(self):
        self._ensure_files()

    def _ensure_files(self):
        if not SETTINGS_FILE.exists():
            self.save_settings(DEFAULT_SETTINGS)

        if not TODOS_FILE.exists():
            now = datetime.now()
            # Initial sample todos with weekly recurrence demonstration
            sample_todos = [
                {
                    "id": str(uuid.uuid4()),
                    "title": "每周一项目周会 🚀",
                    "description": "整理更新日志，同步本周迭代目标",
                    "priority": "high",
                    "category": "工作",
                    "due_time": calculate_next_occurrence(REPEAT_WEEKLY, [1], "09:30", now) or (now + timedelta(days=1)).strftime("%Y-%m-%d 09:30"),
                    "reminder_enabled": True,
                    "repeat_type": REPEAT_WEEKLY,
                    "repeat_days": [1],
                    "repeat_time": "09:30",
                    "reminded": False,
                    "completed": False,
                    "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "completed_at": None,
                },
                {
                    "id": str(uuid.uuid4()),
                    "title": "欢迎体验 Windows 灵动岛！✨",
                    "description": "点击胶囊展开面板，支持代办、每周重复提醒、本地音乐播放与监控",
                    "priority": "medium",
                    "category": "工作",
                    "due_time": (now + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M"),
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
                    "title": "每天下午喝水与运动 💧",
                    "description": "保持充沛精力，劳逸结合",
                    "priority": "low",
                    "category": "健康",
                    "due_time": calculate_next_occurrence(REPEAT_DAILY, [1, 2, 3, 4, 5, 6, 7], "15:00", now) or (now + timedelta(hours=2)).strftime("%Y-%m-%d 15:00"),
                    "reminder_enabled": True,
                    "repeat_type": REPEAT_DAILY,
                    "repeat_days": [1, 2, 3, 4, 5, 6, 7],
                    "repeat_time": "15:00",
                    "reminded": False,
                    "completed": False,
                    "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "completed_at": None,
                }
            ]
            self.save_todos(sample_todos)

        if not MEMO_FILE.exists():
            self.save_memo("💡 灵动便签：随手记录你的灵感、常用链接或备忘信息...\n- 支持实时自动保存\n- 随取随用")

        if not PLAYLIST_FILE.exists():
            self.save_playlist([])

    # --- Todo Operations ---
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

        # If repeat is enabled, ensure due_time matches next occurrence if not provided
        if repeat_type and repeat_type != REPEAT_NONE and repeat_time:
            calculated_due = calculate_next_occurrence(repeat_type, repeat_days or [], repeat_time, now)
            if calculated_due:
                due_time = calculated_due
                reminder_enabled = True

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
            "repeat_time": repeat_time.strip(),
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
        todos = self.get_todos()
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        for todo in todos:
            if todo["id"] == todo_id:
                rtype = todo.get("repeat_type", REPEAT_NONE)
                # If currently not completed and is a recurring task,
                # mark this iteration done and immediately roll forward to next occurrence!
                if not todo.get("completed", False) and rtype != REPEAT_NONE and todo.get("repeat_time"):
                    next_due = calculate_next_occurrence(
                        rtype,
                        todo.get("repeat_days", []),
                        todo.get("repeat_time", ""),
                        now
                    )
                    if next_due:
                        todo["due_time"] = next_due
                        todo["reminded"] = False
                        todo["completed"] = False
                        todo["completed_at"] = now_str
                        self.save_todos(todos)
                        return True

                # Standard non-repeating toggle
                todo["completed"] = not todo["completed"]
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
