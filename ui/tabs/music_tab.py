import os
import math
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QScrollArea, QFrame, QFileDialog, QMessageBox,
    QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QCursor, QFont

from music_service import MusicService, SUPPORTED_EXTENSIONS
from ui.styles import THEME
from ui.components.icons import (
    make_play_icon, make_pause_icon, make_prev_icon,
    make_next_icon, make_volume_icon
)


def ms_to_str(ms: int) -> str:
    total_secs = max(0, ms // 1000)
    mins = total_secs // 60
    secs = total_secs % 60
    return f"{mins:02d}:{secs:02d}"


class VinylWidget(QWidget):
    """Sleek animated vinyl record that rotates continuously during playback."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(54, 54)
        self.angle = 0.0
        self.is_playing = False

        self.timer = QTimer(self)
        self.timer.setInterval(33)  # ~30 FPS
        self.timer.timeout.connect(self._on_tick)

    def set_playing(self, playing: bool):
        self.is_playing = playing
        if playing:
            if not self.timer.isActive():
                self.timer.start()
        else:
            self.timer.stop()
        self.update()

    def _on_tick(self):
        self.angle = (self.angle + 2.0) % 360.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        r = min(cx, cy) - 2.0

        p.save()
        p.translate(cx, cy)
        p.rotate(self.angle)

        # 1. Outer vinyl base
        p.setPen(QPen(QColor(255, 255, 255, 24), 1.0))
        p.setBrush(QBrush(QColor(18, 22, 34)))
        p.drawEllipse(QRectF(-r, -r, r * 2, r * 2))

        # 2. Vinyl circular sound grooves
        for gr in [r * 0.86, r * 0.72, r * 0.58]:
            p.setPen(QPen(QColor(255, 255, 255, 12), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(-gr, -gr, gr * 2, gr * 2))

        # 3. Center gradient label (Apple Music cyan)
        lr = r * 0.40
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(14, 165, 233)))
        p.drawEllipse(QRectF(-lr, -lr, lr * 2, lr * 2))

        # 4. Spindle hole
        hr = r * 0.12
        p.setBrush(QBrush(QColor(15, 23, 42)))
        p.drawEllipse(QRectF(-hr, -hr, hr * 2, hr * 2))

        p.restore()
        p.end()


class AudioWaveWidget(QWidget):
    """Dynamic animated 4-bar equalizer visualizer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 18)
        self.is_playing = False
        self.tick = 0

        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._on_tick)

    def set_playing(self, playing: bool):
        self.is_playing = playing
        if playing:
            if not self.timer.isActive():
                self.timer.start()
        else:
            self.timer.stop()
        self.update()

    def _on_tick(self):
        self.tick = (self.tick + 1) % 120
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#38BDF8")))

        num_bars = 4
        bar_w = 2.8
        gap = 2.4
        max_h = 13.0
        base_h = 3.0

        for i in range(num_bars):
            if self.is_playing:
                phase = self.tick * 0.32 + i * 1.3
                h = base_h + (max_h - base_h) * (0.5 + 0.5 * math.sin(phase))
            else:
                h = base_h
            x = i * (bar_w + gap) + 1.0
            y = (self.height() - h) / 2.0
            p.drawRoundedRect(QRectF(x, y, bar_w, h), 1.4, 1.4)
        p.end()


class ClickableSlider(QSlider):
    """Smooth horizontal slider that instantly seeks directly to clicked position."""

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.orientation() == Qt.Orientation.Horizontal and self.width() > 0:
                pos_x = event.position().x()
                pct = max(0.0, min(1.0, pos_x / self.width()))
                val = int(self.minimum() + pct * (self.maximum() - self.minimum()))
                self.setValue(val)
                self.sliderMoved.emit(val)
        super().mousePressEvent(event)


