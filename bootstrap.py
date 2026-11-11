# bootstrap.py - Environment & Dependency Auto-Installer for Windows Dynamic Island
import sys
import os

# Windows mixed-DPI multi-monitor stabilization
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "Round"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

import subprocess
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

REQUIRED_PACKAGES = {
    "PyQt6": "PyQt6>=6.5.0",
    "psutil": "psutil>=5.9.0",
}

# Fast mirrors for reliable & ultra-fast installation
PIP_MIRRORS = [
    ("清华大学镜像源", "https://pypi.tuna.tsinghua.edu.cn/simple", "pypi.tuna.tsinghua.edu.cn"),
    ("阿里云镜像源", "https://mirrors.aliyun.com/pypi/simple/", "mirrors.aliyun.com"),
    ("官方 PyPI 源", "https://pypi.org/simple", "pypi.org"),
]


def check_missing_dependencies():
    """Return list of missing package keys from REQUIRED_PACKAGES."""
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return missing


def get_pythonw_path() -> Path:
    """Find pythonw.exe path for no-console background execution."""
    python_dir = Path(sys.executable).parent
    pythonw = python_dir / "pythonw.exe"
    if pythonw.exists():
        return pythonw
    return Path(sys.executable)


def enable_console():
    """Ensure a visible console exists so the user sees the installation progress."""
    if sys.platform == "win32":
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if not hwnd:
                ctypes.windll.kernel32.AllocConsole()
                try:
                    sys.stdout = open("CONOUT$", "w", encoding="utf-8")
                    sys.stderr = open("CONOUT$", "w", encoding="utf-8")
                except Exception:
                    pass
            else:
                ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW = 5
        except Exception:
            pass


def show_error_dialog(title: str, message: str, detail_tb: str = ""):
    """Display a native Windows error dialog with error details and save to error.log."""
    log_file = BASE_DIR / "error.log"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*64}\n")
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {title}:\n")
            f.write(detail_tb or message)
            f.write(f"\n{'='*64}\n")
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            import ctypes
            MB_ICONERROR = 0x00000010
            MB_TOPMOST = 0x00040000
            display_text = f"{message}\n\n详细报错信息已记录至:\n{log_file}"
            ctypes.windll.user32.MessageBoxW(0, display_text, title, MB_ICONERROR | MB_TOPMOST)
            return
        except Exception:
            pass
    print(f"[ERROR] {message}\n{detail_tb}", file=sys.stderr)


def install_missing_dependencies(missing_pkgs: list) -> bool:
    """Automatically install missing packages using pip with mirror fallbacks."""
    enable_console()

    print("\n" + "=" * 64)
    print(" 🏝️  Windows 灵动岛 · 首次运行环境自检")
    print("=" * 64)
    print(" 检测到新电脑/当前环境缺少以下运行依赖:")
    for pkg in missing_pkgs:
        print(f"   -> {pkg} ({REQUIRED_PACKAGES.get(pkg, pkg)})")
    print("\n 正在自动为您下载并安装必要组件，请稍候...")
    print(" （通常需要 10~30 秒，请勿关闭本窗口）")
    print("-" * 64)

    req_specs = [REQUIRED_PACKAGES[pkg] for pkg in missing_pkgs]

    installed = False
    for mirror_name, mirror_url, host in PIP_MIRRORS:
        print(f" 正在尝试连接 [{mirror_name}] 进行安装...")
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--prefer-binary",
            "-i", mirror_url,
            "--trusted-host", host,
        ] + req_specs

        try:
            ret = subprocess.run(cmd, check=False)
            if ret.returncode == 0:
                installed = True
                break
            else:
                print(f" ⚠️  通过 [{mirror_name}] 安装失败，正在尝试备用镜像源...")
        except Exception as e:
            print(f" ⚠️  执行 pip 出错: {e}，正在尝试备用源...")

    if not installed:
        print("\n" + "=" * 64)
        print(" ❌ 依赖自动安装失败！")
        print(" 可能原因: 电脑未联网、网络连接超时或 pip 权限受限。")
        print(" 建议排查方法:")
        print("   1. 检查电脑网络连接是否正常。")
        print("   2. 手动打开终端执行: pip install -r requirements.txt")
        print("=" * 64 + "\n")
        show_error_dialog(
            "Windows 灵动岛 - 依赖安装失败",
            f"缺少必要运行依赖: {', '.join(missing_pkgs)}\n\n由于网络连接超时或权限受限未能自动安装成功。\n建议检查网络连接，或在当前目录终端手动运行: pip install -r requirements.txt"
        )
        return False

    print("-" * 64)
    print(" [✓] 所有必要依赖已安装成功！")
    print(" 正在为您启动 Windows 灵动岛...")
    print("=" * 64 + "\n")
    time.sleep(1)
    return True


def launch_island():
    """Launch main.py in detached background mode without console."""
    pythonw = get_pythonw_path()
    main_file = BASE_DIR / "main.pyw"
    if not main_file.exists():
        main_file = BASE_DIR / "main.py"

    try:
        if sys.platform == "win32":
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            subprocess.Popen(
                [str(pythonw), str(main_file)],
                cwd=str(BASE_DIR),
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                close_fds=True
            )
        else:
            subprocess.Popen([sys.executable, str(main_file)], cwd=str(BASE_DIR))
    except Exception as e:
        import traceback
        show_error_dialog("Windows 灵动岛 - 进程启动异常", f"启动主进程失败: {e}", traceback.format_exc())
        raise


def main():
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")

        missing = check_missing_dependencies()
        if missing:
            ok = install_missing_dependencies(missing)
            if not ok:
                sys.exit(1)

        # Launch island in background
        launch_island()
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        show_error_dialog("Windows 灵动岛 - 启动异常", f"引导器遇到未处理异常: {e}", traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
