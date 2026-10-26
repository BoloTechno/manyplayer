from typing import Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect, Signal
from PySide6.QtGui import QPainter, QColor, QFont, QImage, QPen


class VideoTile(QWidget):
    """Custom widget rendering a single camera feed with 16:9 aspect ratio and status overlays.
    
    Supports:
    - Double click event to trigger maximize/restore.
    - Start/Stop status indication.
    - Video resolution badge.
    - Seamless 16:9 aspect ratio scaling.
    """

    double_clicked = Signal(int)  # Emitted with camera_id on mouse double-click

    def __init__(self, camera_id: int, camera_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.camera_name = camera_name
        self._qimage: Optional[QImage] = None
        self._is_online = False
        self._is_stopped = False
        self._is_maximized = False
        self._last_rendered_seq = -1
        self.setMinimumSize(80, 45)  # 16:9 ratio allowing 36-camera grid on standard screens
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseDoubleClickEvent(self, event) -> None:
        """Emits double_clicked signal when left mouse button is double clicked on valid camera."""
        if event.button() == Qt.MouseButton.LeftButton and self.camera_id > 0:
            self.double_clicked.emit(self.camera_id)
        super().mouseDoubleClickEvent(event)

    def set_maximized(self, is_maximized: bool) -> None:
        """Toggles maximized status for header text overlay."""
        self._is_maximized = is_maximized
        self.update()

    def set_stopped(self) -> None:
        """Sets the tile into STOPPED state."""
        self._is_stopped = True
        self._is_online = False
        self._qimage = None
        self._last_rendered_seq = -1
        self.update()

    def set_frame_if_new(self, frame_bgr, seq: int, is_online: bool = True) -> bool:
        """Sets the frame only if the sequence number has incremented.
        
        Returns True if a new frame was processed, or False if skipped.
        """
        self._is_stopped = False

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

            # Resolution badge (bottom right)
            if target_rect.width() >= 120 and target_rect.height() >= 70:
                res_text = f"{self._qimage.width()}x{self._qimage.height()}"
                res_font = QFont("Segoe UI", 7, QFont.Weight.Bold)
                painter.setFont(res_font)
                res_w = 64
                res_h = 16
                res_x = target_rect.right() - res_w - 4
                res_y = target_rect.bottom() - res_h - 4
                if res_x > 0 and res_y > 0:
                    painter.fillRect(res_x, res_y, res_w, res_h, QColor(10, 14, 18, 180))
                    painter.setPen(QColor(148, 163, 184))
                    painter.drawText(QRect(res_x, res_y, res_w, res_h), Qt.AlignmentFlag.AlignCenter, res_text)
        else:
            # Placeholder display when offline or connecting or stopped
            painter.setPen(QPen(QColor(60, 70, 80), 1))
            painter.drawRect(1, 1, w - 2, h - 2)

            font = QFont("Segoe UI", 9)
            painter.setFont(font)
            painter.setPen(QColor(160, 175, 190))
            if self._is_stopped:
                status_text = "⏹ Dihentikan (STOP)"
            elif self.camera_id <= 0:
                status_text = "Slot Kosong"
            elif not self._is_online:
                status_text = "Menghubungkan..."
            else:
                status_text = "Tidak Ada Sinyal"
            painter.drawText(QRect(0, h // 2 - 12, w, 24), Qt.AlignmentFlag.AlignCenter, status_text)

        # Header Badge Overlay (Semi-transparent dark bar)
        painter.fillRect(0, 0, w, 24, QColor(10, 14, 18, 190))

        # Online Status Indicator Circle (Green dot if online, Yellow if connecting, Gray if stopped)
        if self._is_stopped or self.camera_id <= 0:
            status_color = QColor(100, 116, 139)  # Slate Gray
        elif self._is_online:
            status_color = QColor(0, 220, 120)    # Emerald Green
        else:
            status_color = QColor(240, 180, 20)   # Amber Yellow

        painter.setBrush(status_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(8, 7, 10, 10)

        # Camera Name Label
        painter.setPen(QColor(240, 245, 250))
        label_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(label_font)
        display_name = self.camera_name
        if self._is_maximized:
            display_name = f"🔍 {self.camera_name} [MODE FOKUS - Klik ganda untuk kembali]"
        painter.drawText(QRect(24, 4, w - 30, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, display_name)
