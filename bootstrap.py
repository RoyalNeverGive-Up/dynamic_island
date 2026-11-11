# bootstrap.py - Autonomous Environment & Dependency Manager for Windows Dynamic Island
import sys
import os
import subprocess
import time
from pathlib import Path

# Windows mixed-DPI multi-monitor stabilization
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "Round"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

BASE_DIR = Path(__file__).resolve().parent
VENV_DIR = BASE_DIR / ".venv"

REQUIRED_PACKAGES = {
    "PyQt6": "PyQt6>=6.5.0",
    "psutil": "psutil>=5.9.0",
}

PIP_MIRRORS = [
    ("清华大学开源镜像 (Tsinghua)", "https://pypi.tuna.tsinghua.edu.cn/simple", "pypi.tuna.tsinghua.edu.cn"),
    ("阿里云镜像源 (Aliyun)", "https://mirrors.aliyun.com/pypi/simple/", "mirrors.aliyun.com"),
    ("腾讯云镜像源 (Tencent)", "https://mirrors.cloud.tencent.com/pypi/simple/", "mirrors.cloud.tencent.com"),
    ("华为云镜像源 (Huawei)", "https://repo.huaweicloud.com/repository/pypi/simple/", "repo.huaweicloud.com"),
    ("官方 PyPI 源 (Official)", "https://pypi.org/simple", "pypi.org"),
]


def is_in_venv() -> bool:
    """Check if running inside a virtual environment."""
    return (
        getattr(sys, "base_prefix", sys.prefix) != sys.prefix
        or hasattr(sys, "real_prefix")
    )


def get_venv_python() -> Path:
    """Return python.exe path in the project virtual environment."""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def show_error_dialog(title: str, message: str, detail_tb: str = ""):
    """Display native Windows error dialog and record error to error.log."""
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
            display_text = f"{message}\n\n详细错误日志已记录至:\n{log_file}"
            ctypes.windll.user32.MessageBoxW(0, display_text, title, MB_ICONERROR | MB_TOPMOST)
            return
        except Exception:
            pass
    print(f"[ERROR] {message}\n{detail_tb}", file=sys.stderr)


def ensure_virtual_environment():
    """Ensure project virtual environment exists. If not in venv, re-execute within it."""
    if is_in_venv():
        return

    venv_python = get_venv_python()
    if not venv_python.exists():
        print("\n" + "=" * 64)
        print(" 🏝️  Windows 灵动岛 · 首次环境初始化")
        print("=" * 64)
        print(" 正在为您创建独立的本地虚拟环境 (.venv)...")
        print(" （此操作仅初次运行需要，不影响全局系统，请稍候约 5~15 秒）\n")

        try:
            res = subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=False)
            if res.returncode != 0 or not venv_python.exists():
                show_error_dialog(
                    "Windows 灵动岛 - 环境创建失败",
                    "未能成功创建独立虚拟环境 (.venv)。\n请检查当前文件夹权限或磁盘空间后重试。"
                )
                sys.exit(1)
        except Exception as e:
            import traceback
            show_error_dialog("Windows 灵动岛 - 虚拟环境创建异常", f"创建虚拟环境失败: {e}", traceback.format_exc())
            sys.exit(1)

        print(" [✓] 独立虚拟环境创建成功！\n")

    # Delegate execution to virtual environment python
    args = [str(venv_python), str(Path(__file__).resolve())] + sys.argv[1:]
    try:
        ret = subprocess.run(args)
        sys.exit(ret.returncode)
    except Exception as e:
        import traceback
        show_error_dialog("Windows 灵动岛 - 启动转发异常", f"转交虚拟环境失败: {e}", traceback.format_exc())
        sys.exit(1)


def check_missing_dependencies():
    """Check if all required dependencies are installed."""
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return missing


def install_missing_dependencies(missing_pkgs: list) -> bool:
    """Auto-install dependencies using pip with multiple high-speed mirrors."""
    print("\n" + "=" * 64)
    print(" 🏝️  Windows 灵动岛 · 核心组件自动安装")
    print("=" * 64)
    print(" 检测到环境缺少以下必要组件:")
    for pkg in missing_pkgs:
        print(f"   -> {pkg} ({REQUIRED_PACKAGES.get(pkg, pkg)})")
    print("\n 正在连接国内超高速镜像源下载，请稍候...")
    print(" （通常仅需 10~30 秒，无需手动干预）")
    print("-" * 64)

    req_file = BASE_DIR / "requirements.txt"
    if req_file.exists():
        install_targets = ["-r", str(req_file)]
    else:
        install_targets = [REQUIRED_PACKAGES[pkg] for pkg in missing_pkgs]

    installed = False
    for mirror_name, mirror_url, host in PIP_MIRRORS:
        print(f" 正在尝试连接 [{mirror_name}] 进行安装...")
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--prefer-binary",
            "-i", mirror_url,
            "--trusted-host", host,
        ] + install_targets

        try:
            ret = subprocess.run(cmd, check=False)
            if ret.returncode == 0:
                installed = True
                break
            else:
                print(f" ⚠️  通过 [{mirror_name}] 下载未完成，正在切换备用源...")
        except Exception as e:
            print(f" ⚠️  调用 pip 发生异常: {e}，正在尝试备用源...")

    if not installed:
        print("\n" + "=" * 64)
        print(" ❌ 依赖自动安装失败！")
        print(" 可能原因: 电脑未联网、网络连接超时或防火墙拦截。")
        print(" 解决办法: 检查网络连接后，再次运行 run.bat 重试。")
        print("=" * 64 + "\n")
        show_error_dialog(
            "Windows 灵动岛 - 依赖安装失败",
            f"缺少运行依赖: {', '.join(missing_pkgs)}\n\n由于网络连接超时或权限受限未能自动安装成功。\n建议检查网络连接后重新运行 run.bat 重试。"
        )
        return False

    print("-" * 64)
    print(" [✓] 所有核心组件已全部安装就绪！\n")
    return True


def main():
    try:
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8")
            except Exception:
                pass

        # 1. Ensure isolated virtual environment
        ensure_virtual_environment()

        # 2. Check and auto-install missing packages
        missing = check_missing_dependencies()
        if missing:
            ok = install_missing_dependencies(missing)
            if not ok:
                sys.exit(1)

        # If invoked with --check-only, we are done
        if "--check-only" in sys.argv:
            sys.exit(0)

        # If launched directly without run.bat, execute main.py
        main_file = BASE_DIR / "main.py"
        subprocess.run([sys.executable, str(main_file)] + sys.argv[1:])
        sys.exit(0)

    except SystemExit:
        raise
    except Exception as e:
        import traceback
        show_error_dialog("Windows 灵动岛 - 启动异常", f"引导器遇到未处理异常: {e}", traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
