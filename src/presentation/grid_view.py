import logging
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QGridLayout, QLabel, QButtonGroup, QFrame
)
from PySide6.QtCore import Qt, QTimer
from src.domain.entities import Camera
from src.core.frame_store import SharedFrameStore
from src.core.worker_pool import StreamWorkerPool
from src.presentation.widgets.video_tile import VideoTile

logger = logging.getLogger(__name__)


class GridView(QWidget):
    """Menu 1: Multi-Grid RTSP Monitor supporting 16 (4x4), 25 (5x5), and 36 (6x6) cameras.
    
    Uses a Pull-based Master UI Timer (15 FPS) to eliminate UI freezes.
    """

    def __init__(
        self,
        cameras: List[Camera],
        frame_store: SharedFrameStore,
        worker_pool: StreamWorkerPool,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.cameras = {cam.id: cam for cam in cameras}
        self.frame_store = frame_store
        self.worker_pool = worker_pool
        self.current_mode = 16  # Default: 16 (4x4)
        self.tiles: Dict[int, VideoTile] = {}

        self._setup_ui()
        self._setup_master_timer()
        self.set_grid_mode(16)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Top Control Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        title_label = QLabel("TAMPILAN MULTI-GRID MONITOR")
        title_label.setStyleSheet("color: #E2E8F0; font-size: 14px; font-weight: bold;")
        toolbar.addWidget(title_label)

        toolbar.addStretch()

        mode_label = QLabel("Pilih Layout:")
        mode_label.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: bold;")
        toolbar.addWidget(mode_label)

        # Grid Switcher Button Group
        self.button_group = QButtonGroup(self)
        self.btn_16 = QPushButton("4x4 (16 Kamera)")
        self.btn_25 = QPushButton("5x5 (25 Kamera)")
        self.btn_36 = QPushButton("6x6 (36 Kamera)")

        for btn in (self.btn_16, self.btn_25, self.btn_36):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #CBD5E1;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #334155;
                    color: #FFFFFF;
                }
                QPushButton:checked {
                    background-color: #0284C7;
                    color: #FFFFFF;
                    border: 1px solid #38BDF8;
                }
            """)
            self.button_group.addButton(btn)
            toolbar.addWidget(btn)

        self.btn_16.setChecked(True)
        self.btn_16.clicked.connect(lambda: self.set_grid_mode(16))
        self.btn_25.clicked.connect(lambda: self.set_grid_mode(25))
        self.btn_36.clicked.connect(lambda: self.set_grid_mode(36))

        main_layout.addLayout(toolbar)

        # Video Grid Container
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(4)
        main_layout.addWidget(self.grid_container, stretch=1)

    def _setup_master_timer(self) -> None:
        """Single centralized Master Timer at 15 FPS (66ms interval) pulling visible frames."""
        self.master_timer = QTimer(self)
        self.master_timer.setInterval(66)  # ~15 FPS
        self.master_timer.timeout.connect(self._on_master_timer_tick)
        self.master_timer.start()

    def set_grid_mode(self, mode: int) -> None:
        """Switches grid view to 16 (4x4), 25 (5x5), or 36 (6x6) cameras."""
        self.current_mode = mode
        grid_dim = int(mode ** 0.5)  # 4, 5, or 6

        # Clear existing tiles from layout
        while self.grid_layout.count() > 0:
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        self.tiles.clear()
        active_ids = list(range(1, mode + 1))

        # Rebuild grid layout
        for idx, cam_id in enumerate(active_ids):
            cam = self.cameras.get(cam_id)
            cam_name = cam.name if cam else f"Camera {cam_id:02d}"
            tile = VideoTile(camera_id=cam_id, camera_name=cam_name)
            self.tiles[cam_id] = tile

            row = idx // grid_dim
            col = idx % grid_dim
            self.grid_layout.addWidget(tile, row, col)

        # Dynamically throttle stream workers: only visible cameras are active!
        self.worker_pool.set_active_cameras(
            active_camera_ids=active_ids,
            cameras_map=self.cameras,
            is_main_stream=False
        )

    def _on_master_timer_tick(self) -> None:
        """Pulls latest frames for visible cameras and updates tiles in batch (skips unchanged frames)."""
        if not self.isVisible():
            return

        visible_ids = list(self.tiles.keys())
        data_map = self.frame_store.get_visible_frames_with_seq(visible_ids)

        for cam_id, tile in self.tiles.items():
            cam_data = data_map.get(cam_id)
            if cam_data:
                frame, seq, is_online = cam_data
                tile.set_frame_if_new(frame, seq=seq, is_online=is_online)
            else:
                tile.set_offline()

    def pause_rendering(self) -> None:
        """Pauses master timer when navigating away from Menu 1."""
        self.master_timer.stop()

    def resume_rendering(self) -> None:
        """Resumes master timer when returning to Menu 1."""
        self.master_timer.start()
        # Re-activate stream workers for current mode
        self.set_grid_mode(self.current_mode)
