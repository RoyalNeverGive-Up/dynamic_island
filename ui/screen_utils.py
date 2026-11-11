"""
Multi-monitor aware screen geometry and edge-snapping utilities.
Supports multi-display topologies, DPI scaling, and drop-shadow margin compensation.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QScreen
from PyQt6.QtCore import QPoint, QRect
from config import SHADOW_MARGIN


def get_screen_at_point(point: QPoint) -> QScreen:
    """Find the screen containing point, or the screen closest to point."""
    screen = QApplication.screenAt(point)
    if screen:
        return screen
    closest = QApplication.primaryScreen()
    min_dist = float('inf')
    for s in QApplication.screens():
        geom = s.geometry()
        dx = max(geom.left() - point.x(), 0, point.x() - geom.right())
        dy = max(geom.top() - point.y(), 0, point.y() - geom.bottom())
        dist = dx * dx + dy * dy
        if dist < min_dist:
            min_dist = dist
            closest = s
    return closest


def get_virtual_desktop_rect() -> QRect:
    """Return the bounding union of all display screens."""
    total = QRect()
    for s in QApplication.screens():
        total = total.united(s.geometry())
    return total


def clamp_window_to_edges(
    target_pos: QPoint,
    win_width: int,
    win_height: int,
    cursor_pos: QPoint,
    snap_distance: int = 16,
    strict_contain: bool = False
) -> QPoint:
    """
    Given an intended window top-left target_pos, adjust target_pos so that:
    1. The visual capsule (accounting for SHADOW_MARGIN) can touch the edges of the display area (0px gap).
    2. Gently snaps to the outer edges of the active screen and taskbar within snap_distance.
    3. Window never gets lost off-screen.
    4. If strict_contain is True (used on drag release / window resize), clamps fully inside active screen edges.
    """
    cur_screen = get_screen_at_point(cursor_pos)
    s_geom = cur_screen.geometry()
    s_avail = cur_screen.availableGeometry()
    virt_rect = get_virtual_desktop_rect()
    margin = SHADOW_MARGIN

    # Outer edges for active screen (where the visual content touches screen borders)
    edge_left_x = s_geom.left() - margin
    edge_right_x = s_geom.right() + 1 - win_width + margin
    edge_top_y = s_geom.top() - margin
    edge_bottom_y = s_geom.bottom() + 1 - win_height + margin
    avail_bottom_y = s_avail.bottom() + 1 - win_height + margin

    # Virtual desktop outer bounds
    min_virt_x = virt_rect.left() - margin
    max_virt_x = virt_rect.right() + 1 - win_width + margin

    x = target_pos.x()
    y = target_pos.y()

    if strict_contain:
        # On release / settle: ensure the window visual edges remain inside current screen
        x = max(edge_left_x, min(edge_right_x, x))
        y = max(edge_top_y, min(edge_bottom_y, y))
    else:
        # X snapping and clamping
        if abs(x - edge_left_x) <= snap_distance:
            x = edge_left_x
        elif abs(x - edge_right_x) <= snap_distance:
            x = edge_right_x
        # Hard clamp against virtual desktop bounds
        x = max(min_virt_x, min(max_virt_x, x))

        # Y snapping and clamping
        if abs(y - edge_top_y) <= snap_distance or y < edge_top_y:
            y = edge_top_y
        elif abs(y - avail_bottom_y) <= snap_distance:
            y = avail_bottom_y
        elif abs(y - edge_bottom_y) <= snap_distance or y > edge_bottom_y:
            y = edge_bottom_y
        else:
            y = max(edge_top_y, min(edge_bottom_y, y))

    return QPoint(x, y)
