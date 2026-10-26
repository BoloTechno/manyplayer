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
        self.aspect_ratio_mode: str = "auto"  # "auto" (default, preserves frame ratio), "16:9", "4:3", "stretch"
        self.setMinimumSize(80, 45)  # Responsive minimum size allowing 36-camera grid
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_aspect_ratio_mode(self, mode: str) -> None:
        """Sets aspect ratio preservation mode: 'auto', '16:9', '4:3', or 'stretch'."""
        if mode in ("auto", "16:9", "4:3", "stretch") and self.aspect_ratio_mode != mode:
            self.aspect_ratio_mode = mode
            self.update()

    def get_native_aspect_ratio(self) -> float:
        """Returns native aspect ratio of current frame, defaulting to 16/9 if no frame is present."""
        if self._qimage is not None and not self._qimage.isNull() and self._qimage.width() > 0 and self._qimage.height() > 0:
            return self._qimage.width() / float(self._qimage.height())
        return 16.0 / 9.0

    def get_aspect_ratio_string(self) -> str:
        """Returns a human-readable aspect ratio label (e.g. '16:9', '4:3', '16:10', '1:1')."""
        if self.aspect_ratio_mode == "stretch":
            return "Stretch"
        if self.aspect_ratio_mode in ("16:9", "4:3"):
            return self.aspect_ratio_mode

        ratio = self.get_native_aspect_ratio()
        if abs(ratio - 16.0 / 9.0) < 0.05:
            return "16:9"
        elif abs(ratio - 4.0 / 3.0) < 0.05:
            return "4:3"
        elif abs(ratio - 16.0 / 10.0) < 0.05:
            return "16:10"
        elif abs(ratio - 1.0) < 0.05:
            return "1:1"
        return f"{ratio:.2f}:1"

    def mouseDoubleClickEvent(self, event) -> None:
        """Emits double_clicked signal when left mouse button is double clicked on valid camera."""
        if event.button() == Qt.MouseButton.LeftButton and self.camera_id > 0:
            self.double_clicked.emit(self.camera_id)
            event.accept()
            return
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
        """Calculates the target rectangle preserving aspect ratio (16:9, 4:3, or native)
        centered within the tile with letterboxing/pillarboxing (no stretching/distortion).
        """
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return QRect(0, 0, 0, 0)

        if self.aspect_ratio_mode == "stretch":
            return QRect(0, 0, w, h)

        if self.aspect_ratio_mode == "16:9":
            aspect = 16.0 / 9.0
        elif self.aspect_ratio_mode == "4:3":
            aspect = 4.0 / 3.0
        else:
            # "auto": automatically adjust to the native frame proportions
            aspect = self.get_native_aspect_ratio()

        target_w = w
        target_h = int(round(w / aspect))
        if target_h > h:
            target_h = h
            target_w = int(round(h * aspect))

        x_offset = (w - target_w) // 2
        y_offset = (h - target_h) // 2
        return QRect(x_offset, y_offset, target_w, target_h)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()

        # Background Fill (Dark Charcoal)
        painter.fillRect(0, 0, w, h, QColor(22, 26, 30))

        if self._qimage is not None and not self._qimage.isNull():
            target_rect = self.get_target_video_rect()
            painter.drawImage(target_rect, self._qimage)

            # Resolution & Aspect Ratio badge (bottom right)
            if target_rect.width() >= 105 and target_rect.height() >= 55:
                ratio_str = self.get_aspect_ratio_string()
                res_text = f"{self._qimage.width()}x{self._qimage.height()} ({ratio_str})"
                res_font = QFont("Segoe UI", 7, QFont.Weight.Bold)
                painter.setFont(res_font)
                fm = painter.fontMetrics()
                badge_w = fm.horizontalAdvance(res_text) + 12
                badge_h = 16
                badge_x = target_rect.right() - badge_w - 4
                badge_y = target_rect.bottom() - badge_h - 4
                if badge_x > 0 and badge_y > 0:
                    painter.fillRect(badge_x, badge_y, badge_w, badge_h, QColor(10, 14, 18, 190))
                    painter.setPen(QColor(148, 163, 184))
                    painter.drawText(QRect(badge_x, badge_y, badge_w, badge_h), Qt.AlignmentFlag.AlignCenter, res_text)
        else:
            # Placeholder display when offline or connecting or stopped
            painter.setPen(QPen(QColor(60, 70, 80), 1))
            painter.drawRect(1, 1, w - 2, h - 2)

            font = QFont("Segoe UI", 10 if self._is_maximized else 9)
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
            painter.drawText(QRect(0, h // 2 - 14, w, 28), Qt.AlignmentFlag.AlignCenter, status_text)

        # Header Badge Overlay (Semi-transparent dark bar)
        header_height = 28 if self._is_maximized else 24
        painter.fillRect(0, 0, w, header_height, QColor(10, 14, 18, 195))

        # Online Status Indicator Circle (Green dot if online, Yellow if connecting, Gray if stopped)
        if self._is_stopped or self.camera_id <= 0:
            status_color = QColor(100, 116, 139)  # Slate Gray
        elif self._is_online:
            status_color = QColor(0, 220, 120)    # Emerald Green
        else:
            status_color = QColor(240, 180, 20)   # Amber Yellow

        painter.setBrush(status_color)
        painter.setPen(Qt.PenStyle.NoPen)
        circle_y = 9 if self._is_maximized else 7
        painter.drawEllipse(10, circle_y, 10, 10)

        # Camera Name Label
        painter.setPen(QColor(240, 245, 250))
        label_font = QFont("Segoe UI", 9 if self._is_maximized else 8, QFont.Weight.Bold)
        painter.setFont(label_font)
        display_name = self.camera_name
        if self._is_maximized:
            display_name = f"🔍 {self.camera_name}   [MODE FOKUS - Klik ganda atau klik tombol kembali]"
        painter.drawText(QRect(28, 2, w - 35, header_height - 4), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, display_name)
