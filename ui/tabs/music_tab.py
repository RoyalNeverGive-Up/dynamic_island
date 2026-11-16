import os
import math
from pathlib import Path
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QScrollArea, QFrame, QFileDialog, QMessageBox,
    QLineEdit, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRectF, QPointF, QSize, QEvent
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QCursor, QFont,
    QPixmap, QPainterPath, QLinearGradient
)

from music_service import MusicService, SUPPORTED_EXTENSIONS
from ui.styles import THEME
from ui.components.icons import (
    make_play_icon, make_pause_icon, make_prev_icon,
    make_next_icon, make_volume_icon, make_heart_icon,
    make_shuffle_icon, make_repeat_icon, make_search_icon,
    make_plus_icon, make_folder_icon, make_close_icon
)


def ms_to_str(ms: int) -> str:
    total_secs = max(0, ms // 1000)
    mins = total_secs // 60
    secs = total_secs % 60
    return f"{mins:02d}:{secs:02d}"


def get_audio_quality_badge(filename: str) -> str:
    """Return an Apple Music style audio quality descriptor."""
    ext = Path(filename).suffix.lower().replace(".", "")
    if ext in ("flac", "ape"):
        return "LOSSLESS"
    elif ext == "wav":
        return "HI-RES"
    elif ext in ("m4a", "aac"):
        return "AAC"
    elif ext == "mp3":
        return "MP3"
    elif ext == "ogg":
        return "OGG"
    return ext.upper() if ext else "AUDIO"


class ElidedLabel(QLabel):
    """A QLabel that automatically elides text with ellipsis (...) when width is constrained,
    and never expands parent layout beyond available space."""
    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._full_text = text or ""
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)
        self._update_elided()

    def setText(self, text: str):
        self._full_text = text or ""
        self.updateGeometry()
        self._update_elided()

    def text(self) -> str:
        return self._full_text

    def changeEvent(self, event):
        super().changeEvent(event)
        if event and event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._update_elided()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided()

    def _update_elided(self):
        fm = self.fontMetrics()
        avail_w = max(0, self.width())
        if avail_w > 0 and self._full_text:
            elided = fm.elidedText(self._full_text, Qt.TextElideMode.ElideRight, avail_w)
            super().setText(elided)
        else:
            super().setText(self._full_text)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, self.fontMetrics().height())

    def sizeHint(self) -> QSize:
        fm = self.fontMetrics()
        w = fm.horizontalAdvance(self._full_text)
        return QSize(min(220, w), fm.height())


