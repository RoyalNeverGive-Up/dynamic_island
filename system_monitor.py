from PyQt6.QtCore import QObject, QTimer, pyqtSignal
import psutil

class SystemMonitor(QObject):
    stats_updated = pyqtSignal(dict)  # {"cpu": float, "mem": float, "mem_used_gb": float, "mem_total_gb": float, "disk": float}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.timer.setInterval(1500)
        self.timer.timeout.connect(self._collect_stats)
        # prime cpu measurement
        psutil.cpu_percent(interval=None)
        self.timer.start()

    def _collect_stats(self):
        try:
            cpu_pct = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            mem_pct = mem.percent
            mem_used_gb = round(mem.used / (1024 ** 3), 1)
            mem_total_gb = round(mem.total / (1024 ** 3), 1)

            disk = psutil.disk_usage('/')
            disk_pct = disk.percent

            cpu_count = psutil.cpu_count(logical=True)

            self.stats_updated.emit({
                "cpu": cpu_pct,
                "cpu_count": cpu_count,
                "mem": mem_pct,
                "mem_used_gb": mem_used_gb,
                "mem_total_gb": mem_total_gb,
                "disk": disk_pct,
            })
        except Exception as e:
            print(f"Error in SystemMonitor: {e}")
