import logging
from typing import List, Optional
from PySide6.QtWidgets import QMainWindow, QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from src.domain.entities import Camera
from src.core.camera_store import CameraStore
from src.core.frame_store import SharedFrameStore
from src.core.worker_pool import StreamWorkerPool
from src.presentation.grid_view import GridView
from src.presentation.dialogs.camera_config_dialog import CameraConfigDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main Application Window for ManyPlayer RTSP Multi-Camera Surveillance."""

    cameras_changed = Signal(list)  # Emitted when cameras configuration is modified live

    def __init__(
        self,
        cameras: List[Camera],
        frame_store: SharedFrameStore,
        worker_pool: StreamWorkerPool,
        camera_store: Optional[CameraStore] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.cameras = cameras
        self.frame_store = frame_store
        self.worker_pool = worker_pool
        self.camera_store = camera_store or CameraStore()

        self.setWindowTitle("ManyPlayer - CCTV Video Wall")
        self.setStyleSheet("background-color: #0F172A; color: #F8FAFC;")

        # Responsive sizing according to primary screen work area
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_w = min(1280, int(avail.width() * 0.95))
            target_h = min(720, int(avail.height() * 0.92))
            self.resize(target_w, target_h)
            pos_x = avail.x() + (avail.width() - target_w) // 2
            pos_y = avail.y() + (avail.height() - target_h) // 2
            self.move(pos_x, pos_y)
        else:
            self.resize(1024, 600)

        self.setMinimumSize(700, 450)

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.grid_view = GridView(self.cameras, self.frame_store, self.worker_pool, parent=self)
        self.grid_view.fullscreen_requested.connect(self.toggle_fullscreen)
        self.grid_view.manage_cameras_requested.connect(self.open_camera_management_dialog)
        self.setCentralWidget(self.grid_view)

    def open_camera_management_dialog(self) -> None:
        """Opens modal dialog for managing RTSP camera streams."""
        dialog = CameraConfigDialog(self.cameras, camera_store=self.camera_store, parent=self)
        dialog.cameras_updated.connect(self.on_cameras_updated)
        dialog.exec()

    def on_cameras_updated(self, new_cameras: List[Camera]) -> None:
        """Handles live update of cameras configuration without restarting the application."""
        self.cameras = new_cameras
        self.grid_view.update_cameras(new_cameras)
        self.cameras_changed.emit(new_cameras)
        logger.info(f"Live camera configuration updated: {len(new_cameras)} cameras registered.")

    def toggle_fullscreen(self) -> None:
        """Toggles between fullscreen and normal/maximized windowed mode."""
        if self.isFullScreen():
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    def enter_fullscreen(self) -> None:
        """Enters fullscreen mode."""
        self.showFullScreen()
        self.grid_view.set_fullscreen_state(True)
        logger.info("Entered Fullscreen mode.")

    def exit_fullscreen(self) -> None:
        """Exits fullscreen mode and restores maximized window."""
        self.showMaximized()
        self.grid_view.set_fullscreen_state(False)
        logger.info("Exited Fullscreen mode.")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Global key event handler for ESC (tiered restore) and F11 (fullscreen toggle)."""
        if event.key() == Qt.Key.Key_Escape:
            # Tier 1: If camera is maximized in GridView, first restore to multi-grid
            if self.grid_view.maximized_cam_id is not None:
                self.grid_view.restore_grid()
                event.accept()
                return

            # Tier 2: If in Fullscreen mode, restore normal window
            if self.isFullScreen():
                self.exit_fullscreen()
                event.accept()
                return

        elif event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
            event.accept()
            return

        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        """Handles graceful application shutdown on Windows."""
        logger.info("Shutting down ManyPlayer application...")
        self.grid_view.pause_rendering()
        self.worker_pool.stop_all()
        event.accept()
