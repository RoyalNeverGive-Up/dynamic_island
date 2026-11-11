# ui/components/icons.py - Programmatically rendered crisp vector QIcons
# Immune to Windows font fallback issues, emoji rendering bugs, and character clipping.

from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush
from PyQt6.QtCore import Qt, QPoint, QSize

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