class VinylWidget(QWidget):
    """Sleek animated vinyl record that rotates continuously during playback."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(56, 56)
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

        # 3. Center gradient label (Apple Music rose)
        lr = r * 0.40
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#FA2D48")))
        p.drawEllipse(QRectF(-lr, -lr, lr * 2, lr * 2))

        # 4. Spindle hole
        hr = r * 0.12
        p.setBrush(QBrush(QColor(15, 23, 42)))
        p.drawEllipse(QRectF(-hr, -hr, hr * 2, hr * 2))

        p.restore()
        p.end()


class AlbumCoverWidget(VinylWidget):
    """Apple Music signature rounded album art card with soft ambient drop-shadow and vibrant glow."""

    def __init__(self, size: int = 58, radius: int = 11, parent=None):
        super().__init__(parent)
        self.size = size
        self.radius = radius
        self.setFixedSize(size, size)
        self.pixmap: Optional[QPixmap] = None

        # Ambient drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def set_cover_bytes(self, data: Optional[bytes]):
        if data:
            src = QPixmap()
            if src.loadFromData(data):
                target = QPixmap(self.size, self.size)
                target.fill(Qt.GlobalColor.transparent)
                scaled = src.scaled(
                    self.size, self.size,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                p = QPainter(target)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                path = QPainterPath()
                path.addRoundedRect(QRectF(0.0, 0.0, float(self.size), float(self.size)), float(self.radius), float(self.radius))
                p.setClipPath(path)
                ox = max(0, (scaled.width() - self.size) // 2)
                oy = max(0, (scaled.height() - self.size) // 2)
                p.drawPixmap(0, 0, scaled, ox, oy, self.size, self.size)
                p.end()
                self.pixmap = target
            else:
                self.pixmap = None
        else:
            self.pixmap = None
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = float(self.size)

        if self.pixmap and not self.pixmap.isNull():
            p.drawPixmap(0, 0, self.pixmap)
            # Glowing border when playing, subtle hairline when idle
            if self.is_playing:
                p.setPen(QPen(QColor("#FA2D48"), 1.8))
            else:
                p.setPen(QPen(QColor(255, 255, 255, 45), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(0.6, 0.6, r - 1.2, r - 1.2), float(self.radius), float(self.radius))
        else:
            # Apple Music signature vibrant multi-stop gradient
            path = QPainterPath()
            path.addRoundedRect(QRectF(0.0, 0.0, r, r), float(self.radius), float(self.radius))
            p.setClipPath(path)

            grad = QLinearGradient(0, 0, r, r)
            grad.setColorAt(0.0, QColor("#FA243C"))
            grad.setColorAt(0.5, QColor("#8B5CF6"))
            grad.setColorAt(1.0, QColor("#2563EB"))
            p.fillRect(0, 0, int(r), int(r), grad)

            # Hairline border
            border_color = QColor(255, 255, 255, 60) if self.is_playing else QColor(255, 255, 255, 30)
            p.setPen(QPen(border_color, 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(0.5, 0.5, r - 1.0, r - 1.0), float(self.radius), float(self.radius))

            # Centered white music note
            p.setPen(QColor("#FFFFFF"))
            font = QFont("Segoe UI Emoji", int(r * 0.42))
            font.setBold(True)
            p.setFont(font)
            p.drawText(QRectF(0, 0, r, r), Qt.AlignmentFlag.AlignCenter, "🎵")

        p.end()


class AudioWaveWidget(QWidget):
    """Dynamic animated 4-bar equalizer visualizer in Apple Music Rose."""

    def __init__(self, parent=None, color: str = "#FA2D48"):
        super().__init__(parent)
        self.setFixedSize(18, 14)
        self.is_playing = False
        self.bar_color = color
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
        p.setBrush(QBrush(QColor(self.bar_color)))

        num_bars = 4
        bar_w = 2.4
        gap = 1.8
        max_h = 11.0
        base_h = 2.4

        for i in range(num_bars):
            if self.is_playing:
                phase = self.tick * 0.32 + i * 1.3
                h = base_h + (max_h - base_h) * (0.5 + 0.5 * math.sin(phase))
            else:
                h = base_h
            x = i * (bar_w + gap) + 1.0
            y = (self.height() - h) / 2.0
            p.drawRoundedRect(QRectF(x, y, bar_w, h), 1.2, 1.2)
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


class VolumeSlider(ClickableSlider):
    """Horizontal volume slider that responds specifically to mouse wheel only when hovered."""

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta:
            step = 4 if delta > 0 else -4
            new_val = max(0, min(100, self.value() + step))
            self.setValue(new_val)
            self.sliderMoved.emit(new_val)
            event.accept()
        else:
            super().wheelEvent(event)


class VolumeButton(QPushButton):
    """Volume icon button with wheel event support for volume tuning."""

    wheel_scrolled = pyqtSignal(int)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta:
            self.wheel_scrolled.emit(delta)
            event.accept()
        else:
            super().wheelEvent(event)


class CategoryGroupItemWidget(QFrame):
    """Hierarchical directory item for Level-1 Categories: Album, Artist, Folder, or Lossless Format."""

    clicked = pyqtSignal(str)

    def __init__(self, key: str, title: str, subtitle: str, count: int, icon_type: str = "album", cover_bytes: Optional[bytes] = None, parent=None):
        super().__init__(parent)
        self.key = key
        self.title = title
        self.subtitle = subtitle
        self.count = count
        self.icon_type = icon_type
        self.cover_bytes = cover_bytes

        self.setObjectName("AppleCategoryItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(44)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(10)

        # 1. 32x32 Thumbnail / Icon
        self.thumb_lbl = QLabel()
        self.thumb_lbl.setFixedSize(32, 32)
        if self.cover_bytes:
            src = QPixmap()
            if src.loadFromData(self.cover_bytes):
                target = QPixmap(32, 32)
                target.fill(Qt.GlobalColor.transparent)
                scaled = src.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                p = QPainter(target)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                path = QPainterPath()
                path.addRoundedRect(QRectF(0.0, 0.0, 32.0, 32.0), 6.0, 6.0)
                p.setClipPath(path)
                ox = max(0, (scaled.width() - 32) // 2)
                oy = max(0, (scaled.height() - 32) // 2)
                p.drawPixmap(0, 0, scaled, ox, oy, 32, 32)
                p.end()
                self.thumb_lbl.setPixmap(target)
            else:
                self.thumb_lbl.setPixmap(self._make_default_icon())
        else:
            self.thumb_lbl.setPixmap(self._make_default_icon())
        layout.addWidget(self.thumb_lbl)

        # 2. Title & Subtitle (Auto-elided to never push container width)
        info_box = QVBoxLayout()
        info_box.setSpacing(1)
        info_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_lbl = ElidedLabel(self.title)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        title_lbl.setToolTip(self.title)
        info_box.addWidget(title_lbl)

        sub_lbl = ElidedLabel(self.subtitle)
        sub_lbl.setStyleSheet("font-size: 11px; color: #86868B;")
        sub_lbl.setToolTip(self.subtitle)
        info_box.addWidget(sub_lbl)

        layout.addLayout(info_box, 1)

        # 3. Count Pill badge
        count_lbl = QLabel(f"{self.count} 首")
        count_lbl.setStyleSheet("""
            font-size: 11px;
            font-weight: 600;
            color: #A1A1A6;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 9px;
            padding: 2px 7px;
        """)
        layout.addWidget(count_lbl)

        # 4. Chevron right indicator (›)
        arr_lbl = QLabel("›")
        arr_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #6E6E73; margin-left: 2px;")
        layout.addWidget(arr_lbl)

    def _make_default_icon(self) -> QPixmap:
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.0, 0.0, 32.0, 32.0), 6.0, 6.0)
        p.setClipPath(path)

        grad = QLinearGradient(0, 0, 32, 32)
        if self.icon_type == "artist":
            grad.setColorAt(0.0, QColor("#8B5CF6"))
            grad.setColorAt(1.0, QColor("#3B82F6"))
            symbol = "🎤"
        elif self.icon_type == "album":
            grad.setColorAt(0.0, QColor("#FA243C"))
            grad.setColorAt(1.0, QColor("#F59E0B"))
            symbol = "💿"
        elif self.icon_type == "lossless":
            grad.setColorAt(0.0, QColor("#10B981"))
            grad.setColorAt(1.0, QColor("#06B6D4"))
            symbol = "🎧"
        else:  # folder
            grad.setColorAt(0.0, QColor("#F97316"))
            grad.setColorAt(1.0, QColor("#EAB308"))
            symbol = "📁"

        p.fillRect(0, 0, 32, 32, grad)
        p.setPen(QColor("#FFFFFF"))
        font = QFont("Segoe UI Emoji", 11)
        p.setFont(font)
        p.drawText(QRectF(0, 0, 32, 32), Qt.AlignmentFlag.AlignCenter, symbol)
        p.end()
        return pix

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
            event.accept()
        else:
            super().mousePressEvent(event)


class PlaylistItemWidget(QFrame):
    """Apple Music style compact track row with Favorite heart, metadata & format badge."""

    play_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)
    favorite_toggled = pyqtSignal(int)

    def __init__(self, index: int, track: dict, is_current: bool = False, is_playing: bool = False, cover_pixmap: Optional[QPixmap] = None, parent=None):
        super().__init__(parent)
        self.index = index
        self.track = track
        self.is_current = is_current
        self.is_playing = is_playing
        self.cover_pixmap = cover_pixmap
        self.is_fav = bool(track.get("favorite", False))

        self.setObjectName("AppleTrackActive" if self.is_current else "AppleTrackItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)

        # 1. State indicator (Equalizer wave if playing, or track number)
        self.indicator_box = QWidget()
        self.indicator_box.setFixedWidth(20)
        ind_layout = QHBoxLayout(self.indicator_box)
        ind_layout.setContentsMargins(0, 0, 0, 0)
        ind_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self.is_current and self.is_playing:
            self.wave = AudioWaveWidget(self, color="#FA2D48")
            self.wave.set_playing(True)
            ind_layout.addWidget(self.wave)
        else:
            idx_str = f"{self.index + 1:02d}" if self.index < 99 else f"{self.index + 1}"
            self.num_lbl = QLabel(idx_str)
            self.num_lbl.setStyleSheet(f"""
                font-size: 10px;
                font-weight: {'700' if self.is_current else '500'};
                color: {'#FA2D48' if self.is_current else '#6E6E73'};
            """)
            ind_layout.addWidget(self.num_lbl)

        layout.addWidget(self.indicator_box)

        # 2. Mini Artwork Cover Thumbnail (28x28 rounded)
        self.thumb_lbl = QLabel()
        self.thumb_lbl.setFixedSize(28, 28)
        if self.is_current and self.cover_pixmap and not self.cover_pixmap.isNull():
            self.thumb_lbl.setPixmap(self.cover_pixmap.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        else:
            mini_pix = QPixmap(28, 28)
            mini_pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(mini_pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(QRectF(0.0, 0.0, 28.0, 28.0), 5.0, 5.0)
            p.setClipPath(path)
            grad = QLinearGradient(0, 0, 28, 28)
            if self.is_current:
                grad.setColorAt(0.0, QColor("#FA243C"))
                grad.setColorAt(1.0, QColor("#8B5CF6"))
            else:
                grad.setColorAt(0.0, QColor("#1E293B"))
                grad.setColorAt(1.0, QColor("#0F172A"))
            p.fillRect(0, 0, 28, 28, grad)
            p.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(0.5, 0.5, 27.0, 27.0), 5.0, 5.0)
            p.setPen(QColor("#FFFFFF" if self.is_current else "#94A3B8"))
            font = QFont("Segoe UI Emoji", 10)
            p.setFont(font)
            p.drawText(QRectF(0, 0, 28, 28), Qt.AlignmentFlag.AlignCenter, "🎵")
            p.end()
            self.thumb_lbl.setPixmap(mini_pix)

        layout.addWidget(self.thumb_lbl)

        # 3. Track Title & Artist · Album Subtitle
        info_box = QVBoxLayout()
        info_box.setSpacing(0)
        info_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_text = self.track.get("title", "未知曲目")
        self.title_lbl = ElidedLabel(title_text)
        self.title_lbl.setStyleSheet(f"""
            font-size: 12px;
            font-weight: {'700' if self.is_current else '500'};
            color: {'#FA2D48' if self.is_current else '#FFFFFF'};
        """)
        self.title_lbl.setToolTip(f"{title_text}\n路径: {self.track.get('path', '')}")
        info_box.addWidget(self.title_lbl)

        sub_row = QHBoxLayout()
        sub_row.setSpacing(4)

        artist_text = self.track.get("artist") or "未知歌手"
        album_text = self.track.get("album") or "单曲精选"
        meta_str = f"{artist_text} · {album_text}" if album_text != "单曲精选" else artist_text
        artist_lbl = ElidedLabel(meta_str)
        artist_lbl.setStyleSheet("font-size: 10px; color: #86868B;")
        sub_row.addWidget(artist_lbl, 1)

        # Quality Format Badge
        ext = Path(self.track.get("filename", "")).suffix.replace(".", "").upper()
        if ext:
            badge_text = "LOSSLESS" if ext in ("FLAC", "WAV", "APE") else ext
            badge_lbl = QLabel(badge_text)
            badge_lbl.setStyleSheet("""
                font-size: 8px;
                font-weight: 700;
                color: #A1A1A6;
                background: rgba(255, 255, 255, 0.08);
                border-radius: 2px;
                padding: 0px 3px;
            """)
            sub_row.addWidget(badge_lbl)

        info_box.addLayout(sub_row)
        layout.addLayout(info_box, 1)

        # 4. Favorite Heart Button
        self.fav_btn = QPushButton()
        self.fav_btn.setFixedSize(22, 22)
        self.fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fav_btn.setToolTip("取消喜欢" if self.is_fav else "添加到个人喜爱 (❤️)")
        self.fav_btn.setIcon(make_heart_icon(13, filled=self.is_fav, color="#FA2D48" if self.is_fav else "#86868B"))
        self.fav_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 11px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(250, 45, 72, 0.15);
            }
        """)
        self.fav_btn.clicked.connect(self._on_fav_clicked)
        layout.addWidget(self.fav_btn)

        # 5. Remove Button
        del_btn = QPushButton()
        del_btn.setIcon(make_close_icon(10, "#6E6E73"))
        del_btn.setFixedSize(20, 20)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setToolTip("从资料库移除")
        del_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.2);
            }
        """)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.index))
        layout.addWidget(del_btn)

    def _on_fav_clicked(self):
        self.favorite_toggled.emit(self.index)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.play_requested.emit(self.index)
            event.accept()
        else:
            super().mousePressEvent(event)


class MusicTab(QWidget):
    """Hierarchical, high-capacity Apple Music Player with category drilldown navigation."""

    CATEGORIES = [
        ("all", "全部", "🎵"),
        ("favorites", "喜爱", "❤️"),
        ("artists", "歌手", "🎤"),
        ("albums", "专辑", "💿"),
        ("lossless", "无损", "🎧"),
        ("folders", "目录", "📁"),
    ]

    def __init__(self, music_service: MusicService, parent=None):
        super().__init__(parent)
        self.music = music_service
        self.user_is_seeking = False
        self.search_filter = ""
        self.show_remaining_time = True
        self.rendered_count_limit = 80
        self.current_category = "all"
        self.active_drilldown: Optional[str] = None  # None = Level 1, or specific artist/album/folder/format name

        self.setAcceptDrops(True)
        self._init_ui()
        self._connect_signals()
        self.reload_playlist()
        self._on_cover_changed(self.music.get_current_cover_bytes())

    def _init_ui(self):
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(6)

        # 1. Flagship Apple Music Now Playing Hero Card (Enhanced size ~105px)
        self.player_card = QFrame()
        self.player_card.setObjectName("MusicPlayerCard")
        self.player_card.setStyleSheet("""
            QFrame#MusicPlayerCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(32, 35, 48, 0.95), stop:1 rgba(18, 20, 32, 0.98));
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 14px;
            }
        """)
        card_layout = QVBoxLayout(self.player_card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(8)

        # Row 1: Enlarged 58x58 Album Cover + Wide Song Info + Card Favorite Heart
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # 58x58 Floating Album Cover
        self.cover_widget = AlbumCoverWidget(size=58, radius=11, parent=self)
        self.vinyl = self.cover_widget  # backwards compatibility alias
        top_row.addWidget(self.cover_widget)

        # Song Title & Artist info (Takes all available width and auto-elides smoothly)
        meta_box = QVBoxLayout()
        meta_box.setSpacing(2)
        meta_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_line = QHBoxLayout()
        title_line.setSpacing(6)
        self.now_title_lbl = ElidedLabel("未在播放音乐")
        self.now_title_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        title_line.addWidget(self.now_title_lbl, 1)

        self.card_wave = AudioWaveWidget(self, color="#FA2D48")
        title_line.addWidget(self.card_wave)
        meta_box.addLayout(title_line)

        sub_line = QHBoxLayout()
        sub_line.setSpacing(6)
        self.now_artist_lbl = ElidedLabel("选择下方歌曲畅听")
        self.now_artist_lbl.setStyleSheet("font-size: 11px; color: #86868B;")
        sub_line.addWidget(self.now_artist_lbl, 1)

        self.quality_badge = QLabel("LOSSLESS")
        self.quality_badge.setStyleSheet("""
            font-size: 9px;
            font-weight: 800;
            color: #CBD5E1;
            background: rgba(255, 255, 255, 0.10);
            border-radius: 3px;
            padding: 1px 4px;
        """)
        self.quality_badge.setVisible(False)
        sub_line.addWidget(self.quality_badge)
        meta_box.addLayout(sub_line)

        top_row.addLayout(meta_box, 1)

        # Favorite Heart on top row
        self.card_fav_btn = QPushButton()
        self.card_fav_btn.setFixedSize(28, 28)
        self.card_fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.card_fav_btn.setToolTip("收藏当前播放曲目 (❤️)")
        self.card_fav_btn.setIcon(make_heart_icon(16, filled=False, color="#86868B"))
        self.card_fav_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(250, 45, 72, 0.2);
                border-color: rgba(250, 45, 72, 0.4);
            }
        """)
        self.card_fav_btn.clicked.connect(self._toggle_card_favorite)
        top_row.addWidget(self.card_fav_btn)

        card_layout.addLayout(top_row)

        # Transport Controls: Shuffle, Prev, 46x46 Play, Next, Repeat
        ctrl_box = QHBoxLayout()
        ctrl_box.setSpacing(8)
        ctrl_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Shuffle
        self.shuffle_btn = QPushButton()
        self.shuffle_btn.setFixedSize(28, 28)
        self.shuffle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.shuffle_btn.setToolTip("随机播放")
        self._update_shuffle_icon()
        self.shuffle_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.16);
            }
        """)
        self.shuffle_btn.clicked.connect(self._toggle_shuffle)
        ctrl_box.addWidget(self.shuffle_btn)

        # Prev
        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(make_prev_icon(15, "#FFFFFF"))
        self.prev_btn.setFixedSize(32, 32)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setToolTip("上一首 (←)")
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 16px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.16);
            }
        """)
        self.prev_btn.clicked.connect(self.music.prev_track)
        ctrl_box.addWidget(self.prev_btn)

        # Hero Play/Pause Button (46x46 Apple Rose gradient with soft drop shadow)
        self.play_btn = QPushButton()
        self.play_btn.setObjectName("HeroPlayButton")
        self.play_btn.setIcon(make_play_icon(19, "#FFFFFF"))
        self.play_btn.setFixedSize(46, 46)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.setToolTip("播放 / 暂停 (Space)")
        self.play_btn.setStyleSheet("""
            QPushButton#HeroPlayButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FA243C, stop:1 #FF5E62);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 23px;
                padding: 0px;
            }
            QPushButton#HeroPlayButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF3B53, stop:1 #FF7579);
                border-color: #FFFFFF;
            }
        """)
        play_shadow = QGraphicsDropShadowEffect(self.play_btn)
        play_shadow.setBlurRadius(14)
        play_shadow.setColor(QColor(250, 36, 60, 110))
        play_shadow.setOffset(0, 3)
        self.play_btn.setGraphicsEffect(play_shadow)
        self.play_btn.clicked.connect(self.music.toggle_play)
        ctrl_box.addWidget(self.play_btn)

        # Next
        self.next_btn = QPushButton()
        self.next_btn.setIcon(make_next_icon(15, "#FFFFFF"))
        self.next_btn.setFixedSize(32, 32)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setToolTip("下一首 (→)")
        self.next_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 16px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.16);
            }
        """)
        self.next_btn.clicked.connect(self.music.next_track)
        ctrl_box.addWidget(self.next_btn)

        # Repeat
        self.repeat_btn = QPushButton()
        self.repeat_btn.setFixedSize(28, 28)
        self.repeat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_repeat_icon()
        self.repeat_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.16);
            }
        """)
        self.repeat_btn.clicked.connect(self._toggle_mode)
        ctrl_box.addWidget(self.repeat_btn)

        # Volume Controls
        vol_box = QHBoxLayout()
        vol_box.setSpacing(6)
        vol_box.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Volume Button (Wheel enabled specifically here)
        self.vol_btn = VolumeButton()
        self.vol_btn.setFixedSize(26, 26)
        self.vol_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vol_btn.setToolTip("点击静音 (在此处滑动滚轮调节音量)")
        self.vol_btn.setIcon(make_volume_icon(16, self.music.is_muted(), "#CBD5E1"))
        self.vol_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 13px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        self.vol_btn.clicked.connect(self._toggle_mute)
        self.vol_btn.wheel_scrolled.connect(self._on_vol_wheel)
        vol_box.addWidget(self.vol_btn)

        # Volume Slider (Wheel enabled specifically here)
        self.vol_slider = VolumeSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(self.music.get_volume())
        self.vol_slider.setFixedWidth(68)
        self.vol_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vol_slider.setToolTip(f"音量: {self.music.get_volume()}% (在此处滑动滚轮微调)")
        self.vol_slider.setStyleSheet("""
            QSlider {
                background: transparent;
                height: 14px;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 0.16);
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #FFFFFF;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 9px;
                height: 9px;
                margin: -2.5px 0;
                background: #FFFFFF;
                border-radius: 4.5px;
            }
        """)
        self.vol_slider.valueChanged.connect(self._on_vol_changed)
        vol_box.addWidget(self.vol_slider)

        # Row 2: Apple Scrubber Slider & Countdown
        prog_row = QHBoxLayout()
        prog_row.setSpacing(8)

        self.time_cur_lbl = QLabel("00:00")
        self.time_cur_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #FFFFFF; min-width: 36px;")
        prog_row.addWidget(self.time_cur_lbl)

        self.progress_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.progress_slider.setStyleSheet("""
            QSlider {
                background: transparent;
                height: 16px;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 0.16);
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FA243C, stop:1 #FF5E62);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 11px;
                height: 11px;
                margin: -3.5px 0;
                background: #FFFFFF;
                border-radius: 5.5px;
            }
            QSlider::handle:horizontal:hover {
                width: 13px;
                height: 13px;
                margin: -4.5px 0;
                border-radius: 6.5px;
            }
        """)
        self.progress_slider.sliderPressed.connect(self._on_seek_pressed)
        self.progress_slider.sliderReleased.connect(self._on_seek_released)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        prog_row.addWidget(self.progress_slider, 1)

        self.time_tot_lbl = QLabel("-00:00")
        self.time_tot_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #86868B; min-width: 36px;")
        self.time_tot_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.time_tot_lbl.setToolTip("点击切换 剩余时间 / 总时长")
        self.time_tot_lbl.mousePressEvent = lambda e: self._toggle_time_display()
        prog_row.addWidget(self.time_tot_lbl)

        card_layout.addLayout(prog_row)

        # Row 3: Bottom Control Bar with Centered Transport Controls & Balanced Volume
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)
        bottom_row.setContentsMargins(0, 0, 0, 0)

        # Left balancer spacer (matching right volume width ~100px so transport buttons are dead-centered)
        left_spacer = QWidget()
        left_spacer.setFixedWidth(100)
        left_spacer.setStyleSheet("background: transparent;")
        bottom_row.addWidget(left_spacer)

        bottom_row.addStretch(1)
        bottom_row.addLayout(ctrl_box)
        bottom_row.addStretch(1)
        bottom_row.addLayout(vol_box)

        card_layout.addLayout(bottom_row)
        main_layout.addWidget(self.player_card)

        # 2. Compact Segmented Category Bar (Height 28px)
        self.cat_bar = QFrame()
        self.cat_bar.setFixedHeight(28)
        self.cat_bar.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }
        """)
        cat_layout = QHBoxLayout(self.cat_bar)
        cat_layout.setContentsMargins(4, 2, 4, 2)
        cat_layout.setSpacing(4)

        self.cat_buttons: Dict[str, QPushButton] = {}
        for cat_id, cat_name, icon_symbol in self.CATEGORIES:
            btn = QPushButton(f"{icon_symbol} {cat_name}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, cid=cat_id: self._select_category(cid))
            self.cat_buttons[cat_id] = btn
            cat_layout.addWidget(btn)

        main_layout.addWidget(self.cat_bar)
        self._update_category_buttons()

        # 3. Breadcrumb Navigation & Action Row (Height 28px)
        self.nav_header = QHBoxLayout()
        self.nav_header.setSpacing(6)

        # Back Button (Level-2 drilldown)
        self.back_btn = QPushButton("‹ 返回")
        self.back_btn.setObjectName("AppleBackButton")
        self.back_btn.setFixedHeight(26)
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setStyleSheet("""
            QPushButton#AppleBackButton {
                background: rgba(250, 45, 72, 0.16);
                color: #FA2D48;
                border: 1px solid rgba(250, 45, 72, 0.35);
                border-radius: 12px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton#AppleBackButton:hover {
                background: rgba(250, 45, 72, 0.28);
                border-color: #FA2D48;
            }
        """)
        self.back_btn.clicked.connect(self._navigate_back)
        self.back_btn.setVisible(False)
        self.nav_header.addWidget(self.back_btn)

        # Context Title Label (Level-2 drilldown)
        self.drilldown_title_lbl = ElidedLabel("")
        self.drilldown_title_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #FFFFFF;")
        self.drilldown_title_lbl.setVisible(False)
        self.nav_header.addWidget(self.drilldown_title_lbl, 1)

        # Search Bar Pill
        self.search_edit = QLineEdit()
        self.search_edit.setFixedHeight(26)
        self.search_edit.setPlaceholderText("🔍 搜索歌曲...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 13px;
                padding: 2px 10px;
                color: #FFFFFF;
                font-size: 11px;
            }
            QLineEdit:focus {
                background-color: rgba(255, 255, 255, 0.12);
                border-color: #FA2D48;
            }
        """)
        self.search_edit.textChanged.connect(self._on_search_changed)
        self.nav_header.addWidget(self.search_edit, 1)

        # Action Buttons (Level-1)
        self.add_files_btn = QPushButton(" 歌曲")
        self.add_files_btn.setIcon(make_plus_icon(12, "#FFFFFF"))
        self.add_files_btn.setFixedHeight(26)
        self.add_files_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_files_btn.setToolTip("添加歌曲文件")
        self.add_files_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 13px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.16);
            }
        """)
        self.add_files_btn.clicked.connect(self._choose_files)
        self.nav_header.addWidget(self.add_files_btn)

        self.add_folder_btn = QPushButton(" 目录")
        self.add_folder_btn.setIcon(make_folder_icon(12, "#FFFFFF"))
        self.add_folder_btn.setFixedHeight(26)
        self.add_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_folder_btn.setToolTip("导入整个音乐目录")
        self.add_folder_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 13px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.16);
            }
        """)
        self.add_folder_btn.clicked.connect(self._choose_folder)
        self.nav_header.addWidget(self.add_folder_btn)

        self.locate_btn = QPushButton("🎯")
        self.locate_btn.setFixedSize(26, 26)
        self.locate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.locate_btn.setToolTip("定位当前播放曲目")
        self.locate_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #A1A1A6;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 13px;
                font-size: 11px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(250, 45, 72, 0.2);
                color: #FA2D48;
            }
        """)
        self.locate_btn.clicked.connect(self._scroll_to_current)
        self.nav_header.addWidget(self.locate_btn)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.setFixedHeight(26)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 11px;
                color: #86868B;
                padding: 0 4px;
            }
            QPushButton:hover {
                color: #EF4444;
            }
        """)
        self.clear_btn.clicked.connect(self._clear_playlist)
        self.nav_header.addWidget(self.clear_btn)

        main_layout.addLayout(self.nav_header)

        # 4. High-Capacity Scrollable Area (Maximizes height: 8-10 songs or category groups!)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QFrame#AppleTrackItem {
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }
            QFrame#AppleTrackItem:hover {
                background-color: rgba(255, 255, 255, 0.06);
            }
            QFrame#AppleTrackActive {
                background-color: rgba(250, 45, 72, 0.14);
                border: 1px solid rgba(250, 45, 72, 0.35);
                border-radius: 6px;
            }
            QFrame#AppleTrackActive:hover {
                background-color: rgba(250, 45, 72, 0.20);
            }
            QFrame#AppleCategoryItem {
                background-color: transparent;
                border: none;
                border-radius: 8px;
            }
            QFrame#AppleCategoryItem:hover {
                background-color: rgba(255, 255, 255, 0.07);
            }
        """)

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(2)

        self.scroll_area.setWidget(self.list_container)
        main_layout.addWidget(self.scroll_area, 1)

    def _connect_signals(self):
        self.music.playback_state_changed.connect(self._on_playback_state)
        self.music.track_changed.connect(self._on_track_changed)
        self.music.cover_changed.connect(self._on_cover_changed)
        self.music.position_changed.connect(self._on_position_changed)
        self.music.playlist_changed.connect(self.reload_playlist)
        self.music.volume_changed.connect(self._on_volume_signal)
        self.music.mode_changed.connect(self._on_mode_changed)

    def _on_vol_wheel(self, delta: int):
        cur = self.music.get_volume()
        step = 4 if delta > 0 else -4
        self.music.set_volume(cur + step)

    def _select_category(self, cat_id: str):
        if self.current_category != cat_id:
            self.current_category = cat_id
            self.active_drilldown = None
            self.search_filter = ""
            self.search_edit.clear()
            self.rendered_count_limit = 80
            self._update_category_buttons()
            self.reload_playlist()

    def _update_category_buttons(self):
        active_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FA243C, stop:1 #FF5E62);
                color: #FFFFFF;
                border: none;
                border-radius: 11px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 700;
            }
        """
        normal_style = """
            QPushButton {
                background: transparent;
                color: #98989D;
                border: none;
                border-radius: 11px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background: rgba(255, 255, 255, 0.08);
            }
        """
        for cid, btn in self.cat_buttons.items():
            btn.setStyleSheet(active_style if cid == self.current_category else normal_style)

    def _on_drilldown_selected(self, key: str):
        """Navigate to Level-2 songs list inside the selected group."""
        self.active_drilldown = key
        self.search_filter = ""
        self.search_edit.clear()
        self.rendered_count_limit = 80
        self.reload_playlist()

    def _navigate_back(self):
        """Navigate back to Level-1 categories list."""
        self.active_drilldown = None
        self.search_filter = ""
        self.search_edit.clear()
        self.rendered_count_limit = 80
        self.reload_playlist()

    def _update_card_fav_icon(self):
        is_fav = self.music.is_favorite(self.music.current_track)
        self.card_fav_btn.setIcon(make_heart_icon(16, filled=is_fav, color="#FA2D48" if is_fav else "#86868B"))
        self.card_fav_btn.setToolTip("从个人喜爱移除" if is_fav else "添加到个人喜爱 (❤️)")

    def _toggle_card_favorite(self):
        if self.music.current_track:
            self.music.toggle_favorite(self.music.current_track)
            self._update_card_fav_icon()

    def _on_item_fav_toggled(self, track_index: int):
        self.music.toggle_favorite(track_index)
        self._update_card_fav_icon()

    def _update_shuffle_icon(self):
        is_shuf = (self.music.get_mode() == MusicService.MODE_SHUFFLE)
        self.shuffle_btn.setIcon(make_shuffle_icon(15, active=is_shuf, color="#FFFFFF"))

    def _update_repeat_icon(self):
        cur_mode = self.music.get_mode()
        self.repeat_btn.setIcon(make_repeat_icon(15, mode=cur_mode, color="#FFFFFF"))
        self.repeat_btn.setToolTip(f"循环模式: {cur_mode}")

    def _toggle_shuffle(self):
        if self.music.get_mode() == MusicService.MODE_SHUFFLE:
            self.music.mode_index = 0
            self.music.mode_changed.emit(MusicService.MODE_LIST_LOOP)
        else:
            self.music.mode_index = 2
            self.music.mode_changed.emit(MusicService.MODE_SHUFFLE)
        self._update_shuffle_icon()
        self._update_repeat_icon()

    def _on_playback_state(self, is_playing: bool):
        self.play_btn.setIcon(make_pause_icon(18, "#FFFFFF") if is_playing else make_play_icon(19, "#FFFFFF"))
        self.cover_widget.set_playing(is_playing)
        self.card_wave.set_playing(is_playing)
        self.card_wave.setVisible(is_playing)
        self.reload_playlist()

    def _on_track_changed(self, track: dict):
        if track:
            title = track.get("title", "未知曲目")
            self.now_title_lbl.setText(title)
            self.now_title_lbl.setToolTip(f"{title}\n路径: {track.get('path', '')}")
            artist = track.get("artist", "") or "未知歌手"
            album = track.get("album", "") or "单曲精选"
            sub_text = f"{artist} · {album}" if album != "单曲精选" else artist
            self.now_artist_lbl.setText(sub_text)

            # Apple Music audio quality badge
            filename = track.get("filename", "")
            badge = get_audio_quality_badge(filename)
            self.quality_badge.setText(badge)
            self.quality_badge.setVisible(True)

            self._update_card_fav_icon()
            self._on_cover_changed(self.music.get_current_cover_bytes())
        else:
            self.now_title_lbl.setText("未在播放音乐")
            self.now_title_lbl.setToolTip("")
            self.now_artist_lbl.setText("选择下方歌曲畅听")
            self.quality_badge.setVisible(False)
            self._update_card_fav_icon()
            self._on_cover_changed(None)
        self.reload_playlist()

    def _on_cover_changed(self, cover_bytes: Optional[bytes]):
        if hasattr(self, "cover_widget") and self.cover_widget:
            self.cover_widget.set_cover_bytes(cover_bytes)

    def _toggle_time_display(self):
        """Toggle right timestamp between Apple Music remaining countdown (-MM:SS) and total duration (MM:SS)."""
        self.show_remaining_time = not self.show_remaining_time
        dur = self.music.player.duration()
        pos = self.music.player.position()
        self._on_position_changed(pos, dur)

    def _on_position_changed(self, pos: int, dur: int):
        if not self.user_is_seeking:
            if dur > 0:
                pct = int((pos / dur) * 1000)
                self.progress_slider.setValue(pct)
            else:
                self.progress_slider.setValue(0)

        self.time_cur_lbl.setText(ms_to_str(pos))
        if self.show_remaining_time and dur > 0:
            rem_ms = max(0, dur - pos)
            self.time_tot_lbl.setText(f"-{ms_to_str(rem_ms)}")
        else:
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
            if self.show_remaining_time:
                rem_ms = max(0, dur - preview_ms)
                self.time_tot_lbl.setText(f"-{ms_to_str(rem_ms)}")
            else:
                self.time_tot_lbl.setText(ms_to_str(dur))

    def _toggle_mode(self):
        new_mode = self.music.toggle_mode()
        self._on_mode_changed(new_mode)

    def _on_mode_changed(self, mode: str):
        self._update_shuffle_icon()
        self._update_repeat_icon()

    def _toggle_mute(self):
        is_muted = self.music.toggle_mute()
        self.vol_btn.setIcon(make_volume_icon(16, is_muted, "#CBD5E1"))
        self.vol_slider.setValue(self.music.get_volume())

    def _on_vol_changed(self, vol: int):
        self.music.set_volume(vol)
        self.vol_slider.setToolTip(f"音量: {vol}% (在此处滑动滚轮微调)")
        self.vol_btn.setIcon(make_volume_icon(16, vol == 0, "#CBD5E1"))

    def _on_volume_signal(self, vol: int):
        if self.vol_slider.value() != vol:
            self.vol_slider.setValue(vol)
        self.vol_btn.setIcon(make_volume_icon(16, vol == 0, "#CBD5E1"))
        self.vol_slider.setToolTip(f"音量: {vol}% (在此处滑动滚轮微调)")

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
            "清空音乐资料库",
            f"确定要清空音乐资料库中的全部 {len(self.music.playlist)} 首歌曲吗？",
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
        # If in a category drilldown that doesn't include current track, switch to all
        if self.active_drilldown or self.current_category != "all":
            self.active_drilldown = None
            self._select_category("all")
        if self.search_filter:
            self.search_edit.clear()
        if hasattr(self, "_active_widget") and self._active_widget:
            self.scroll_area.ensureWidgetVisible(self._active_widget, 50, 50)

    def reload_playlist(self):
        # 1. Silently rebuild UI without intermediate repaints or flickers
        self.list_container.setUpdatesEnabled(False)
        try:
            # Hide and delete old widgets cleanly
            while self.list_layout.count() > 0:
                item = self.list_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.hide()
                    widget.deleteLater()

            playlist = self.music.playlist
            total_count = len(playlist)
            self._active_widget = None

            # Check if we should render Level-1 Directory or Level-2 Track List
            is_hierarchical_category = self.current_category in ("artists", "albums", "folders", "lossless")
            show_directory_level = is_hierarchical_category and (self.active_drilldown is None)

            # Update Navigation Header states
            if show_directory_level:
                self.back_btn.setVisible(False)
                self.drilldown_title_lbl.setVisible(False)
                self.add_files_btn.setVisible(True)
                self.add_folder_btn.setVisible(True)
                self.clear_btn.setVisible(True)
                if self.current_category == "artists":
                    self.search_edit.setPlaceholderText("🔍 搜索歌手...")
                elif self.current_category == "albums":
                    self.search_edit.setPlaceholderText("🔍 搜索专辑名称或歌手...")
                elif self.current_category == "folders":
                    self.search_edit.setPlaceholderText("🔍 搜索目录...")
                elif self.current_category == "lossless":
                    self.search_edit.setPlaceholderText("🔍 搜索无损格式...")
            else:
                if is_hierarchical_category:
                    cat_name_map = {"artists": "歌手", "albums": "专辑", "folders": "目录", "lossless": "格式"}
                    back_label = f"‹ 返回{cat_name_map.get(self.current_category, '')}"
                    self.back_btn.setText(back_label)
                    self.back_btn.setVisible(True)
                    self.drilldown_title_lbl.setText(f"{self.active_drilldown}")
                    self.drilldown_title_lbl.setVisible(True)
                    self.add_files_btn.setVisible(False)
                    self.add_folder_btn.setVisible(False)
                    self.clear_btn.setVisible(False)
                    self.search_edit.setPlaceholderText("🔍 搜索当前列表中的曲目...")
                else:
                    self.back_btn.setVisible(False)
                    self.drilldown_title_lbl.setVisible(False)
                    self.add_files_btn.setVisible(True)
                    self.add_folder_btn.setVisible(True)
                    self.clear_btn.setVisible(True)
                    self.search_edit.setPlaceholderText("🔍 搜索歌曲、歌手、专辑或格式...")

            # -----------------------------------------------------------------
            # Level 1 Directory Rendering (Albums / Artists / Folders / Lossless)
            # Memory-only lookup: Instant zero-latency switching with 0 disk I/O!
            # -----------------------------------------------------------------
            if show_directory_level:
                cats = self.music.get_categories()
                group_items = []

                if self.current_category == "artists":
                    artists_dict = cats.get("artists", {})
                    for art_name, indices in sorted(artists_dict.items(), key=lambda x: len(x[1]), reverse=True):
                        if not self.search_filter or self.search_filter in art_name.lower():
                            first_track = playlist[indices[0]] if indices else {}
                            cov = self.music._cover_cache.get(first_track.get("path", ""))
                            group_items.append((art_name, art_name, f"艺人 · {len(indices)} 首歌曲", len(indices), "artist", cov))

                elif self.current_category == "albums":
                    albums_dict = cats.get("albums", {})
                    for alb_name, indices in sorted(albums_dict.items(), key=lambda x: len(x[1]), reverse=True):
                        first_track = playlist[indices[0]] if indices else {}
                        artist = first_track.get("artist") or "未知歌手"
                        if not self.search_filter or (self.search_filter in alb_name.lower() or self.search_filter in artist.lower()):
                            cov = self.music._cover_cache.get(first_track.get("path", ""))
                            group_items.append((alb_name, alb_name, f"{artist} · {len(indices)} 首歌曲", len(indices), "album", cov))

                elif self.current_category == "folders":
                    folders_dict = cats.get("folders", {})
                    for fld_name, indices in sorted(folders_dict.items(), key=lambda x: len(x[1]), reverse=True):
                        if not self.search_filter or self.search_filter in fld_name.lower():
                            group_items.append((fld_name, fld_name, f"本地目录 · {len(indices)} 首歌曲", len(indices), "folder", None))

                elif self.current_category == "lossless":
                    formats: Dict[str, List[int]] = {}
                    for idx in cats.get("lossless", []):
                        fmt = playlist[idx].get("format", "LOSSLESS")
                        formats.setdefault(fmt, []).append(idx)

                    all_lossless_count = len(cats.get("lossless", []))
                    if all_lossless_count > 0:
                        group_items.append(("__all_lossless__", "全部无损音频", "高解析及无损音频合集", all_lossless_count, "lossless", None))

                    for fmt, indices in sorted(formats.items(), key=lambda x: len(x[1]), reverse=True):
                        if not self.search_filter or self.search_filter in fmt.lower():
                            desc = "高解析原声音频" if fmt == "WAV" else "高保真无损压缩音频"
                            group_items.append((fmt, f"{fmt} 原声", f"{desc} · {len(indices)} 首歌曲", len(indices), "lossless", None))

                # Empty state for directory level
                if not group_items:
                    self._render_empty_state("该分类暂无数据", "请尝试导入新的音频文件或选择其他分类")
                    return

                # Render directory items
                for key, title, subtitle, count, icon_type, cov in group_items[:self.rendered_count_limit]:
                    row_item = CategoryGroupItemWidget(key, title, subtitle, count, icon_type, cov)
                    row_item.clicked.connect(self._on_drilldown_selected)
                    self.list_layout.addWidget(row_item)

                if len(group_items) > self.rendered_count_limit:
                    remaining = len(group_items) - self.rendered_count_limit
                    more_btn = QPushButton(f"▼ 查看更多分类项 (还有 {remaining} 项)...")
                    more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    more_btn.setStyleSheet("""
                        QPushButton {
                            background: rgba(255, 255, 255, 0.06);
                            color: #FA2D48;
                            border: 1px dashed rgba(250, 45, 72, 0.35);
                            border-radius: 6px;
                            padding: 6px;
                            font-size: 11px;
                            font-weight: 600;
                        }
                        QPushButton:hover { background: rgba(250, 45, 72, 0.15); border-color: #FA2D48; }
                    """)
                    more_btn.clicked.connect(self._load_more)
                    self.list_layout.addWidget(more_btn)

                self.list_layout.addStretch()
                return

            # -----------------------------------------------------------------
            # Level 2 Track List Rendering (or Level 1 for All / Favorites)
            # -----------------------------------------------------------------
            cat_filtered: List[tuple[int, dict]] = []
            for i, track in enumerate(playlist):
                if self.current_category == "favorites":
                    if not track.get("favorite", False):
                        continue
                elif self.current_category == "lossless":
                    if not track.get("is_lossless", False):
                        continue
                    if self.active_drilldown and self.active_drilldown != "__all_lossless__":
                        if track.get("format") != self.active_drilldown:
                            continue
                elif self.current_category == "artists" and self.active_drilldown:
                    if track.get("artist") != self.active_drilldown:
                        continue
                elif self.current_category == "albums" and self.active_drilldown:
                    if track.get("album") != self.active_drilldown:
                        continue
                elif self.current_category == "folders" and self.active_drilldown:
                    if track.get("folder") != self.active_drilldown:
                        continue
                cat_filtered.append((i, track))

            # Search filter
            filtered_items = []
            for orig_idx, track in cat_filtered:
                if not self.search_filter:
                    filtered_items.append((orig_idx, track))
                else:
                    title = track.get("title", "").lower()
                    artist = track.get("artist", "").lower()
                    album = track.get("album", "").lower()
                    filename = track.get("filename", "").lower()
                    ext = Path(filename).suffix.lower()
                    if (self.search_filter in title or
                        self.search_filter in artist or
                        self.search_filter in album or
                        self.search_filter in filename or
                        self.search_filter in ext):
                        filtered_items.append((orig_idx, track))

            # Empty state for track list
            if not playlist or not filtered_items:
                empty_title = "暂无喜爱的歌曲" if self.current_category == "favorites" else "未找到匹配曲目"
                empty_sub = "点击曲目右侧红心即可收藏" if self.current_category == "favorites" else "请尝试其他关键词或返回上一级"
                self._render_empty_state(empty_title, empty_sub)
                return

            # Render track rows
            items_to_render = filtered_items[:self.rendered_count_limit]
            for orig_idx, track in items_to_render:
                is_cur = (orig_idx == self.music.current_index)
                is_play = is_cur and self.music.is_playing
                thumb_pix = self.cover_widget.pixmap if is_cur else None
                item_widget = PlaylistItemWidget(orig_idx, track, is_cur, is_play, cover_pixmap=thumb_pix)
                item_widget.play_requested.connect(self.music.play_track)
                item_widget.delete_requested.connect(self.music.remove_track)
                item_widget.favorite_toggled.connect(self._on_item_fav_toggled)
                self.list_layout.addWidget(item_widget)

                if is_cur:
                    self._active_widget = item_widget

            # Load more button
            remaining = len(filtered_items) - len(items_to_render)
            if remaining > 0:
                load_more_btn = QPushButton(f"▼ 查看更多曲目 (还有 {remaining} 首)...")
                load_more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                load_more_btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.06);
                        color: #FA2D48;
                        border: 1px dashed rgba(250, 45, 72, 0.35);
                        border-radius: 6px;
                        padding: 6px;
                        font-size: 11px;
                        font-weight: 600;
                    }
                    QPushButton:hover { background: rgba(250, 45, 72, 0.15); border-color: #FA2D48; }
                """)
                load_more_btn.clicked.connect(self._load_more)
                self.list_layout.addWidget(load_more_btn)

            self.list_layout.addStretch()

        finally:
            self.list_container.setUpdatesEnabled(True)
            self.scroll_area.verticalScrollBar().setValue(0)

    def _render_empty_state(self, title: str, subtitle: str):
        empty_frame = QFrame()
        empty_frame.setStyleSheet("""
            QFrame {
                background: rgba(25, 28, 42, 0.6);
                border: 2px dashed rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                padding: 20px;
            }
        """)
        empty_layout = QVBoxLayout(empty_frame)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(8)

        empty_icon = "❤️" if self.current_category == "favorites" else "🎵"
        icon_lbl = QLabel(empty_icon)
        icon_lbl.setStyleSheet("font-size: 32px;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(icon_lbl)

        hint_title = QLabel(title)
        hint_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        hint_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(hint_title)

        hint_sub = QLabel(subtitle)
        hint_sub.setStyleSheet("font-size: 11px; color: #86868B;")
        hint_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(hint_sub)

        if not self.music.playlist:
            btn_box = QHBoxLayout()
            btn_box.setSpacing(8)
            btn_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

            add_btn = QPushButton(" 添加歌曲文件")
            add_btn.setIcon(make_plus_icon(12, "#FFFFFF"))
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FA243C, stop:1 #FF5E62);
                    color: #FFFFFF;
                    font-size: 11px;
                    font-weight: 600;
                    border-radius: 12px;
                    padding: 5px 14px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF3B53, stop:1 #FF7579);
                }
            """)
            add_btn.clicked.connect(self._choose_files)
            btn_box.addWidget(add_btn)

            dir_btn = QPushButton(" 导入音乐文件夹")
            dir_btn.setIcon(make_folder_icon(12, "#FFFFFF"))
            dir_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            dir_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.1);
                    color: #FFFFFF;
                    font-size: 11px;
                    font-weight: 500;
                    border-radius: 12px;
                    padding: 5px 14px;
                }
                QPushButton:hover { background: rgba(255, 255, 255, 0.18); }
            """)
            dir_btn.clicked.connect(self._choose_folder)
            btn_box.addWidget(dir_btn)

            empty_layout.addLayout(btn_box)

        self.list_layout.addWidget(empty_frame)

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
