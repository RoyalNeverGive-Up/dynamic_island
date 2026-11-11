# ui/components/icons.py - Programmatically rendered crisp vector QIcons
# Immune to Windows font fallback issues, emoji rendering bugs, and character clipping.

from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, QSize

def make_close_icon(size: int = 16, color: str = "#FFFFFF") -> QIcon:
    """Crisp, antialiased '✕' cross icon."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    pen = QPen(QColor(color), 2.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    
    margin = max(3, size // 4)
    p.drawLine(margin, margin, size - margin, size - margin)
    p.drawLine(size - margin, margin, margin, size - margin)
    p.end()
    return QIcon(pix)


def make_collapse_icon(size: int = 16, color: str = "#FFFFFF") -> QIcon:
    """Crisp, antialiased upward chevron '⌃' icon for collapsing."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    pen = QPen(QColor(color), 2.2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    
    left = 3
    right = size - 3
    center_x = size // 2
    top_y = max(4, size // 4)
    bot_y = size - max(4, size // 3)
    
    p.drawLine(left, bot_y, center_x, top_y)
    p.drawLine(center_x, top_y, right, bot_y)
    p.end()
    return QIcon(pix)


def make_pin_icon(size: int = 18, pinned: bool = False, color: str = "#CBD5E1") -> QIcon:
    """Crisp, antialiased pushpin icon with active/inactive states."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    active_color = "#38BDF8"
    draw_color = QColor(active_color if pinned else color)
    
    # 1. Needle (drawn below head)
    needle_pen = QPen(QColor("#94A3B8" if not pinned else active_color), 2.0)
    needle_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(needle_pen)
    p.drawLine(size // 2, 10, size // 2, size - 2)
    
    # 2. Pin Body / Head
    pen = QPen(draw_color, 1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    
    if pinned:
        p.setBrush(QBrush(draw_color))
    else:
        p.setBrush(QBrush(QColor(255, 255, 255, 30)))
        
    # Draw pin cap & base
    cx = size // 2
    # Top knob
    p.drawEllipse(cx - 3, 2, 6, 6)
    # Middle body
    p.drawRect(cx - 4, 7, 8, 4)
    
    p.end()
    return QIcon(pix)


def make_play_icon(size: int = 16, color: str = "#FFFFFF") -> QIcon:
    """Crisp, antialiased right-pointing play triangle."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color)))
    pad_x = size * 0.28
    pad_y = size * 0.2
    poly = QPolygonF([
        QPointF(pad_x, pad_y),
        QPointF(size - pad_x * 0.75, size / 2.0),
        QPointF(pad_x, size - pad_y)
    ])
    p.drawPolygon(poly)
    p.end()
    return QIcon(pix)


def make_pause_icon(size: int = 16, color: str = "#FFFFFF") -> QIcon:
    """Crisp, antialiased double vertical pause bars."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color)))
    bar_w = max(2.5, size * 0.22)
    bar_h = size * 0.58
    pad_y = (size - bar_h) / 2.0
    gap = size * 0.16
    left_x = (size - (2 * bar_w + gap)) / 2.0
    p.drawRoundedRect(QRectF(left_x, pad_y, bar_w, bar_h), bar_w / 2, bar_w / 2)
    p.drawRoundedRect(QRectF(left_x + bar_w + gap, pad_y, bar_w, bar_h), bar_w / 2, bar_w / 2)
    p.end()
    return QIcon(pix)


def make_prev_icon(size: int = 16, color: str = "#FFFFFF") -> QIcon:
    """Crisp, antialiased previous track (bar + left triangle) icon."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color)))
    bar_w = max(2.0, size * 0.12)
    p.drawRoundedRect(QRectF(size * 0.18, size * 0.22, bar_w, size * 0.56), 1.0, 1.0)
    poly = QPolygonF([
        QPointF(size * 0.82, size * 0.22),
        QPointF(size * 0.34, size * 0.5),
        QPointF(size * 0.82, size * 0.78)
    ])
    p.drawPolygon(poly)
    p.end()
    return QIcon(pix)


def make_next_icon(size: int = 16, color: str = "#FFFFFF") -> QIcon:
    """Crisp, antialiased next track (right triangle + bar) icon."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color)))
    poly = QPolygonF([
        QPointF(size * 0.18, size * 0.22),
        QPointF(size * 0.66, size * 0.5),
        QPointF(size * 0.18, size * 0.78)
    ])
    p.drawPolygon(poly)
    bar_w = max(2.0, size * 0.12)
    p.drawRoundedRect(QRectF(size * 0.72, size * 0.22, bar_w, size * 0.56), 1.0, 1.0)
    p.end()
    return QIcon(pix)


def make_volume_icon(size: int = 16, muted: bool = False, color: str = "#FFFFFF") -> QIcon:
    """Crisp, antialiased volume speaker & soundwave icon."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color if not muted else "#EF4444")))
    poly = QPolygonF([
        QPointF(size * 0.15, size * 0.38),
        QPointF(size * 0.36, size * 0.38),
        QPointF(size * 0.58, size * 0.2),
        QPointF(size * 0.58, size * 0.8),
        QPointF(size * 0.36, size * 0.62),
        QPointF(size * 0.15, size * 0.62),
    ])
    p.drawPolygon(poly)
    if muted:
        pen = QPen(QColor("#EF4444"), 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(size * 0.7, size * 0.36), QPointF(size * 0.9, size * 0.64))
        p.drawLine(QPointF(size * 0.9, size * 0.36), QPointF(size * 0.7, size * 0.64))
    else:
        pen = QPen(QColor(color), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(size * 0.46, size * 0.32, size * 0.3, size * 0.36), -60 * 16, 120 * 16)
        p.drawArc(QRectF(size * 0.44, size * 0.18, size * 0.46, size * 0.64), -60 * 16, 120 * 16)
    p.end()
    return QIcon(pix)
