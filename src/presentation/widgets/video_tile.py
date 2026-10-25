from typing import Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QFont, QImage, QPen


class VideoTile(QWidget):
    """Custom widget rendering a single camera feed with 16:9 aspect ratio and status overlays."""

    def __init__(self, camera_id: int, camera_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.camera_name = camera_name
        self._qimage: Optional[QImage] = None
        self._is_online = False
        self._last_rendered_seq = -1
        self.setMinimumSize(80, 45)  # 16:9 ratio allowing 36-camera grid on standard laptop screens

    def set_frame_if_new(self, frame_bgr, seq: int, is_online: bool = True) -> bool:
        """Sets the frame only if the sequence number has incremented.
        
        Returns True if a new frame was processed, or False if skipped.
        """
        # If offline status changed, always update
        if not is_online:
            if self._is_online or self._qimage is not None:
                self._is_online = False
                self._qimage = None
                self._last_rendered_seq = seq
                self.update()
                return True
            return False

        # If sequence has not changed, skip conversion entirely (Zero CPU waste)
        if seq == self._last_rendered_seq and self._qimage is not None:
            return False

        self._last_rendered_seq = seq
        self._is_online = True

        if frame_bgr is not None:
            h, w, ch = frame_bgr.shape
            bytes_per_line = ch * w
            self._qimage = QImage(
                frame_bgr.data,
                w,
                h,
                bytes_per_line,
                QImage.Format.Format_BGR888
            ).copy()
        else:
            self._qimage = None

        self.update()
        return True

    def set_frame(self, frame_bgr, is_online: bool = True) -> None:
        """Direct set method for backward compatibility."""
        self.set_frame_if_new(frame_bgr, seq=self._last_rendered_seq + 1, is_online=is_online)

    def set_offline(self) -> None:
        self.set_frame_if_new(None, seq=-1, is_online=False)

    def get_target_video_rect(self) -> QRect:
        """Calculates the exact 16:9 aspect ratio target rectangle within this widget."""
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

        w = self.width()
        h = self.height()

        # Background Fill (Dark Charcoal)
        painter.fillRect(0, 0, w, h, QColor(22, 26, 30))

        if self._qimage is not None and not self._qimage.isNull():
            target_rect = self.get_target_video_rect()
            painter.drawImage(target_rect, self._qimage)
        else:
            # Placeholder display when offline or connecting
            painter.setPen(QPen(QColor(60, 70, 80), 1))
            painter.drawRect(1, 1, w - 2, h - 2)

            font = QFont("Segoe UI", 9)
            painter.setFont(font)
            painter.setPen(QColor(160, 175, 190))
            status_text = "Menghubungkan..." if not self._is_online else "Tidak Ada Sinyal"
            painter.drawText(QRect(0, h // 2 - 12, w, 24), Qt.AlignmentFlag.AlignCenter, status_text)

        # Header Badge Overlay (Semi-transparent dark bar)
        painter.fillRect(0, 0, w, 24, QColor(10, 14, 18, 190))

        # Online Status Indicator Circle (Green dot if online, Yellow if connecting)
        status_color = QColor(0, 220, 120) if self._is_online else QColor(240, 180, 20)
        painter.setBrush(status_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(8, 7, 10, 10)

        # Camera Name Label
        painter.setPen(QColor(240, 245, 250))
        label_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(label_font)
        painter.drawText(QRect(24, 4, w - 30, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.camera_name)
