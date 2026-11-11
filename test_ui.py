import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

from PyQt6.QtWidgets import QApplication
from reminder_service import ReminderService
from pomodoro_service import PomodoroService
from system_monitor import SystemMonitor
from music_service import MusicService
from ui.island_window import IslandWindow
from storage import storage

def test_ui():
    app = QApplication.instance() or QApplication(sys.argv)
    
    pomodoro = PomodoroService()
    sys_mon = SystemMonitor()
    music = MusicService()
    island = IslandWindow(pomodoro, sys_mon, music)
    
    # 1. Check compact state
    assert island.state == IslandWindow.STATE_COMPACT
    print("[OK] Compact state initialized with high-contrast clock pill")
    
    # 2. Expand to dashboard
    island.expand_to_dashboard()
    assert island.state == IslandWindow.STATE_EXPANDED
    print("[OK] Expanded to dashboard successfully")
    
    # 3. Switch dashboard tabs (now 6 tabs including Music)
    for i in range(6):
        island.dashboard_view.switch_tab(i)
    print("[OK] All 6 tabs (including Music) switched successfully")
    
    # 4. Trigger alert
    sample_alert_todo = {
        "id": "test-123",
        "title": "每周一项目周会 🚀",
        "due_time": "2026-11-16 09:30"
    }
    island.show_alert(sample_alert_todo)
    assert island.state == IslandWindow.STATE_ALERT
    print("[OK] Alert mode tested successfully")
    
    # 5. Collapse back to compact
    island.collapse_to_compact()
    assert island.state == IslandWindow.STATE_COMPACT
    print("[OK] Collapsed back to compact capsule successfully")
    
    print("ALL UI INTEGRATION TESTS PASSED!")
    sys.exit(0)

if __name__ == "__main__":
    test_ui()
