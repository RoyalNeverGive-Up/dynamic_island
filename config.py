import os
import sys
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

TODOS_FILE = DATA_DIR / "todos.json"
ALARMS_FILE = DATA_DIR / "alarms.json"
HABITS_FILE = DATA_DIR / "habits.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
MEMO_FILE = DATA_DIR / "memo.txt"
PLAYLIST_FILE = DATA_DIR / "playlist.json"

# Default Island Dimensions
SHADOW_MARGIN = 12

COMPACT_WIDTH = 360
COMPACT_HEIGHT = 42
COMPACT_RADIUS = 21

ALERT_WIDTH = 420
ALERT_HEIGHT = 76
ALERT_RADIUS = 22

EXPANDED_WIDTH = 480
EXPANDED_HEIGHT = 640
EXPANDED_RADIUS = 24

# Default Settings
DEFAULT_SETTINGS = {
    "always_on_top": True,
    "sound_enabled": True,
    "autostart": False,
    "position_mode": "top_center",  # "top_center", "top_left", "top_right", "custom"
    "custom_pos_x": None,
    "custom_pos_y": None,
    "compact_show_cpu": True,
    "compact_show_time": True,
    "auto_collapse": False,
    "theme_opacity": 0.95,
    "music_volume": 70,
}

# Priorities
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

PRIORITY_CONFIG = {
    PRIORITY_HIGH: {"label": "紧急", "color": "#FF453A", "bg": "rgba(255, 69, 58, 0.25)"},
    PRIORITY_MEDIUM: {"label": "重要", "color": "#FF9F0A", "bg": "rgba(255, 159, 10, 0.25)"},
    PRIORITY_LOW: {"label": "普通", "color": "#30D158", "bg": "rgba(48, 209, 88, 0.25)"},
}

# Categories
CATEGORIES = ["工作", "生活", "学习", "健康", "随记"]

# Recurrence Constants
REPEAT_NONE = "none"
REPEAT_DAILY = "daily"
REPEAT_WEEKLY = "weekly"
REPEAT_WORKDAY = "workday"

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
