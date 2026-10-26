import logging
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QGridLayout, QLabel, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer
from src.domain.entities import Camera
from src.core.frame_store import SharedFrameStore
from src.core.worker_pool import StreamWorkerPool
from src.presentation.widgets.video_tile import VideoTile

logger = logging.getLogger(__name__)


class GridView(QWidget):
    """Menu 1: Multi-Grid RTSP Monitor supporting 16 (4x4), 25 (5x5), and 36 (6x6) cameras.
    
    Features:
    - Master UI Timer at 15 FPS pulling latest frames without UI freezing.
    - Double-click any camera tile to maximize (1x1 Focus) / restore.
    - Controls for [ ▶ MULAI / START ] and [ ⏹ BERHENTI / STOP ].
    - Dynamic stream worker throttling to optimize CPU and network bandwidth.
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
        self.maximized_cam_id: Optional[int] = None
        self._is_streaming_active: bool = True

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
        title_label.setStyleSheet("color: #E2E8F0; font-size: 14px; font-weight: 900;")
        toolbar.addWidget(title_label)

        # Status Pill
        self.status_pill = QLabel("● LIVE (15 FPS)")
        self.status_pill.setStyleSheet("color: #34D399; font-size: 11px; font-weight: bold; margin-left: 8px;")
        toolbar.addWidget(self.status_pill)

        toolbar.addStretch()

        # Start / Stop Stream Controls
        self.btn_start = QPushButton("▶ MULAI")
        self.btn_stop = QPushButton("⏹ BERHENTI")

        for btn, is_start in ((self.btn_start, True), (self.btn_stop, False)):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if is_start:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #065F46;
                        color: #34D399;
                        border: 1px solid #10B981;
                        border-radius: 6px;
                        padding: 6px 14px;
                        font-size: 12px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #047857;
                        color: #FFFFFF;
                    }
                    QPushButton:disabled {
                        background-color: #1E293B;
                        color: #64748B;
                        border: 1px solid #334155;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #7F1D1D;
                        color: #F87171;
                        border: 1px solid #EF4444;
                        border-radius: 6px;
                        padding: 6px 14px;
                        font-size: 12px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #991B1B;
                        color: #FFFFFF;
                    }
                    QPushButton:disabled {
                        background-color: #1E293B;
                        color: #64748B;
                        border: 1px solid #334155;
                    }
                """)

        self.btn_start.setEnabled(False)  # Streaming starts automatically
        self.btn_stop.setEnabled(True)
        self.btn_start.clicked.connect(self.start_streaming)
        self.btn_stop.clicked.connect(self.stop_streaming)

        toolbar.addWidget(self.btn_start)
        toolbar.addWidget(self.btn_stop)

        toolbar.addSpacing(16)

        # Restore Grid Button (only visible when a camera is maximized)
        self.btn_restore = QPushButton("↩ KEMBALI KE GRID")
        self.btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restore.setStyleSheet("""
            QPushButton {
                background-color: #D97706;
                color: #FFFFFF;
                border: 1px solid #F59E0B;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #B45309;
            }
        """)
        self.btn_restore.setVisible(False)
        self.btn_restore.clicked.connect(self.restore_grid)
        toolbar.addWidget(self.btn_restore)

        self.mode_label = QLabel("Pilih Layout:")
        self.mode_label.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: bold;")
        toolbar.addWidget(self.mode_label)

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
        self.maximized_cam_id = None
        self.btn_restore.setVisible(False)
        self.mode_label.setText("Pilih Layout:")
        grid_dim = int(mode ** 0.5)  # 4, 5, or 6

        # Clear existing tiles from layout
        while self.grid_layout.count() > 0:
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.tiles.clear()

        # Select active IDs from sorted configured cameras
        configured_ids = sorted(self.cameras.keys())
        active_ids = configured_ids[:mode]

        # Rebuild grid layout
        for idx in range(mode):
            if idx < len(active_ids):
                cam_id = active_ids[idx]
                cam = self.cameras.get(cam_id)
                cam_name = cam.name if cam else f"Camera {cam_id:02d}"
            else:
                # Placeholder slot when total cameras is less than grid capacity
                cam_id = -1000 - idx
                cam_name = f"Slot {idx + 1:02d} (Kosong)"

            tile = VideoTile(camera_id=cam_id, camera_name=cam_name)
            tile.double_clicked.connect(self.toggle_maximize_camera)
            if not self._is_streaming_active:
                tile.set_stopped()

            self.tiles[cam_id] = tile

            row = idx // grid_dim
            col = idx % grid_dim
            self.grid_layout.addWidget(tile, row, col)

        # Dynamically throttle stream workers only if Grid View & streaming are active
        if self._is_streaming_active and self.master_timer.isActive():
            self.worker_pool.set_active_cameras(
                active_camera_ids=[cid for cid in active_ids if cid > 0],
                cameras_map=self.cameras,
                is_main_stream=False
            )

    def toggle_maximize_camera(self, camera_id: int) -> None:
        """Toggles between single-camera maximized focus and the multi-camera grid."""
        if camera_id <= 0:
            return
        if self.maximized_cam_id == camera_id:
            self.restore_grid()
        else:
            self.maximize_camera(camera_id)

    def maximize_camera(self, camera_id: int) -> None:
        """Maximizes a single camera tile to fill the entire grid container."""
        if camera_id not in self.tiles or camera_id <= 0:
            return

        self.maximized_cam_id = camera_id

        # Remove all widgets from grid layout
        while self.grid_layout.count() > 0:
            self.grid_layout.takeAt(0)

        # Show only maximized tile
        for cid, tile in self.tiles.items():
            if cid == camera_id:
                tile.setVisible(True)
                tile.set_maximized(True)
                self.grid_layout.addWidget(tile, 0, 0, 1, 1)
            else:
                tile.setVisible(False)
                tile.set_maximized(False)

        self.btn_restore.setVisible(True)
        cam = self.cameras.get(camera_id)
        cam_title = cam.name if cam else f"Kamera {camera_id}"
        self.mode_label.setText(f"Mode: 🔍 Fokus ({cam_title})")

        # Throttle workers to ONLY this camera to conserve resources
        if self._is_streaming_active and self.master_timer.isActive():
            self.worker_pool.set_active_cameras(
                active_camera_ids=[camera_id],
                cameras_map=self.cameras,
                is_main_stream=False
            )
        logger.info(f"Grid maximized to Camera {camera_id} (1x1 Focus).")

    def restore_grid(self) -> None:
        """Restores the multi-grid view from single-camera maximized mode."""
        if self.maximized_cam_id is None:
            return

        self.maximized_cam_id = None
        self.btn_restore.setVisible(False)
        self.mode_label.setText("Pilih Layout:")

        # Re-layout existing tiles according to current mode
        while self.grid_layout.count() > 0:
            self.grid_layout.takeAt(0)

        grid_dim = int(self.current_mode ** 0.5)
        configured_ids = sorted(self.cameras.keys())
        active_ids = configured_ids[:self.current_mode]

        for idx, (cid, tile) in enumerate(self.tiles.items()):
            tile.setVisible(True)
            tile.set_maximized(False)
            row = idx // grid_dim
            col = idx % grid_dim
            self.grid_layout.addWidget(tile, row, col)

        if self._is_streaming_active and self.master_timer.isActive():
            self.worker_pool.set_active_cameras(
                active_camera_ids=[cid for cid in active_ids if cid > 0],
                cameras_map=self.cameras,
                is_main_stream=False
            )
        logger.info(f"Grid restored to {self.current_mode}-camera mode.")

    def start_streaming(self) -> None:
        """Starts RTSP stream ingestion and master UI timer."""
        self._is_streaming_active = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_pill.setText("● LIVE (15 FPS)")
        self.status_pill.setStyleSheet("color: #34D399; font-size: 11px; font-weight: bold; margin-left: 8px;")

        self.master_timer.start()

        if self.maximized_cam_id is not None:
            active_ids = [self.maximized_cam_id]
        else:
            configured_ids = sorted(self.cameras.keys())
            active_ids = [cid for cid in configured_ids[:self.current_mode] if cid > 0]

        self.worker_pool.set_active_cameras(
            active_camera_ids=active_ids,
            cameras_map=self.cameras,
            is_main_stream=False
        )
        logger.info("Grid streaming resumed.")

    def stop_streaming(self) -> None:
        """Stops all active RTSP stream workers and pauses UI rendering."""
        self._is_streaming_active = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_pill.setText("⏹ DIHENTIKAN")
        self.status_pill.setStyleSheet("color: #F87171; font-size: 11px; font-weight: bold; margin-left: 8px;")

        self.master_timer.stop()
        self.worker_pool.stop_all()

        for tile in self.tiles.values():
            tile.set_stopped()

        logger.info("Grid streaming stopped.")

    def _on_master_timer_tick(self) -> None:
        """Pulls latest frames for visible cameras and updates tiles in batch (skips unchanged frames)."""
        if not self.isVisible() or not self._is_streaming_active:
            return

        visible_ids = [self.maximized_cam_id] if self.maximized_cam_id else list(self.tiles.keys())
        data_map = self.frame_store.get_visible_frames_with_seq(visible_ids)

        for cam_id in visible_ids:
            tile = self.tiles.get(cam_id)
            if not tile:
                continue
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
        if self._is_streaming_active:
            self.master_timer.start()
            if self.maximized_cam_id is not None:
                self.worker_pool.set_active_cameras(
                    active_camera_ids=[self.maximized_cam_id],
                    cameras_map=self.cameras,
                    is_main_stream=False
                )
            else:
                self.set_grid_mode(self.current_mode)

    def update_cameras(self, cameras: List[Camera]) -> None:
        """Dynamically updates camera dictionary and refreshes visible grid layout."""
        self.cameras = {cam.id: cam for cam in cameras}
        self.set_grid_mode(self.current_mode)
