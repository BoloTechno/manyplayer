from typing import List, Tuple, Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect, QPointF
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush
from src.domain.geometry import LineSegment
from src.domain.entities import CounterState
from src.core.ai_detector import Detection


class HUDOverlay(QWidget):
    """Transparent overlay rendering live People Counter HUD statistics and normalized virtual tripwire."""

    def __init__(
        self,
        normalized_tripwire: LineSegment,
        counter_state: CounterState,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.tripwire = normalized_tripwire
        self.counter_state = counter_state
        self._tracked_boxes: List[Tuple[int, Detection]] = []
        self._frame_dims: Tuple[int, int] = (640, 360)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_tracked_boxes(self, tracked_boxes: List[Tuple[int, Detection]], frame_dims: Tuple[int, int] = (640, 360)) -> None:
        """Sets current frame tracked bounding boxes and their source frame resolution."""
        self._tracked_boxes = tracked_boxes
        self._frame_dims = frame_dims
        self.update()

    def update_stats(self) -> None:
        """Triggers a redraw of the HUD numbers."""
        self.update()

    def _get_video_target_rect(self) -> QRect:
        """Calculates the 16:9 aspect ratio target rectangle matching the underlying VideoTile."""
        w = self.width()
        h = self.height()
        target_w = w
        target_h = int(w * 9 / 16)
        if target_h > h:
            target_h = h
            target_w = int(h * 16 / 9)

        x_offset = (w - target_w) // 2
        y_offset = (h - target_h) // 2
        return QRect(x_offset, y_offset, target_w, target_h)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        target_rect = self._get_video_target_rect()
        offset_x = target_rect.x()
        offset_y = target_rect.y()
        tw = target_rect.width()
        th = target_rect.height()

        src_w, src_h = self._frame_dims
        box_scale_x = tw / float(src_w if src_w > 0 else 640)
        box_scale_y = th / float(src_h if src_h > 0 else 360)

        # 1. Draw Active Tracked Persons (Bounding Boxes & Centroids)
        for track_id, det in self._tracked_boxes:
            bx1 = offset_x + det.x1 * box_scale_x
            by1 = offset_y + det.y1 * box_scale_y
            bw = (det.x2 - det.x1) * box_scale_x
            bh = (det.y2 - det.y1) * box_scale_y

            # Green box around person
            painter.setPen(QPen(QColor(0, 255, 120), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(bx1, by1, bw, bh, 4, 4)

            # Foot centroid indicator dot
            foot_x = offset_x + det.foot_point.x * box_scale_x
            foot_y = offset_y + det.foot_point.y * box_scale_y
            painter.setBrush(QBrush(QColor(255, 60, 60)))
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawEllipse(QPointF(foot_x, foot_y), 4, 4)

            # Track ID Tag
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            painter.setBrush(QBrush(QColor(0, 255, 120)))
            tag_rect = QRect(int(bx1), int(by1 - 18), 75, 18)
            painter.drawRoundedRect(tag_rect, 3, 3)
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, f"ID #{track_id}")

        # 2. Draw Scaled Virtual Tripwire Line Segment (From 0.0 - 1.0 Normalized Coordinates)
        if self.tripwire:
            p1_x = offset_x + self.tripwire.p1.x * tw
            p1_y = offset_y + self.tripwire.p1.y * th
            p2_x = offset_x + self.tripwire.p2.x * tw
            p2_y = offset_y + self.tripwire.p2.y * th

            p1 = QPointF(p1_x, p1_y)
            p2 = QPointF(p2_x, p2_y)

            # Glowing line effect
            glow_pen = QPen(QColor(255, 220, 0, 80), 8)
            painter.setPen(glow_pen)
            painter.drawLine(p1, p2)

            # Core crisp line
            line_pen = QPen(QColor(255, 220, 0, 240), 3, Qt.PenStyle.DashLine)
            painter.setPen(line_pen)
            painter.drawLine(p1, p2)

            # End-point handle dots (Finite segment boundaries)
            painter.setBrush(QBrush(QColor(255, 220, 0)))
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            painter.drawEllipse(p1, 6, 6)
            painter.drawEllipse(p2, 6, 6)

            # Tripwire Label
            mid_x = (p1.x() + p2.x()) / 2
            mid_y = (p1.y() + p2.y()) / 2
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.setPen(QColor(255, 220, 0))
            painter.drawText(int(mid_x - 65), int(mid_y - 12), 130, 20, Qt.AlignmentFlag.AlignCenter, "GARIS LINTASAN")

        # 3. Draw Large Statistics HUD Cards (Top-Left)
        card_w, card_h = 130, 68
        spacing = 10
        margin_x, margin_y = 16, 16

        def draw_stat_card(x: int, y: int, label: str, value: int, accent_color: QColor):
            painter.setPen(QPen(accent_color, 2))
            painter.setBrush(QBrush(QColor(18, 22, 26, 220)))
            painter.drawRoundedRect(x, y, card_w, card_h, 8, 8)

            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.setPen(QColor(190, 205, 220))
            painter.drawText(QRect(x, y + 8, card_w, 20), Qt.AlignmentFlag.AlignCenter, label)

            painter.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
            painter.setPen(accent_color)
            painter.drawText(QRect(x, y + 26, card_w, 36), Qt.AlignmentFlag.AlignCenter, str(value))

        draw_stat_card(margin_x, margin_y, "🟢 MASUK (IN)", self.counter_state.entered, QColor(0, 225, 120))
        draw_stat_card(margin_x + card_w + spacing, margin_y, "🔴 KELUAR (OUT)", self.counter_state.exited, QColor(255, 75, 85))
        draw_stat_card(margin_x + (card_w + spacing) * 2, margin_y, "🔵 DI DALAM", self.counter_state.current_inside, QColor(0, 175, 255))
