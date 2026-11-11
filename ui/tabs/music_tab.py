from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QScrollArea, QFrame, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor
from music_service import MusicService
from ui.styles import THEME

def ms_to_str(ms: int) -> str:
    total_secs = max(0, ms // 1000)
    mins = total_secs // 60
    secs = total_secs % 60
    return f"{mins:02d}:{secs:02d}"


class PlaylistItemWidget(QFrame):
    play_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)

    def __init__(self, index: int, track: dict, is_current: bool = False, parent=None):
        super().__init__(parent)
        self.index = index
        self.track = track
        self.is_current = is_current
        self.setObjectName("TaskCard")
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # Index / Playing icon
        self.icon_lbl = QLabel("▶" if self.is_current else f"{self.index + 1}")
        self.icon_lbl.setStyleSheet(f"""
            font-size: 11px;
            font-weight: bold;
            color: {'#38BDF8' if self.is_current else '#94A3B8'};
            min-width: 20px;
        """)
        layout.addWidget(self.icon_lbl)

        # Title
        title_lbl = QLabel(self.track.get("title", "未知曲目"))
        title_lbl.setStyleSheet(f"""
            font-size: 13px;
            font-weight: {'700' if self.is_current else '500'};
            color: {'#38BDF8' if self.is_current else '#FFFFFF'};
        """)
        layout.addWidget(title_lbl, 1)

        # Actions
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(24, 24)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
                background: rgba(239, 68, 68, 0.2);
                color: #EF4444;
            }
        """)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.index))
        layout.addWidget(del_btn)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.play_requested.emit(self.index)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


class MusicTab(QWidget):
    def __init__(self, music_service: MusicService, parent=None):
        super().__init__(parent)
        self.music = music_service
        self.user_is_seeking = False

        self._init_ui()
        self._connect_signals()
        self.reload_playlist()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(10)

        # 1. Top Bar
        top_bar = QHBoxLayout()
        title_lbl = QLabel("🎵 本地音乐播放")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        top_bar.addWidget(title_lbl)

        top_bar.addStretch()

        self.add_files_btn = QPushButton("➕ 添加歌曲")
        self.add_files_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_files_btn.clicked.connect(self._choose_files)
        top_bar.addWidget(self.add_files_btn)

        self.add_folder_btn = QPushButton("📁 导入文件夹")
        self.add_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_folder_btn.clicked.connect(self._choose_folder)
        top_bar.addWidget(self.add_folder_btn)

        main_layout.addLayout(top_bar)

        # 2. Now Playing Card
        player_card = QFrame()
        player_card.setObjectName("TaskCard")
        player_card.setStyleSheet(f"""
            background: rgba(25, 28, 42, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 14px;
            padding: 4px;
        """)
        card_layout = QVBoxLayout(player_card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)

        # Song Title & Artist
        song_info_row = QHBoxLayout()
        disc_lbl = QLabel("💿")
        disc_lbl.setStyleSheet("font-size: 26px;")
        song_info_row.addWidget(disc_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self.now_title_lbl = QLabel("未在播放音乐")
        self.now_title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        title_box.addWidget(self.now_title_lbl)

        self.now_artist_lbl = QLabel("点击下方添加歌曲开始畅听")
        self.now_artist_lbl.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_box.addWidget(self.now_artist_lbl)

        song_info_row.addLayout(title_box, 1)

        # Mode button
        self.mode_btn = QPushButton(f"🔁 {self.music.get_mode()}")
        self.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #38BDF8;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 6px;
                padding: 4px 8px;
            }
        """)
        self.mode_btn.clicked.connect(self._toggle_mode)
        song_info_row.addWidget(self.mode_btn)

        card_layout.addLayout(song_info_row)

        # Progress bar & time stamps (High Contrast)
        prog_row = QHBoxLayout()
        prog_row.setSpacing(8)

        self.time_cur_lbl = QLabel("00:00")
        self.time_cur_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #FFFFFF;")
        prog_row.addWidget(self.time_cur_lbl)

        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.sliderPressed.connect(self._on_seek_pressed)
        self.progress_slider.sliderReleased.connect(self._on_seek_released)
        prog_row.addWidget(self.progress_slider, 1)

        self.time_tot_lbl = QLabel("00:00")
        self.time_tot_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #FFFFFF;")
        prog_row.addWidget(self.time_tot_lbl)

        card_layout.addLayout(prog_row)

        # Playback Controls Row
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(12)
        ctrl_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setFixedSize(36, 36)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setStyleSheet("font-size: 16px; border-radius: 18px; padding: 0px;")
        self.prev_btn.clicked.connect(self.music.prev_track)
        ctrl_row.addWidget(self.prev_btn)

        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("PrimaryButton")
        self.play_btn.setFixedSize(48, 48)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.setStyleSheet("font-size: 20px; font-weight: bold; border-radius: 24px; padding: 0px;")
        self.play_btn.clicked.connect(self.music.toggle_play)
        ctrl_row.addWidget(self.play_btn)

        self.next_btn = QPushButton("⏭")
        self.next_btn.setFixedSize(36, 36)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setStyleSheet("font-size: 16px; border-radius: 18px; padding: 0px;")
        self.next_btn.clicked.connect(self.music.next_track)
        ctrl_row.addWidget(self.next_btn)

        # Volume slider
        ctrl_row.addSpacing(16)
        vol_lbl = QLabel("🔊")
        vol_lbl.setStyleSheet("font-size: 14px;")
        ctrl_row.addWidget(vol_lbl)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(self.music.get_volume())
        self.vol_slider.setFixedWidth(80)
        self.vol_slider.valueChanged.connect(self.music.set_volume)
        ctrl_row.addWidget(self.vol_slider)

        card_layout.addLayout(ctrl_row)
        main_layout.addWidget(player_card)

        # 3. Playlist Header & List
        list_header = QHBoxLayout()
        self.playlist_count_lbl = QLabel("播放列表 (0 首)")
        self.playlist_count_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #CBD5E1;")
        list_header.addWidget(self.playlist_count_lbl)

        list_header.addStretch()

        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet("background: transparent; border: none; font-size: 11px; color: #94A3B8;")
        self.clear_btn.clicked.connect(self._clear_playlist)
        list_header.addWidget(self.clear_btn)

        main_layout.addLayout(list_header)

        # Scrollable Playlist
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch()

        self.scroll_area.setWidget(self.list_container)
        main_layout.addWidget(self.scroll_area, 1)

    def _connect_signals(self):
        self.music.playback_state_changed.connect(self._on_playback_state)
        self.music.track_changed.connect(self._on_track_changed)
        self.music.position_changed.connect(self._on_position_changed)
        self.music.playlist_changed.connect(self.reload_playlist)
        self.music.mode_changed.connect(lambda m: self.mode_btn.setText(f"🔁 {m}"))

    def _on_playback_state(self, is_playing: bool):
        self.play_btn.setText("⏸" if is_playing else "▶")

    def _on_track_changed(self, track: dict):
        if track:
            self.now_title_lbl.setText(track.get("title", "未知曲目"))
            self.now_artist_lbl.setText(track.get("artist", "本地音乐"))
        else:
            self.now_title_lbl.setText("未在播放音乐")
            self.now_artist_lbl.setText("列表为空")
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

    def _toggle_mode(self):
        new_mode = self.music.toggle_mode()
        self.mode_btn.setText(f"🔁 {new_mode}")

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
        if self.music.playlist:
            self.music.clear_playlist()

    def reload_playlist(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        playlist = self.music.playlist
        self.playlist_count_lbl.setText(f"播放列表 ({len(playlist)} 首)")

        if not playlist:
            empty_lbl = QLabel("🎵 暂无音乐，点击上方「添加歌曲」导入本地音频")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #64748B; padding: 30px; font-size: 13px;")
            self.list_layout.insertWidget(0, empty_lbl)
            return

        for i, track in enumerate(playlist):
            is_cur = (i == self.music.current_index)
            item_widget = PlaylistItemWidget(i, track, is_cur)
            item_widget.play_requested.connect(self.music.play_track)
            item_widget.delete_requested.connect(self.music.remove_track)
            self.list_layout.insertWidget(self.list_layout.count() - 1, item_widget)
