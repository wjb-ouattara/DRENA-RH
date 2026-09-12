"""
========================================================================
DRENAET-RH — Mixin pour rendre une fenêtre frameless redimensionnable
========================================================================
Quand on supprime la barre titre native Windows (FramelessWindowHint),
on perd aussi les bords de redimensionnement. Ce mixin les réactive
en interceptant les événements souris sur les 8 zones de bords :

    NW   N   NE
     ┌───┬───┐
    W│       │E
     ├───┼───┤
    SW   S   SE

Usage :
    class MyWindow(ResizableWindowMixin, QMainWindow):
        def __init__(self):
            super().__init__()
            self.setMouseTracking(True)
            self.init_resize_tracking()
"""

from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QMouseEvent, QCursor


class ResizableWindowMixin:
    """Mixin pour rendre une fenêtre frameless redimensionnable."""

    # Largeur de la zone de bord (pixels) pour le resize
    EDGE_MARGIN = 6

    # États de redimensionnement
    EDGE_NONE = 0
    EDGE_LEFT = 1
    EDGE_RIGHT = 2
    EDGE_TOP = 4
    EDGE_BOTTOM = 8
    EDGE_TOP_LEFT = EDGE_TOP | EDGE_LEFT
    EDGE_TOP_RIGHT = EDGE_TOP | EDGE_RIGHT
    EDGE_BOTTOM_LEFT = EDGE_BOTTOM | EDGE_LEFT
    EDGE_BOTTOM_RIGHT = EDGE_BOTTOM | EDGE_RIGHT

    def init_resize_tracking(self):
        """À appeler dans __init__ après super().__init__()."""
        self._resize_edge = self.EDGE_NONE
        self._is_resizing = False
        self._resize_start_pos: QPoint = None
        self._resize_start_geom: QRect = None
        self.setMouseTracking(True)

    # ====================================================================
    def _get_edge_at_position(self, pos: QPoint) -> int:
        """Détermine sur quel bord se trouve la souris."""
        if self.isMaximized():
            return self.EDGE_NONE

        rect = self.rect()
        x, y = pos.x(), pos.y()
        w, h = rect.width(), rect.height()
        m = self.EDGE_MARGIN

        edge = self.EDGE_NONE
        if x < m:
            edge |= self.EDGE_LEFT
        elif x > w - m:
            edge |= self.EDGE_RIGHT

        if y < m:
            edge |= self.EDGE_TOP
        elif y > h - m:
            edge |= self.EDGE_BOTTOM

        return edge

    # ====================================================================
    def _update_cursor(self, edge: int):
        """Met à jour le curseur selon le bord."""
        cursors = {
            self.EDGE_LEFT: Qt.CursorShape.SizeHorCursor,
            self.EDGE_RIGHT: Qt.CursorShape.SizeHorCursor,
            self.EDGE_TOP: Qt.CursorShape.SizeVerCursor,
            self.EDGE_BOTTOM: Qt.CursorShape.SizeVerCursor,
            self.EDGE_TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
            self.EDGE_BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
            self.EDGE_TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
            self.EDGE_BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
        }
        cursor_shape = cursors.get(edge, Qt.CursorShape.ArrowCursor)
        self.setCursor(QCursor(cursor_shape))

    # ====================================================================
    # ÉVÉNEMENTS SOURIS (override dans la classe utilisant le mixin)
    # ====================================================================
    def mousePressEvent(self, event: QMouseEvent):
        """Démarre le redimensionnement si on est sur un bord."""
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_edge_at_position(event.position().toPoint())
            if edge != self.EDGE_NONE:
                self._is_resizing = True
                self._resize_edge = edge
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geom = self.geometry()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Met à jour le curseur et redimensionne si actif."""
        if self._is_resizing and self._resize_start_pos and self._resize_start_geom:
            # On est en train de redimensionner
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            geom = QRect(self._resize_start_geom)
            edge = self._resize_edge

            min_w = self.minimumWidth() if self.minimumWidth() > 0 else 600
            min_h = self.minimumHeight() if self.minimumHeight() > 0 else 400

            if edge & self.EDGE_LEFT:
                new_x = geom.x() + delta.x()
                new_w = geom.width() - delta.x()
                if new_w >= min_w:
                    geom.setX(new_x)
                    geom.setWidth(new_w)
            elif edge & self.EDGE_RIGHT:
                new_w = geom.width() + delta.x()
                if new_w >= min_w:
                    geom.setWidth(new_w)

            if edge & self.EDGE_TOP:
                new_y = geom.y() + delta.y()
                new_h = geom.height() - delta.y()
                if new_h >= min_h:
                    geom.setY(new_y)
                    geom.setHeight(new_h)
            elif edge & self.EDGE_BOTTOM:
                new_h = geom.height() + delta.y()
                if new_h >= min_h:
                    geom.setHeight(new_h)

            self.setGeometry(geom)
            event.accept()
            return

        # Pas en train de resize : mettre à jour le curseur
        if not event.buttons():
            edge = self._get_edge_at_position(event.position().toPoint())
            self._update_cursor(edge)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Arrête le redimensionnement."""
        if self._is_resizing:
            self._is_resizing = False
            self._resize_edge = self.EDGE_NONE
            self._resize_start_pos = None
            self._resize_start_geom = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()
            return
        super().mouseReleaseEvent(event)