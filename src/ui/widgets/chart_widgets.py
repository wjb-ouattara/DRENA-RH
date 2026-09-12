"""
========================================================================
DRENAET-RH — Widgets de graphiques (QPainter, sans dépendance externe)
========================================================================
2 widgets réutilisables :
- BarChartWidget  : graphique en barres verticales
- DonutChartWidget : graphique en anneau (donut) avec légende

Conçus pour être légers (pas de matplotlib/pyqtgraph), cohérents avec
le style visuel DRENAET-RH (couleurs, arrondis, typographie).
"""

from typing import List, Dict, Any

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPainterPath
from PyQt6.QtWidgets import QWidget, QSizePolicy


DEFAULT_PALETTE = [
    "#4338CA", "#7C3AED", "#EC4899", "#10B981", "#F59E0B",
    "#3B82F6", "#DC2626", "#8B5CF6", "#06B6D4", "#64748B",
]


# ========================================================================
class BarChartWidget(QWidget):
    """Graphique en barres verticales avec labels."""

    def __init__(self, data: List[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.data = data or []
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data: List[Dict[str, Any]]):
        """data = [{"label": str, "value": int, "color": optional str}]"""
        self.data = data or []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        if not self.data:
            painter.setPen(QColor("#94A3B8"))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(
                QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "Aucune donnée disponible"
            )
            painter.end()
            return

        # Marges
        margin_left = 40
        margin_right = 20
        margin_top = 20
        margin_bottom = 50

        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        max_value = max((d["value"] for d in self.data), default=1)
        max_value = max(max_value, 1)

        n = len(self.data)
        bar_spacing = 12
        bar_width = max(20, (chart_w - (n - 1) * bar_spacing) / n) if n else 20
        bar_width = min(bar_width, 60)

        # Axe Y : 4 graduations
        painter.setPen(QPen(QColor("#E2E8F0"), 1))
        painter.setFont(QFont("Arial", 8))
        for i in range(5):
            y_val = max_value * i / 4
            y = margin_top + chart_h - (chart_h * i / 4)
            painter.drawLine(
                QPointF(margin_left, y), QPointF(w - margin_right, y)
            )
            painter.setPen(QColor("#94A3B8"))
            painter.drawText(
                QRectF(0, y - 8, margin_left - 6, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                str(int(y_val)),
            )
            painter.setPen(QPen(QColor("#E2E8F0"), 1))

        # Barres
        total_bars_width = n * bar_width + (n - 1) * bar_spacing
        start_x = margin_left + max(0, (chart_w - total_bars_width) / 2)

        for i, item in enumerate(self.data):
            value = item["value"]
            label = item["label"]
            color = item.get("color") or DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)]

            bar_h = (value / max_value) * chart_h if max_value else 0
            x = start_x + i * (bar_width + bar_spacing)
            y = margin_top + chart_h - bar_h

            # Barre avec coins arrondis en haut
            path = QPainterPath()
            radius = min(6, bar_width / 2)
            rect = QRectF(x, y, bar_width, bar_h)
            path.addRoundedRect(rect, radius, radius)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(color)))
            painter.drawPath(path)

            # Valeur au-dessus de la barre
            painter.setPen(QColor("#1E1B4B"))
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            painter.drawText(
                QRectF(x - 10, y - 20, bar_width + 20, 16),
                Qt.AlignmentFlag.AlignCenter, str(value),
            )

            # Label en bas (rotation si trop long)
            painter.setPen(QColor("#64748B"))
            painter.setFont(QFont("Arial", 8))
            label_rect = QRectF(x - 20, margin_top + chart_h + 8, bar_width + 40, 40)

            display_label = label if len(label) <= 12 else label[:11] + "…"
            painter.drawText(
                label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, display_label
            )

        painter.end()


