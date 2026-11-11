import os
import random
from pathlib import Path
from typing import List, Dict, Optional, Any

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from storage import storage

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}

class MusicService(QObject):
    playback_state_changed = pyqtSignal(bool)           # is_playing
    track_changed = pyqtSignal(dict)                    # current track info
    position_changed = pyqtSignal(int, int)             # position_ms, duration_ms
    playlist_changed = pyqtSignal()
    volume_changed = pyqtSignal(int)
    mode_changed = pyqtSignal(str)

    MODE_LIST_LOOP = "列表循环"
    MODE_SINGLE_LOOP = "单曲循环"
    MODE_SHUFFLE = "随机播放"
    MODES = [MODE_LIST_LOOP, MODE_SINGLE_LOOP, MODE_SHUFFLE]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        self.playlist: List[Dict[str, Any]] = storage.get_playlist()
        self.current_index = -1
        self.current_track: Optional[Dict[str, Any]] = None
        self.mode_index = 0
        self.is_playing = False

        # Load volume from settings
        settings = storage.get_settings()
        init_vol = settings.get("music_volume", 70)
        self.set_volume(init_vol)

        self._connect_signals()

    def _connect_signals(self):
        self.player.playbackStateChanged.connect(self._on_playback_state)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status)

    def _on_playback_state(self, state):
        self.is_playing = (state == QMediaPlayer.PlaybackState.PlayingState)
        self.playback_state_changed.emit(self.is_playing)

    def _on_position_changed(self, pos):
        dur = self.player.duration()
        self.position_changed.emit(pos, dur)

    def _on_duration_changed(self, dur):
        pos = self.player.position()
        self.position_changed.emit(pos, dur)

    def _on_media_status(self, status):
        # End of media -> advance according to mode
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            mode = self.MODES[self.mode_index]
            if mode == self.MODE_SINGLE_LOOP:
                self.player.setPosition(0)
                self.player.play()
            elif mode == self.MODE_SHUFFLE:
                self.play_random()
            else:
                self.next_track()

    def set_volume(self, vol: int):
        vol = max(0, min(100, vol))
        self.audio_output.setVolume(vol / 100.0)
        storage.update_setting("music_volume", vol)
        self.volume_changed.emit(vol)

    def get_volume(self) -> int:
        return int(self.audio_output.volume() * 100)

    def toggle_mute(self) -> bool:
        """Toggle mute state and return True if currently muted."""
        cur = self.get_volume()
        if cur > 0:
            self._pre_mute_volume = cur
            self.set_volume(0)
            return True
        else:
            restore = getattr(self, "_pre_mute_volume", 70)
            self.set_volume(restore if restore > 0 else 70)
            return False

    def is_muted(self) -> bool:
        return self.get_volume() == 0

    def toggle_mode(self) -> str:
        self.mode_index = (self.mode_index + 1) % len(self.MODES)
        mode = self.MODES[self.mode_index]
        self.mode_changed.emit(mode)
        return mode

    def get_mode(self) -> str:
        return self.MODES[self.mode_index]

    def add_files(self, file_paths: List[str]):
        added = False
        for path_str in file_paths:
            p = Path(path_str)
            if p.suffix.lower() in SUPPORTED_EXTENSIONS and p.exists():
                title = p.stem
                track = {
                    "path": str(p.resolve()),
                    "title": title,
                    "artist": "本地音频",
                    "filename": p.name,
                }
                # Check duplicate
                if not any(t["path"] == track["path"] for t in self.playlist):
                    self.playlist.append(track)
                    added = True

        if added:
            storage.save_playlist(self.playlist)
            self.playlist_changed.emit()
            if self.current_index == -1 and len(self.playlist) > 0:
                self.current_index = 0
                self.current_track = self.playlist[0]
                self.track_changed.emit(self.current_track)

    def add_folder(self, folder_path: str):
        p = Path(folder_path)
        if not p.is_dir():
            return
        files = []
        for root, _, filenames in os.walk(folder_path):
            for f in filenames:
                ext = Path(f).suffix.lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files.append(os.path.join(root, f))
        if files:
            self.add_files(files)

    def remove_track(self, index: int):
        if 0 <= index < len(self.playlist):
            was_playing_this = (index == self.current_index)
            self.playlist.pop(index)
            storage.save_playlist(self.playlist)
            self.playlist_changed.emit()

            if len(self.playlist) == 0:
                self.stop()
                self.current_index = -1
                self.current_track = None
                self.track_changed.emit({})
            else:
                if was_playing_this:
                    self.current_index = min(index, len(self.playlist) - 1)
                    self.play_track(self.current_index)
                elif self.current_index > index:
                    self.current_index -= 1

    def clear_playlist(self):
        self.stop()
        self.playlist = []
        self.current_index = -1
        self.current_track = None
        storage.save_playlist([])
        self.playlist_changed.emit()
        self.track_changed.emit({})

    def play_track(self, index: int):
        if not (0 <= index < len(self.playlist)):
            return
        self.current_index = index
        self.current_track = self.playlist[index]
        file_path = self.current_track["path"]

        url = QUrl.fromLocalFile(file_path)
        self.player.setSource(url)
        self.player.play()
        self.track_changed.emit(self.current_track)

    def toggle_play(self):
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def play(self):
        if self.current_index == -1 and len(self.playlist) > 0:
            self.play_track(0)
        elif self.current_track:
            self.player.play()

    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()

    def next_track(self):
        if not self.playlist:
            return
        mode = self.MODES[self.mode_index]
        if mode == self.MODE_SHUFFLE:
            self.play_random()
        else:
            next_idx = (self.current_index + 1) % len(self.playlist)
            self.play_track(next_idx)

    def prev_track(self):
        if not self.playlist:
            return
        # If played > 3 seconds, replay current track
        if self.player.position() > 3000:
            self.player.setPosition(0)
            return

        mode = self.MODES[self.mode_index]
        if mode == self.MODE_SHUFFLE:
            self.play_random()
        else:
            prev_idx = (self.current_index - 1 + len(self.playlist)) % len(self.playlist)
            self.play_track(prev_idx)

    def play_random(self):
        if not self.playlist:
            return
        if len(self.playlist) == 1:
            self.play_track(0)
            return
        indices = [i for i in range(len(self.playlist)) if i != self.current_index]
        self.play_track(random.choice(indices))

    def seek(self, position_ms: int):
        self.player.setPosition(position_ms)
