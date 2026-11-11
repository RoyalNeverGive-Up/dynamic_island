from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame
)
from PyQt6.QtCore import Qt
from ui.styles import THEME
from system_monitor import SystemMonitor

class MetricCard(QFrame):
    def __init__(self, title: str, icon: str, accent_color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskCard")
        self.accent_color = accent_color
        self._init_ui(title, icon)

    def _init_ui(self, title: str, icon: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header
        top_row = QHBoxLayout()
        icon_lbl = QLabel(f"{icon}  {title}")
        icon_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        top_row.addWidget(icon_lbl)

        top_row.addStretch()

        self.value_lbl = QLabel("0%")
        self.value_lbl.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {self.accent_color};")
        top_row.addWidget(self.value_lbl)

        layout.addLayout(top_row)

        # Progress bar
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        self.bar.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: {self.accent_color};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.bar)

        # Subtitle info
        self.sub_lbl = QLabel("")
        self.sub_lbl.setStyleSheet(f"font-size: 11px; color: {THEME['text_muted']};")
        layout.addWidget(self.sub_lbl)

    def update_data(self, pct: float, subtitle: str = ""):
        self.value_lbl.setText(f"{pct:.1f}%")
        self.bar.setValue(int(pct))
        if subtitle:
            self.sub_lbl.setText(subtitle)


class SystemTab(QWidget):
    def __init__(self, system_monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self.monitor = system_monitor
        self._init_ui()
        self.monitor.stats_updated.connect(self._on_stats_updated)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("⚡ 硬件实时状态")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(header)

        # CPU Card
        self.cpu_card = MetricCard("处理器 (CPU)", "💻", THEME['accent_cyan'])
        layout.addWidget(self.cpu_card)

        # Memory Card
        self.mem_card = MetricCard("运行内存 (RAM)", "🧠", THEME['accent_purple'])
        layout.addWidget(self.mem_card)

        # Disk Card
        self.disk_card = MetricCard("系统存储 (Disk)", "💾", THEME['accent_orange'])
        layout.addWidget(self.disk_card)

        layout.addStretch()

    def _on_stats_updated(self, stats: dict):
        cpu_pct = stats.get("cpu", 0.0)
        cpu_cores = stats.get("cpu_count", 0)
        self.cpu_card.update_data(cpu_pct, f"逻辑核心: {cpu_cores} 线程 · 负载稳定")

        mem_pct = stats.get("mem", 0.0)
        mem_used = stats.get("mem_used_gb", 0.0)
        mem_total = stats.get("mem_total_gb", 0.0)
        self.mem_card.update_data(mem_pct, f"已用 {mem_used} GB / 总共 {mem_total} GB")

        disk_pct = stats.get("disk", 0.0)
        self.disk_card.update_data(disk_pct, "主系统盘空间状态良好")