class PlaylistItemWidget(QFrame):
    """Modern interactive playlist row item with live waveform and quick play/delete."""

    play_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)

    def __init__(self, index: int, track: dict, is_current: bool = False, is_playing: bool = False, parent=None):
        super().__init__(parent)
        self.index = index
        self.track = track
        self.is_current = is_current
        self.is_playing = is_playing

        self.setObjectName("ActiveTrackCard" if self.is_current else "TaskCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(10)

        # 1. State indicator (Animated Wave when playing, or Track Number)
        self.indicator_box = QWidget()
        self.indicator_box.setFixedWidth(24)
        ind_layout = QHBoxLayout(self.indicator_box)
        ind_layout.setContentsMargins(0, 0, 0, 0)
        ind_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self.is_current and self.is_playing:
            self.wave = AudioWaveWidget(self)
            self.wave.set_playing(True)
            ind_layout.addWidget(self.wave)
        else:
            idx_str = f"{self.index + 1:02d}" if self.index < 99 else f"{self.index + 1}"
            self.num_lbl = QLabel(idx_str)
            self.num_lbl.setStyleSheet(f"""
                font-size: 11px;
                font-weight: {'bold' if self.is_current else 'normal'};
                color: {'#38BDF8' if self.is_current else '#64748B'};
            """)
            ind_layout.addWidget(self.num_lbl)

        layout.addWidget(self.indicator_box)

        # 2. Track Title & Format Badge
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setSpacing(6)

        title_text = self.track.get("title", "未知曲目")
        self.title_lbl = QLabel(title_text)
        self.title_lbl.setStyleSheet(f"""
            font-size: 13px;
            font-weight: {'700' if self.is_current else '500'};
            color: {'#38BDF8' if self.is_current else '#FFFFFF'};
        """)
        self.title_lbl.setToolTip(f"{title_text}\n路径: {self.track.get('path', '')}")
        title_row.addWidget(self.title_lbl, 1)

        # Audio file format badge (e.g. MP3, FLAC, WAV)
        ext = Path(self.track.get("filename", "")).suffix.replace(".", "").upper()
        if ext:
            ext_badge = QLabel(ext)
            ext_badge.setStyleSheet("""
                font-size: 9px;
                font-weight: bold;
                color: #38BDF8;
                background: rgba(56, 189, 248, 0.14);
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 4px;
                padding: 1px 4px;
            """)
            title_row.addWidget(ext_badge)

        title_box.addLayout(title_row)
        layout.addLayout(title_box, 1)

        # 3. Actions: Quick Play & Delete buttons
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(24, 24)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setToolTip("从播放列表中移除")
        del_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748B;
                border: none;
                font-size: 12px;
                border-radius: 4px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.22);
                color: #EF4444;
            }
        """)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.index))
        layout.addWidget(del_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.play_requested.emit(self.index)
            event.accept()
        else:
            super().mousePressEvent(event)


class MusicTab(QWidget):
    """High-contrast, drag-and-drop enabled Apple-style Music Player interface."""

    def __init__(self, music_service: MusicService, parent=None):
        super().__init__(parent)
        self.music = music_service
        self.user_is_seeking = False
        self.search_filter = ""
        self.rendered_count_limit = 80  # Render limit for instantaneous performance on 1000+ tracks

        self.setAcceptDrops(True)
        self._init_ui()
        self._connect_signals()
        self.reload_playlist()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(10)

        # 1. Top Bar
        top_bar = QHBoxLayout()
        title_box = QHBoxLayout()
        title_box.setSpacing(8)

        title_lbl = QLabel("🎵 本地音乐播放")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        title_box.addWidget(title_lbl)

        top_bar.addLayout(title_box)
        top_bar.addStretch()

        self.add_files_btn = QPushButton("➕ 添加歌曲")
        self.add_files_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_files_btn.setToolTip("支持添加音频文件，或直接将文件拖拽进窗口")
        self.add_files_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 8px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(56, 189, 248, 0.2);
                border-color: #38BDF8;
                color: #38BDF8;
            }
        """)
        self.add_files_btn.clicked.connect(self._choose_files)
        top_bar.addWidget(self.add_files_btn)

        self.add_folder_btn = QPushButton("📁 导入文件夹")
        self.add_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_folder_btn.setToolTip("选择整个音乐目录一键批量导入")
        self.add_folder_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 8px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(56, 189, 248, 0.2);
                border-color: #38BDF8;
                color: #38BDF8;
            }
        """)
        self.add_folder_btn.clicked.connect(self._choose_folder)
        top_bar.addWidget(self.add_folder_btn)

        main_layout.addLayout(top_bar)

        # 2. Now Playing Hero Card
        self.player_card = QFrame()
        self.player_card.setObjectName("MusicPlayerCard")
        card_layout = QVBoxLayout(self.player_card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        # Song Info Row: Vinyl Record + Titles + Mode Toggle
        song_info_row = QHBoxLayout()
        song_info_row.setSpacing(12)

        # Rotating Vinyl Record
        self.vinyl = VinylWidget(self)
        song_info_row.addWidget(self.vinyl)

        # Title & Subtitle
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title_header = QHBoxLayout()
        title_header.setSpacing(6)

        self.now_title_lbl = QLabel("未在播放音乐")
        self.now_title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #FFFFFF;")
        title_header.addWidget(self.now_title_lbl, 1)

        self.card_wave = AudioWaveWidget(self)
        title_header.addWidget(self.card_wave)

        title_box.addLayout(title_header)

        self.now_artist_lbl = QLabel("点击下方列表曲目或拖拽文件开始畅听")
        self.now_artist_lbl.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_box.addWidget(self.now_artist_lbl)

        song_info_row.addLayout(title_box, 1)

        # Mode button
        self.mode_btn = QPushButton(f"🔁 {self.music.get_mode()}")
        self.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_btn.setToolTip("切换播放模式: 列表循环 / 单曲循环 / 随机播放")
        self.mode_btn.setStyleSheet("""
            QPushButton {
                background: rgba(56, 189, 248, 0.12);
                color: #38BDF8;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 6px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background: rgba(56, 189, 248, 0.25);
                border-color: #38BDF8;
            }
        """)
        self.mode_btn.clicked.connect(self._toggle_mode)
        song_info_row.addWidget(self.mode_btn)

        card_layout.addLayout(song_info_row)

        # Progress Slider & Timestamp Row
        prog_row = QHBoxLayout()
        prog_row.setSpacing(8)

        self.time_cur_lbl = QLabel("00:00")
        self.time_cur_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #FFFFFF; min-width: 38px;")
        prog_row.addWidget(self.time_cur_lbl)

        self.progress_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.progress_slider.sliderPressed.connect(self._on_seek_pressed)
        self.progress_slider.sliderReleased.connect(self._on_seek_released)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        prog_row.addWidget(self.progress_slider, 1)

        self.time_tot_lbl = QLabel("00:00")
        self.time_tot_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #94A3B8; min-width: 38px;")
        prog_row.addWidget(self.time_tot_lbl)

        card_layout.addLayout(prog_row)

        # Playback Controls Row
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(14)
        ctrl_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Previous Track Button
        self.prev_btn = QPushButton()
        self.prev_btn.setObjectName("IconButton")
        self.prev_btn.setIcon(make_prev_icon(16, "#CBD5E1"))
        self.prev_btn.setFixedSize(36, 36)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setToolTip("上一首 (快捷键: 左箭头 ←)")
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.18);
                border-color: rgba(255, 255, 255, 0.3);
            }
        """)
        self.prev_btn.clicked.connect(self.music.prev_track)
        ctrl_row.addWidget(self.prev_btn)

        # Primary Play/Pause Button (Hero Glowing Button)
        self.play_btn = QPushButton()
        self.play_btn.setObjectName("IconButton")
        self.play_btn.setIcon(make_play_icon(20, "#FFFFFF"))
        self.play_btn.setFixedSize(48, 48)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.setToolTip("播放 / 暂停 (快捷键: 空格键 Space)")
        self.play_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0284C7, stop:1 #38BDF8);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 24px;
                padding: 0px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0369A1, stop:1 #0284C7);
                border-color: #FFFFFF;
            }
        """)
        self.play_btn.clicked.connect(self.music.toggle_play)
        ctrl_row.addWidget(self.play_btn)

        # Next Track Button
        self.next_btn = QPushButton()
        self.next_btn.setObjectName("IconButton")
        self.next_btn.setIcon(make_next_icon(16, "#CBD5E1"))
        self.next_btn.setFixedSize(36, 36)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setToolTip("下一首 (快捷键: 右箭头 →)")
        self.next_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.18);
                border-color: rgba(255, 255, 255, 0.3);
            }
        """)
        self.next_btn.clicked.connect(self.music.next_track)
        ctrl_row.addWidget(self.next_btn)

        # Volume Section (Mute Toggle + Volume Slider)
        ctrl_row.addSpacing(16)

        self.vol_btn = QPushButton()
        self.vol_btn.setObjectName("IconButton")
        self.vol_btn.setFixedSize(28, 28)
        self.vol_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vol_btn.setToolTip("点击静音 / 取消静音 (滚轮调节音量)")
        self.vol_btn.setIcon(make_volume_icon(16, self.music.is_muted(), "#CBD5E1"))
        self.vol_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        self.vol_btn.clicked.connect(self._toggle_mute)
        ctrl_row.addWidget(self.vol_btn)

        self.vol_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(self.music.get_volume())
        self.vol_slider.setFixedWidth(85)
        self.vol_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vol_slider.setToolTip(f"音量: {self.music.get_volume()}%")
        self.vol_slider.valueChanged.connect(self._on_vol_changed)
        ctrl_row.addWidget(self.vol_slider)

        card_layout.addLayout(ctrl_row)
        main_layout.addWidget(self.player_card)

        # 3. Playlist Header Bar with Live Search & Locate Button
        list_header_row = QHBoxLayout()
        list_header_row.setSpacing(8)

        self.playlist_count_lbl = QLabel(f"播放列表 ({len(self.music.playlist)} 首)")
        self.playlist_count_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #CBD5E1;")
        list_header_row.addWidget(self.playlist_count_lbl)

        # Locate active track button
        self.locate_btn = QPushButton("🎯 定位当前")
        self.locate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.locate_btn.setToolTip("跳转并高亮当前正在播放的曲目")
        self.locate_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 5px;
                padding: 2px 6px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(56, 189, 248, 0.15);
                color: #38BDF8;
                border-color: rgba(56, 189, 248, 0.4);
            }
        """)
        self.locate_btn.clicked.connect(self._scroll_to_current)
        list_header_row.addWidget(self.locate_btn)

        list_header_row.addStretch()

        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 11px;
                color: #94A3B8;
            }
            QPushButton:hover {
                color: #EF4444;
            }
        """)
        self.clear_btn.clicked.connect(self._clear_playlist)
        list_header_row.addWidget(self.clear_btn)

        main_layout.addLayout(list_header_row)

        # Search Bar
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 快速搜索歌曲名称或格式 (如: 周杰伦, mp3, flac)...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._on_search_changed)
        main_layout.addWidget(self.search_edit)

        # 4. Scrollable Playlist
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(6)

        self.scroll_area.setWidget(self.list_container)
        main_layout.addWidget(self.scroll_area, 1)

    def _connect_signals(self):
        self.music.playback_state_changed.connect(self._on_playback_state)
        self.music.track_changed.connect(self._on_track_changed)
        self.music.position_changed.connect(self._on_position_changed)
        self.music.playlist_changed.connect(self.reload_playlist)
        self.music.volume_changed.connect(self._on_volume_signal)
        self.music.mode_changed.connect(self._on_mode_changed)

    def _on_playback_state(self, is_playing: bool):
        self.play_btn.setIcon(make_pause_icon(18, "#FFFFFF") if is_playing else make_play_icon(20, "#FFFFFF"))
        self.vinyl.set_playing(is_playing)
        self.card_wave.set_playing(is_playing)
        self.card_wave.setVisible(is_playing)
        # Update active item waveform in playlist
        self.reload_playlist()

    def _on_track_changed(self, track: dict):
        if track:
            title = track.get("title", "未知曲目")
            self.now_title_lbl.setText(title)
            self.now_title_lbl.setToolTip(f"{title}\n路径: {track.get('path', '')}")
            self.now_artist_lbl.setText(track.get("filename", "本地音频"))
        else:
            self.now_title_lbl.setText("未在播放音乐")
            self.now_title_lbl.setToolTip("")
            self.now_artist_lbl.setText("播放列表为空，请导入歌曲")
        self.reload_playlist()

    def _on_position_changed(self, pos: int, dur: int):
        if not self.user_is_seeking:
            if dur > 0:
                pct = int((pos / dur) * 1000)
                self.progress_slider.setValue(pct)
            else:
                self.progress_slider.setValue(0)

        self.time_cur_lbl.setText(ms_to_str(pos))
        self.time_tot_lbl.setText(ms_to_str(dur))

    def _on_seek_pressed(self):
        self.user_is_seeking = True

    def _on_seek_released(self):
        dur = self.music.player.duration()
        if dur > 0:
            target_pos = int((self.progress_slider.value() / 1000.0) * dur)
            self.music.seek(target_pos)
        self.user_is_seeking = False

    def _on_slider_moved(self, val: int):
        dur = self.music.player.duration()
        if dur > 0:
            preview_ms = int((val / 1000.0) * dur)
            self.time_cur_lbl.setText(ms_to_str(preview_ms))

    def _toggle_mode(self):
        new_mode = self.music.toggle_mode()
        self._on_mode_changed(new_mode)

    def _on_mode_changed(self, mode: str):
        self.mode_btn.setText(f"🔁 {mode}")

    def _toggle_mute(self):
        is_muted = self.music.toggle_mute()
        self.vol_btn.setIcon(make_volume_icon(16, is_muted, "#CBD5E1"))
        self.vol_slider.setValue(self.music.get_volume())

    def _on_vol_changed(self, vol: int):
        self.music.set_volume(vol)
        self.vol_slider.setToolTip(f"音量: {vol}%")
        self.vol_btn.setIcon(make_volume_icon(16, vol == 0, "#CBD5E1"))

    def _on_volume_signal(self, vol: int):
        if self.vol_slider.value() != vol:
            self.vol_slider.setValue(vol)
        self.vol_btn.setIcon(make_volume_icon(16, vol == 0, "#CBD5E1"))
        self.vol_slider.setToolTip(f"音量: {vol}%")

    def _choose_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择本地音频文件", "",
            "音频文件 (*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.wma)"
        )
        if files:
            self.music.add_files(files)

    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择音乐文件夹")
        if folder:
            self.music.add_folder(folder)

    def _clear_playlist(self):
        if not self.music.playlist:
            return
        reply = QMessageBox.question(
            self,
            "清空播放列表",
            f"确定要清空播放列表中的全部 {len(self.music.playlist)} 首歌曲吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.music.clear_playlist()

    def _on_search_changed(self, text: str):
        self.search_filter = text.strip().lower()
        self.rendered_count_limit = 80
        self.reload_playlist()

    def _load_more(self):
        self.rendered_count_limit += 80
        self.reload_playlist()

    def _scroll_to_current(self):
        """Scroll view directly to current active track widget."""
        cur_idx = self.music.current_index
        if cur_idx < 0:
            return
        # If filtered out, clear search to reveal it
        if self.search_filter:
            self.search_edit.clear()
        if hasattr(self, "_active_widget") and self._active_widget:
            self.scroll_area.ensureWidgetVisible(self._active_widget, 50, 50)

    def reload_playlist(self):
        # Clear existing layout items
        while self.list_layout.count() > 0:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        playlist = self.music.playlist
        total_count = len(playlist)
        self._active_widget = None

        # Filter items
        filtered_items = []
        for i, track in enumerate(playlist):
            if not self.search_filter:
                filtered_items.append((i, track))
            else:
                title = track.get("title", "").lower()
                filename = track.get("filename", "").lower()
                if self.search_filter in title or self.search_filter in filename:
                    filtered_items.append((i, track))

        # Update counter label
        if self.search_filter:
            self.playlist_count_lbl.setText(f"播放列表 (已匹配 {len(filtered_items)} / 共 {total_count} 首)")
        else:
            self.playlist_count_lbl.setText(f"播放列表 ({total_count} 首)")

        # Empty State Card
        if not playlist:
            empty_frame = QFrame()
            empty_frame.setStyleSheet("""
                QFrame {
                    background: rgba(25, 28, 42, 0.6);
                    border: 2px dashed rgba(255, 255, 255, 0.12);
                    border-radius: 14px;
                    padding: 24px;
                }
            """)
            empty_layout = QVBoxLayout(empty_frame)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.setSpacing(10)

            icon_lbl = QLabel("🎵")
            icon_lbl.setStyleSheet("font-size: 32px;")
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(icon_lbl)

            hint_title = QLabel("暂无本地播放曲目")
            hint_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
            hint_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(hint_title)

            hint_sub = QLabel("支持直接拖拽音频文件或文件夹至此释放导入\n支持 MP3, FLAC, WAV, M4A, AAC 等常见格式")
            hint_sub.setStyleSheet("font-size: 12px; color: #94A3B8; line-height: 1.4;")
            hint_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(hint_sub)

            btn_box = QHBoxLayout()
            btn_box.setSpacing(10)
            btn_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

            add_btn = QPushButton("➕ 添加歌曲文件")
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.setStyleSheet("""
                QPushButton {
                    background: #0284C7;
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 600;
                    border-radius: 8px;
                    padding: 6px 14px;
                }
                QPushButton:hover { background: #0369A1; }
            """)
            add_btn.clicked.connect(self._choose_files)
            btn_box.addWidget(add_btn)

            dir_btn = QPushButton("📁 导入整张专辑/目录")
            dir_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            dir_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.1);
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 500;
                    border-radius: 8px;
                    padding: 6px 14px;
                }
                QPushButton:hover { background: rgba(255, 255, 255, 0.18); }
            """)
            dir_btn.clicked.connect(self._choose_folder)
            btn_box.addWidget(dir_btn)

            empty_layout.addLayout(btn_box)
            self.list_layout.addWidget(empty_frame)
            return

        # Render items (with performance windowing for 1000+ songs)
        items_to_render = filtered_items[:self.rendered_count_limit]

        for orig_idx, track in items_to_render:
            is_cur = (orig_idx == self.music.current_index)
            is_play = is_cur and self.music.is_playing
            item_widget = PlaylistItemWidget(orig_idx, track, is_cur, is_play)
            item_widget.play_requested.connect(self.music.play_track)
            item_widget.delete_requested.connect(self.music.remove_track)
            self.list_layout.addWidget(item_widget)

            if is_cur:
                self._active_widget = item_widget

        # If there are more matching items, show "Load More" pill
        remaining = len(filtered_items) - len(items_to_render)
        if remaining > 0:
            load_more_btn = QPushButton(f"▼ 查看更多曲目 (还有 {remaining} 首)...")
            load_more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            load_more_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.06);
                    color: #38BDF8;
                    border: 1px dashed rgba(56, 189, 248, 0.35);
                    border-radius: 8px;
                    padding: 8px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: rgba(56, 189, 248, 0.15);
                    border-color: #38BDF8;
                }
            """)
            load_more_btn.clicked.connect(self._load_more)
            self.list_layout.addWidget(load_more_btn)

        self.list_layout.addStretch()

    # Drag and Drop Events
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            files = []
            folders = []
            for url in event.mimeData().urls():
                local_path = url.toLocalFile()
                if os.path.isdir(local_path):
                    folders.append(local_path)
                elif os.path.isfile(local_path):
                    ext = Path(local_path).suffix.lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        files.append(local_path)

            if files:
                self.music.add_files(files)
            for folder in folders:
                self.music.add_folder(folder)

            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    # Mouse Wheel for Volume Adjustment
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.music.set_volume(self.music.get_volume() + 5)
        elif delta < 0:
            self.music.set_volume(self.music.get_volume() - 5)
        event.accept()

    # Keyboard Shortcuts
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.music.toggle_play()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Left:
            self.music.prev_track()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Right:
            self.music.next_track()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Up:
            self.music.set_volume(self.music.get_volume() + 5)
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Down:
            self.music.set_volume(self.music.get_volume() - 5)
            event.accept()
            return
        elif event.key() == Qt.Key.Key_M:
            self._toggle_mute()
            event.accept()
            return
        super().keyPressEvent(event)
