import unittest
import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

from datetime import datetime, timedelta
from PyQt6.QtWidgets import QApplication

# Ensure QApplication exists for Qt signals & widgets
app = QApplication.instance() or QApplication([])

from storage import (
    StorageManager, calculate_next_occurrence, format_repeat_display, parse_natural_time
)
from config import REPEAT_NONE, REPEAT_DAILY, REPEAT_WEEKLY, REPEAT_WORKDAY
from pomodoro_service import PomodoroService
from system_monitor import SystemMonitor
from music_service import MusicService
from ui.tabs.todo_edit_dialog import TodoEditDialog

class TestDynamicIsland(unittest.TestCase):
    def setUp(self):
        self.storage = StorageManager()

    def test_01_todo_crud(self):
        # 1. Create
        title = "自动化测试代办任务"
        new_todo = self.storage.add_todo(
            title=title,
            description="测试用例描述",
            priority="high",
            category="工作",
            due_time="2026-11-10 18:00"
        )
        self.assertIsNotNone(new_todo["id"])
        self.assertEqual(new_todo["title"], title)
        self.assertEqual(new_todo["priority"], "high")

        # 2. Read
        todos = self.storage.get_todos()
        found = any(t["id"] == new_todo["id"] for t in todos)
        self.assertTrue(found)

        # 3. Update
        updated = self.storage.update_todo(new_todo["id"], {"title": "已修改的代办名称", "priority": "low"})
        self.assertTrue(updated)
        todos = self.storage.get_todos()
        target = next(t for t in todos if t["id"] == new_todo["id"])
        self.assertEqual(target["title"], "已修改的代办名称")
        self.assertEqual(target["priority"], "low")

        # 4. Toggle Complete
        is_completed = self.storage.toggle_todo(new_todo["id"])
        self.assertTrue(is_completed)

        # 5. Delete
        deleted = self.storage.delete_todo(new_todo["id"])
        self.assertTrue(deleted)
        todos = self.storage.get_todos()
        self.assertFalse(any(t["id"] == new_todo["id"] for t in todos))

    def test_02_weekly_recurring_reminder(self):
        now = datetime(2026, 11, 10, 14, 0) # Tuesday
        # Tuesday is weekday 2
        # Next occurrence of Wednesday (3) at 10:00 should be tomorrow (Nov 11 10:00)
        next_due = calculate_next_occurrence(REPEAT_WEEKLY, [3], "10:00", base_dt=now)
        self.assertEqual(next_due, "2026-11-11 10:00")

        # Next occurrence of Monday (1) at 09:30 should be next week Monday (Nov 16 09:30)
        next_mon = calculate_next_occurrence(REPEAT_WEEKLY, [1], "09:30", base_dt=now)
        self.assertEqual(next_mon, "2026-11-16 09:30")

        # Create a weekly recurring todo
        rec_todo = self.storage.add_todo(
            title="每周三下午开会",
            repeat_type=REPEAT_WEEKLY,
            repeat_days=[3],
            repeat_time="15:00"
        )
        self.assertEqual(rec_todo["repeat_type"], REPEAT_WEEKLY)
        self.assertIn("🔁 每周三 15:00", format_repeat_display(rec_todo))

        # Toggling a recurring task should roll it forward to the next scheduled date
        old_due = rec_todo["due_time"]
        self.storage.toggle_todo(rec_todo["id"])
        todos = self.storage.get_todos()
        t = next(x for x in todos if x["id"] == rec_todo["id"])
        # Should not be completed forever, should stay pending with updated due_time!
        self.assertFalse(t["completed"])
        self.assertIsNotNone(t["due_time"])

        self.storage.delete_todo(rec_todo["id"])

    def test_03_music_service(self):
        music = MusicService()
        self.assertIsNotNone(music.player)
        self.assertIsNotNone(music.audio_output)

        # Test volume control
        music.set_volume(85)
        self.assertEqual(music.get_volume(), 85)

        # Test mode toggle
        init_mode = music.get_mode()
        new_mode = music.toggle_mode()
        self.assertNotEqual(init_mode, new_mode)

    def test_04_pomodoro_service(self):
        service = PomodoroService()
        self.assertEqual(service.current_mode, PomodoroService.MODE_WORK)
        service.start()
        self.assertTrue(service.is_running)
        service.pause()
        self.assertFalse(service.is_running)

        service.set_mode(PomodoroService.MODE_SHORT_BREAK)
        self.assertEqual(service.current_mode, PomodoroService.MODE_SHORT_BREAK)
        self.assertEqual(service.remaining_seconds, 5 * 60)

    def test_05_system_monitor(self):
        monitor = SystemMonitor()
        received = []
        monitor.stats_updated.connect(lambda stats: received.append(stats))
        monitor._collect_stats()
        self.assertGreater(len(received), 0)
        stats = received[0]
        self.assertIn("cpu", stats)
        self.assertIn("mem", stats)
        self.assertIn("disk", stats)

    def test_06_memo_storage(self):
        orig_memo = self.storage.get_memo()
        test_text = "临时测试便签"
        self.storage.save_memo(test_text)
        self.assertEqual(self.storage.get_memo(), test_text)
        self.storage.save_memo(orig_memo)

    def test_07_natural_time_parsing(self):
        title, due, rtype, rdays, rtime = parse_natural_time("明天下午3点半提交测试报告")
        self.assertEqual(title, "提交测试报告")
        self.assertTrue("15:30" in due)

        title2, due2, rtype2, rdays2, rtime2 = parse_natural_time("每周一09:30敏捷站会")
        self.assertEqual(title2, "敏捷站会")
        self.assertEqual(rtype2, REPEAT_WEEKLY)
        self.assertEqual(rdays2, [1])
        self.assertEqual(rtime2, "09:30")

    def test_08_todo_edit_dialog(self):
        sample_todo = {
            "id": "test-uuid-edit",
            "title": "测试编辑任务",
            "description": "这是备注",
            "priority": "high",
            "category": "工作",
            "due_time": "2026-11-20 15:30",
            "reminder_enabled": True,
            "repeat_type": REPEAT_WEEKLY,
            "repeat_days": [1, 3],
            "repeat_time": "15:30",
            "reminded": False,
            "completed": False
        }
        dialog = TodoEditDialog(sample_todo)
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.title_input.text(), "测试编辑任务")
        # Test simulated save
        dialog._save()
        self.assertIsNotNone(dialog.updated_data)
        self.assertEqual(dialog.updated_data["title"], "测试编辑任务")
        self.assertEqual(dialog.updated_data["repeat_type"], REPEAT_WEEKLY)

    def test_09_autostart_setting(self):
        from ui.tabs.settings_tab import SettingsTab
        # 1. Enable autostart
        ok = self.storage.set_autostart(True)
        self.assertTrue(ok)
        self.assertTrue(self.storage.is_autostart_enabled())

        # 2. Verify UI tab reflect state
        tab = SettingsTab()
        self.assertTrue(tab.autostart_cb.isChecked())

        # 3. Disable autostart
        ok_off = self.storage.set_autostart(False)
        self.assertTrue(ok_off)
        self.assertFalse(self.storage.is_autostart_enabled())

        # 4. Verify UI tab toggle
        tab._on_autostart_toggled(False)
        self.assertFalse(self.storage.is_autostart_enabled())

    def test_10_edge_dragging_and_snapping(self):
        from ui.screen_utils import clamp_window_to_edges, get_screen_at_point
        from config import SHADOW_MARGIN, COMPACT_WIDTH, COMPACT_HEIGHT
        from PyQt6.QtCore import QPoint
        from PyQt6.QtWidgets import QApplication

        win_w = COMPACT_WIDTH + 2 * SHADOW_MARGIN
        win_h = COMPACT_HEIGHT + 2 * SHADOW_MARGIN

        for s in QApplication.screens():
            s_geom = s.geometry()
            center_pt = s_geom.center()

            # 1. Dragging to left edge
            intended_left = QPoint(s_geom.left() - 50, center_pt.y())
            clamped_left = clamp_window_to_edges(intended_left, win_w, win_h, intended_left, strict_contain=True)
            vis_left = clamped_left.x() + SHADOW_MARGIN
            self.assertEqual(vis_left, s_geom.left(), f"Visual left should touch {s_geom.left()}")

            # 2. Dragging to right edge
            intended_right = QPoint(s_geom.right() + 50, center_pt.y())
            clamped_right = clamp_window_to_edges(intended_right, win_w, win_h, intended_right, strict_contain=True)
            vis_right = clamped_right.x() + win_w - SHADOW_MARGIN
            self.assertEqual(vis_right, s_geom.right() + 1, f"Visual right should touch {s_geom.right() + 1}")

            # 3. Dragging to top edge
            intended_top = QPoint(center_pt.x(), s_geom.top() - 50)
            clamped_top = clamp_window_to_edges(intended_top, win_w, win_h, intended_top, strict_contain=True)
            vis_top = clamped_top.y() + SHADOW_MARGIN
            self.assertEqual(vis_top, s_geom.top(), f"Visual top should touch {s_geom.top()}")

            # 4. Dragging to bottom edge
            intended_bot = QPoint(center_pt.x(), s_geom.bottom() + 50)
            clamped_bot = clamp_window_to_edges(intended_bot, win_w, win_h, intended_bot, strict_contain=True)
            vis_bot = clamped_bot.y() + win_h - SHADOW_MARGIN
            self.assertEqual(vis_bot, s_geom.bottom() + 1, f"Visual bottom should touch {s_geom.bottom() + 1}")

    def test_11_target_geometry_multi_screen(self):
        from pomodoro_service import PomodoroService
        from system_monitor import SystemMonitor
        from music_service import MusicService
        from ui.island_window import IslandWindow
        from config import SHADOW_MARGIN, COMPACT_WIDTH, EXPANDED_WIDTH
        from PyQt6.QtWidgets import QApplication

        island = IslandWindow(PomodoroService(), SystemMonitor(), MusicService())

        for s in QApplication.screens():
            s_geom = s.geometry()
            # Set custom position touching top-left of this screen
            left_x = s_geom.left() - SHADOW_MARGIN
            top_y = s_geom.top() - SHADOW_MARGIN
            self.storage.update_setting("position_mode", "custom")
            self.storage.update_setting("custom_pos_x", left_x)
            self.storage.update_setting("custom_pos_y", top_y)

            # Check compact geometry
            geom_compact = island.get_target_geometry(IslandWindow.STATE_COMPACT)
            self.assertEqual(geom_compact.x() + SHADOW_MARGIN, s_geom.left())
            self.assertEqual(geom_compact.y() + SHADOW_MARGIN, s_geom.top())

            # Check expanded geometry preserves screen boundaries
            geom_expanded = island.get_target_geometry(IslandWindow.STATE_EXPANDED)
            vis_expanded_left = geom_expanded.x() + SHADOW_MARGIN
            vis_expanded_right = geom_expanded.x() + geom_expanded.width() - SHADOW_MARGIN
            self.assertGreaterEqual(vis_expanded_left, s_geom.left())
            self.assertLessEqual(vis_expanded_right, s_geom.right() + 1)

if __name__ == "__main__":
    unittest.main()