# ========================================================================
class DonutChartWidget(QWidget):
    """Graphique en anneau (donut) avec légende à droite."""

    def __init__(self, data: List[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.data = data or []
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data: List[Dict[str, Any]]):
        """data = [{"label": str, "value": int, "color": optional str}]"""
        self.data = data or []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        total = sum(d["value"] for d in self.data) if self.data else 0

        if not self.data or total == 0:
            painter.setPen(QColor("#94A3B8"))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(
                QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "Aucune donnée disponible"
            )
            painter.end()
            return

        # Zone du donut (partie gauche) + légende (partie droite)
        donut_size = min(h - 20, w * 0.5)
        donut_size = max(donut_size, 100)
        cx = 20 + donut_size / 2
        cy = h / 2
        outer_radius = donut_size / 2
        inner_radius = outer_radius * 0.6

        rect = QRectF(cx - outer_radius, cy - outer_radius, outer_radius * 2, outer_radius * 2)

        start_angle = 90 * 16  # Qt utilise 1/16e de degré, on démarre en haut
        for i, item in enumerate(self.data):
            value = item["value"]
            color = item.get("color") or DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)]
            span_angle = -int((value / total) * 360 * 16)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(color)))
            painter.drawPie(rect, start_angle, span_angle)

            start_angle += span_angle

        # Trou du donut (fond de la fenêtre)
        bg_color = self.palette().window().color()
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.setPen(Qt.PenStyle.NoPen)
        inner_rect = QRectF(cx - inner_radius, cy - inner_radius, inner_radius * 2, inner_radius * 2)
        painter.drawEllipse(inner_rect)

        # Total au centre
        painter.setPen(QColor("#1E1B4B"))
        painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        painter.drawText(inner_rect, Qt.AlignmentFlag.AlignCenter, str(total))

        # Légende à droite
        legend_x = cx + outer_radius + 24
        legend_y = cy - (len(self.data) * 24) / 2
        painter.setFont(QFont("Arial", 9))

        for i, item in enumerate(self.data):
            color = item.get("color") or DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)]
            y = legend_y + i * 24

            # Puce couleur
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(legend_x, y + 4, 10, 10))

            # Label + valeur
            pct = round((item["value"] / total) * 100, 1) if total else 0
            painter.setPen(QColor("#1E1B4B"))
            text = f"{item['label']} ({item['value']} • {pct}%)"
            painter.drawText(
                QRectF(legend_x + 16, y, w - legend_x - 16, 20),
                Qt.AlignmentFlag.AlignVCenter, text,
            )

        painter.end()


# ========================================================================
class LineChartWidget(QWidget):
    """Graphique en courbe simple (évolution dans le temps)."""

    def __init__(self, data: List[Dict[str, Any]] = None, color: str = "#4338CA", parent=None):
        super().__init__(parent)
        self.data = data or []
        self.color = color
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data: List[Dict[str, Any]]):
        self.data = data or []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        if not self.data:
            painter.setPen(QColor("#94A3B8"))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "Aucune donnée")
            painter.end()
            return

        margin_left = 30
        margin_right = 20
        margin_top = 20
        margin_bottom = 30
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        max_value = max((d["value"] for d in self.data), default=1)
        max_value = max(max_value, 1)
        n = len(self.data)

        # Grille horizontale
        painter.setPen(QPen(QColor("#F1F5F9"), 1))
        for i in range(4):
            y = margin_top + chart_h * i / 3
            painter.drawLine(QPointF(margin_left, y), QPointF(w - margin_right, y))

        # Points de la courbe
        points = []
        step_x = chart_w / max(1, n - 1) if n > 1 else 0
        for i, item in enumerate(self.data):
            x = margin_left + i * step_x
            y = margin_top + chart_h - (item["value"] / max_value) * chart_h
            points.append(QPointF(x, y))

        # Zone remplie sous la courbe
        if len(points) > 1:
            fill_path = QPainterPath()
            fill_path.moveTo(points[0].x(), margin_top + chart_h)
            for p in points:
                fill_path.lineTo(p)
            fill_path.lineTo(points[-1].x(), margin_top + chart_h)
            fill_path.closeSubpath()

            fill_color = QColor(self.color)
            fill_color.setAlpha(30)
            painter.setBrush(QBrush(fill_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(fill_path)

        # Ligne de la courbe
        if len(points) > 1:
            painter.setPen(QPen(QColor(self.color), 2.5))
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])

        # Points
        painter.setBrush(QBrush(QColor(self.color)))
        painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
        for p in points:
            painter.drawEllipse(p, 4, 4)

        # Labels axe X
        painter.setPen(QColor("#64748B"))
        painter.setFont(QFont("Arial", 8))
        for i, item in enumerate(self.data):
            x = margin_left + i * step_x
            painter.drawText(
                QRectF(x - 15, margin_top + chart_h + 6, 30, 16),
                Qt.AlignmentFlag.AlignCenter, item["label"],
            )

        painter.end()