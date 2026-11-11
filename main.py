import sys
import traceback
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def show_error_dialog(error_msg: str, detail_tb: str = ""):
    """Display a native Windows error dialog with error details and save to error.log."""
    log_file = BASE_DIR / "error.log"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*64}\n")
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Windows 灵动岛运行异常:\n")
            f.write(detail_tb or error_msg)
            f.write(f"\n{'='*64}\n")
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            import ctypes
            MB_ICONERROR = 0x00000010
            MB_TOPMOST = 0x00040000
            display_text = (
                f"Windows 灵动岛启动遇到异常:\n\n"
                f"{error_msg}\n\n"
                f"详细错误日志已记录至:\n"
                f"{log_file}"
            )
            ctypes.windll.user32.MessageBoxW(0, display_text, "Windows 灵动岛 - 启动异常", MB_ICONERROR | MB_TOPMOST)
            return
        except Exception:
            pass
    print(f"[ERROR] {error_msg}\n{detail_tb}", file=sys.stderr)


# Global exception hook
def global_exception_hook(exctype, value, tb):
    tb_str = "".join(traceback.format_exception(exctype, value, tb))
    show_error_dialog(f"{exctype.__name__}: {value}", tb_str)
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = global_exception_hook


# Pre-flight check: ensure third-party dependencies are installed before importing them
def _ensure_dependencies():
    missing = []
    for pkg in ["PyQt6", "psutil"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        try:
            from bootstrap import install_missing_dependencies
            ok = install_missing_dependencies(missing)
            if not ok:
                show_error_dialog(f"缺少必要运行依赖: {', '.join(missing)}\n自动安装未成功，请检查网络后重试。")
                sys.exit(1)
        except Exception as e:
            show_error_dialog(f"依赖安装器异常: {e}", traceback.format_exc())
            sys.exit(1)

_ensure_dependencies()

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen

from config import DEFAULT_SETTINGS
from storage import storage
from reminder_service import ReminderService
from pomodoro_service import PomodoroService
from system_monitor import SystemMonitor
from music_service import MusicService
from ui.island_window import IslandWindow

def create_tray_icon() -> QIcon:
    """Generate a crisp, dynamic-island pill icon programmatically."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Outer pill
    painter.setBrush(QBrush(QColor(18, 20, 28)))
    painter.setPen(QPen(QColor(10, 132, 255), 3))
    painter.drawRoundedRect(4, 16, 56, 32, 16, 16)

    # Center glowing dot (island camera / sensor cue)
    painter.setBrush(QBrush(QColor(48, 209, 88)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(16, 26, 12, 12)

    # Right indicator
    painter.setBrush(QBrush(QColor(255, 159, 10)))
    painter.drawEllipse(36, 26, 12, 12)

    painter.end()
    return QIcon(pixmap)


def hide_console():
    """Hide the console window on Windows if started with python.exe without --debug flag."""
    if sys.platform == "win32" and "--debug" not in sys.argv and "--console" not in sys.argv:
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
        except Exception:
            pass


def main():
    try:
        hide_console()
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # Keep running in system tray
        app.setApplicationName("Windows 灵动岛")

        # Initialize Services
        pomodoro_service = PomodoroService()
        system_monitor = SystemMonitor()
        reminder_service = ReminderService()
        music_service = MusicService()

        # Create Island Window
        island = IslandWindow(pomodoro_service, system_monitor, music_service)
        island.show()

        # Connect Reminder Engine to Island Alert Banner
        reminder_service.reminder_triggered.connect(island.show_alert)

        # System Tray Integration
        tray_icon = QSystemTrayIcon(create_tray_icon(), app)
        tray_icon.setToolTip("Windows 灵动岛 · 待办、音乐与灵动中心")

        tray_menu = QMenu()

        action_expand = tray_menu.addAction("🏝️ 展开灵动中心")
        action_expand.triggered.connect(island.expand_to_dashboard)

        action_collapse = tray_menu.addAction("⌃ 收起为胶囊")
        action_collapse.triggered.connect(island.collapse_to_compact)

        tray_menu.addSeparator()

        def quick_add_todo():
            title, ok = QInputDialog.getText(None, "快速添加待办", "请输入待办任务标题:")
            if ok and title.strip():
                storage.add_todo(title=title.strip(), category="工作")
                island.compact_view.update_content()
                island.dashboard_view.todo_tab.load_todos()

        action_add = tray_menu.addAction("➕ 快速添加待办...")
        action_add.triggered.connect(quick_add_todo)

        action_pomo = tray_menu.addAction("🍅 切换番茄钟 (开始/暂停)")
        action_pomo.triggered.connect(pomodoro_service.toggle)

        action_music = tray_menu.addAction("🎵 切换音乐 (播放/暂停)")
        action_music.triggered.connect(music_service.toggle_play)

        tray_menu.addSeparator()

        action_quit = tray_menu.addAction("✕ 退出程序")
        action_quit.triggered.connect(app.quit)

        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #1A1D27;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 4px;
                color: #FFFFFF;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0A84FF;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.1);
                margin: 4px 6px;
            }
        """)

        tray_icon.setContextMenu(tray_menu)
        tray_icon.activated.connect(
            lambda reason: island.expand_to_dashboard() if reason == QSystemTrayIcon.ActivationReason.Trigger else None
        )
        tray_icon.show()

        # Show balloon notification on first startup
        tray_icon.showMessage(
            "Windows 灵动岛已启动",
            "悬浮于屏幕顶部，支持待办、每周提醒、本地音乐播放与专注时钟！",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

        sys.exit(app.exec())
    except Exception as e:
        tb_str = traceback.format_exc()
        show_error_dialog(f"程序初始化失败: {type(e).__name__}: {e}", tb_str)
        sys.exit(1)


if __name__ == "__main__":
    main()
