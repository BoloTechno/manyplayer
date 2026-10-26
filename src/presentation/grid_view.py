import logging
from typing import Dict, List, Optional, Set
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QGridLayout, QLabel, QButtonGroup, QStackedWidget,
    QComboBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from src.domain.entities import Camera
from src.core.frame_store import SharedFrameStore
from src.core.worker_pool import StreamWorkerPool
from src.presentation.widgets.video_tile import VideoTile

logger = logging.getLogger(__name__)


class GridView(QWidget):
    """Menu 1: Multi-Grid RTSP Monitor supporting 16 (4x4), 25 (5x5), and 36 (6x6) cameras.
    
    Features:
    - Master UI Timer at 15 FPS pulling visible frames without UI freezing.
    - Seamless full-screen Focus Mode (1x1) via QStackedWidget on double-click.
    - Controls for [ ▶ MULAI / START ] and [ ⏹ BERHENTI / STOP ].
    - Dynamic stream worker throttling to optimize CPU and network bandwidth.
    """

    fullscreen_requested = Signal()  # Emitted to toggle fullscreen on main window

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
        self.current_aspect_ratio_mode: str = "auto"
        self.current_osd_mode: str = "smart"
        self.selected_cam_id: Optional[int] = None
        self.tiles: Dict[int, VideoTile] = {}
        self.maximized_cam_id: Optional[int] = None
        self._is_streaming_active: bool = True
        self.stopped_cameras: Set[int] = set()
        self.custom_order: List[int] = []

        self._setup_ui()
        self._setup_master_timer()
        self.set_grid_mode(16)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Top Control Toolbar (Compact & responsive, fits 800x600+)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        # Status Pill
        self.status_pill = QLabel("● LIVE (15 FPS)")
        self.status_pill.setStyleSheet("color: #34D399; font-size: 11px; font-weight: bold; margin-left: 4px;")
        toolbar.addWidget(self.status_pill)

        toolbar.addStretch()

        # Start / Stop Stream Controls
        self.btn_start = QPushButton("▶ Mulai")
        self.btn_stop = QPushButton("⏹ Stop")

        for btn, is_start in ((self.btn_start, True), (self.btn_stop, False)):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if is_start:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #065F46;
                        color: #34D399;
                        border: 1px solid #10B981;
                        border-radius: 5px;
                        padding: 4px 10px;
                        font-size: 11px;
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
                        border-radius: 5px;
                        padding: 4px 10px;
                        font-size: 11px;
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

        toolbar.addSpacing(8)

        # Restore Grid Button (replaces layout buttons when in Focus mode)
        self.btn_restore = QPushButton("↩ KEMBALI KE GRID")
        self.btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restore.setStyleSheet("""
            QPushButton {
                background-color: #D97706;
                color: #FFFFFF;
                border: 1px solid #F59E0B;
                border-radius: 5px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #B45309;
            }
        """)
        self.btn_restore.setVisible(False)
        self.btn_restore.clicked.connect(self.restore_grid)
        toolbar.addWidget(self.btn_restore)

        self.mode_label = QLabel("Layout:")
        self.mode_label.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold;")
        toolbar.addWidget(self.mode_label)

        # Grid Switcher Button Group (4x4, 5x5, 6x6)
        self.button_group = QButtonGroup(self)
        self.btn_16 = QPushButton("4x4")
        self.btn_16.setToolTip("16 Kamera (4x4)")
        self.btn_25 = QPushButton("5x5")
        self.btn_25.setToolTip("25 Kamera (5x5)")
        self.btn_36 = QPushButton("6x6")
        self.btn_36.setToolTip("36 Kamera (6x6)")

        for btn in (self.btn_16, self.btn_25, self.btn_36):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #CBD5E1;
                    border: 1px solid #334155;
                    border-radius: 5px;
                    padding: 4px 10px;
                    font-size: 11px;
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

        toolbar.addSpacing(8)

        # Aspect Ratio Selector
        self.ratio_label = QLabel("Rasio:")
        self.ratio_label.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold;")
        toolbar.addWidget(self.ratio_label)

        self.combo_aspect = QComboBox(self)
        self.combo_aspect.addItems([
            "📐 Auto",
            "16:9",
            "4:3",
            "Penuh"
        ])
        self.combo_aspect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_aspect.setStyleSheet("""
            QComboBox {
                background-color: #1E293B;
                color: #CBD5E1;
                border: 1px solid #334155;
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QComboBox:hover {
                border: 1px solid #0284C7;
                color: #FFFFFF;
            }
            QComboBox QAbstractItemView {
                background-color: #1E293B;
                color: #CBD5E1;
                selection-background-color: #0284C7;
                selection-color: #FFFFFF;
                border: 1px solid #334155;
            }
        """)
        self.combo_aspect.currentIndexChanged.connect(self._on_aspect_ratio_combo_changed)
        toolbar.addWidget(self.combo_aspect)

        toolbar.addSpacing(6)

        # OSD Camera Name Visibility Selector
        self.osd_label = QLabel("Label:")
        self.osd_label.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold;")
        toolbar.addWidget(self.osd_label)

        self.combo_osd = QComboBox(self)
        self.combo_osd.addItems([
            "👁️ Smart",
            "👁️ Saat Hover",
            "👁️ Sembunyi"
        ])
        self.combo_osd.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_osd.setStyleSheet("""
            QComboBox {
                background-color: #1E293B;
                color: #CBD5E1;
                border: 1px solid #334155;
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QComboBox:hover {
                border: 1px solid #0284C7;
                color: #FFFFFF;
            }
            QComboBox QAbstractItemView {
                background-color: #1E293B;
                color: #CBD5E1;
                selection-background-color: #0284C7;
                selection-color: #FFFFFF;
                border: 1px solid #334155;
            }
        """)
        self.combo_osd.currentIndexChanged.connect(self._on_osd_combo_changed)
        toolbar.addWidget(self.combo_osd)

        toolbar.addSpacing(6)

        # Fullscreen Toggle Button in GridView Toolbar
        self.btn_fullscreen = QPushButton("⛶ Fullscreen")
        self.btn_fullscreen.setToolTip("Mode Layar Penuh (F11 / Esc untuk keluar)")
        self.btn_fullscreen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fullscreen.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #2DD4BF;
                border: 1px solid #0D9488;
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0D9488;
                color: #FFFFFF;
            }
        """)
        self.btn_fullscreen.clicked.connect(self.fullscreen_requested.emit)
        toolbar.addWidget(self.btn_fullscreen)

        main_layout.addLayout(toolbar)

        # Container Stack: Page 0 = Multi-Grid Layout, Page 1 = Full Focused Single Camera
        self.container_stack = QStackedWidget(self)

        # Page 0: Multi-Grid Container
        self.grid_container = QWidget(self)
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(4)
        self.container_stack.addWidget(self.grid_container)

        # Page 1: Single Camera Focused Container (1x1 full view)
        self.focus_container = QWidget(self)
        focus_layout = QVBoxLayout(self.focus_container)
        focus_layout.setContentsMargins(0, 0, 0, 0)
        focus_layout.setSpacing(0)

        self.focus_tile = VideoTile(camera_id=-1, camera_name="", parent=self.focus_container)
        self.focus_tile.set_maximized(True)
        self.focus_tile.double_clicked.connect(lambda cid: self.restore_grid())
        self.focus_tile.toggle_stream_requested.connect(self.toggle_camera_stream)
        focus_layout.addWidget(self.focus_tile)
        self.container_stack.addWidget(self.focus_container)

        main_layout.addWidget(self.container_stack, stretch=1)

    def _setup_master_timer(self) -> None:
        """Single centralized Master Timer at 15 FPS (66ms interval) pulling visible frames."""
        self.master_timer = QTimer(self)
        self.master_timer.setInterval(66)  # ~15 FPS
        self.master_timer.timeout.connect(self._on_master_timer_tick)
        self.master_timer.start()

    def _ensure_custom_order(self, mode: int) -> None:
        """Ensures self.custom_order is populated and contains at least `mode` slots."""
        configured_ids = sorted(self.cameras.keys())
        if not self.custom_order:
            self.custom_order = list(configured_ids)

        # Append any new cameras not yet in custom_order
        for cid in configured_ids:
            if cid not in self.custom_order:
                self.custom_order.append(cid)

        # Ensure custom_order has at least mode slots using unique placeholder negative IDs
        needed = mode - len(self.custom_order)
        if needed > 0:
            existing_negatives = {cid for cid in self.custom_order if cid < 0}
            for i in range(needed):
                neg_id = -1000 - len(self.custom_order)
                while neg_id in existing_negatives:
                    neg_id -= 1
                self.custom_order.append(neg_id)
                existing_negatives.add(neg_id)

    def set_grid_mode(self, mode: int) -> None:
        """Switches grid view to 16 (4x4), 25 (5x5), or 36 (6x6) cameras."""
        self.current_mode = mode
        self.maximized_cam_id = None
        self.container_stack.setCurrentIndex(0)
        self.btn_restore.setVisible(False)
        self.mode_label.setVisible(True)
        self.btn_16.setVisible(True)
        self.btn_25.setVisible(True)
        self.btn_36.setVisible(True)
        grid_dim = int(mode ** 0.5)  # 4, 5, or 6

        # Clear existing tiles from layout
        while self.grid_layout.count() > 0:
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.tiles.clear()

        # Ensure custom slot order has at least `mode` slots
        self._ensure_custom_order(mode)

        # Rebuild grid layout
        for idx in range(mode):
            cam_id = self.custom_order[idx]
            if cam_id > 0 and cam_id in self.cameras:
                cam = self.cameras.get(cam_id)
                cam_name = cam.name if cam else f"Camera {cam_id:02d}"
            else:
                # Placeholder slot when total cameras is less than grid capacity
                cam_name = f"Slot {idx + 1:02d} (Kosong)"

            tile = VideoTile(camera_id=cam_id, camera_name=cam_name)
            tile.set_aspect_ratio_mode(self.current_aspect_ratio_mode)
            tile.set_osd_mode(self.current_osd_mode)
            tile.clicked.connect(self.select_camera)
            tile.double_clicked.connect(self.toggle_maximize_camera)
            tile.toggle_stream_requested.connect(self.toggle_camera_stream)
            tile.swap_requested.connect(self.swap_camera_slots)
            if not self._is_streaming_active or cam_id in self.stopped_cameras:
                tile.set_stopped()

            # Maintain or set active selection
            if self.selected_cam_id is not None:
                tile.set_selected(cam_id == self.selected_cam_id)
            elif idx == 0 and cam_id > 0:
                self.selected_cam_id = cam_id
                tile.set_selected(True)

            self.tiles[cam_id] = tile

            row = idx // grid_dim
            col = idx % grid_dim
            self.grid_layout.addWidget(tile, row, col)

        # Dynamically throttle stream workers only if Grid View & streaming are active
        active_ids = [cid for cid in self.custom_order[:mode] if cid > 0]
        if self._is_streaming_active and self.master_timer.isActive():
            self.worker_pool.set_active_cameras(
                active_camera_ids=[cid for cid in active_ids if cid not in self.stopped_cameras],
                cameras_map=self.cameras,
                is_main_stream=False
            )

    def swap_camera_slots(self, source_id: int, target_id: int) -> None:
        """Swaps two camera tiles in the grid layout without interrupting or restarting RTSP streams."""
        if source_id == target_id:
            return

        if source_id not in self.custom_order or target_id not in self.custom_order:
            return

        idx1 = self.custom_order.index(source_id)
        idx2 = self.custom_order.index(target_id)

        # Swap positions in custom order list
        self.custom_order[idx1], self.custom_order[idx2] = self.custom_order[idx2], self.custom_order[idx1]

        tile1 = self.tiles.get(source_id)
        tile2 = self.tiles.get(target_id)

        if tile1 and tile2:
            grid_dim = int(self.current_mode ** 0.5)
            r1, c1 = idx1 // grid_dim, idx1 % grid_dim
            r2, c2 = idx2 // grid_dim, idx2 % grid_dim

            # Reposition widgets in grid layout without deleting or recreating them
            self.grid_layout.removeWidget(tile1)
            self.grid_layout.removeWidget(tile2)

            self.grid_layout.addWidget(tile2, r1, c1)
            self.grid_layout.addWidget(tile1, r2, c2)

        # Automatically select the moved camera if it is an active camera
        if source_id > 0:
            self.select_camera(source_id)

        # Update dynamic worker throttling for visible cameras
        if self._is_streaming_active and self.master_timer.isActive():
            visible_active_ids = [
                cid for cid in self.custom_order[:self.current_mode]
                if cid > 0 and cid not in self.stopped_cameras
            ]
            self.worker_pool.set_active_cameras(
                active_camera_ids=visible_active_ids,
                cameras_map=self.cameras,
                is_main_stream=False
            )

        logger.info(f"Swapped camera slot: ID {source_id} (slot {idx1}) <-> ID {target_id} (slot {idx2})")

    def select_camera(self, camera_id: int) -> None:
        """Selects a camera tile and updates border highlight across the grid."""
        if camera_id <= 0:
            return
        self.selected_cam_id = camera_id
        for cid, tile in self.tiles.items():
            tile.set_selected(cid == camera_id)

    def toggle_maximize_camera(self, camera_id: int) -> None:
        """Toggles between single-camera maximized focus and the multi-camera grid."""
        if camera_id <= 0:
            return
        self.select_camera(camera_id)
        if self.container_stack.currentIndex() == 1 and self.maximized_cam_id == camera_id:
            self.restore_grid()
        else:
            self.maximize_camera(camera_id)

    def maximize_camera(self, camera_id: int) -> None:
        """Maximizes a single camera tile to fill the entire container seamlessly via QStackedWidget."""
        if camera_id <= 0 or camera_id not in self.cameras:
            return

        self.select_camera(camera_id)

        cam = self.cameras.get(camera_id)
        cam_name = cam.name if cam else f"Camera {camera_id:02d}"

        self.maximized_cam_id = camera_id
        self.focus_tile.camera_id = camera_id
        self.focus_tile.camera_name = cam_name
        self.focus_tile.set_maximized(True)
        self.focus_tile.set_aspect_ratio_mode(self.current_aspect_ratio_mode)
        self.focus_tile.set_osd_mode(self.current_osd_mode)

        # Copy current frame and status immediately from source grid tile
        source_tile = self.tiles.get(camera_id)
        if source_tile and source_tile._qimage is not None and not source_tile._qimage.isNull():
            self.focus_tile._qimage = source_tile._qimage.copy()
            self.focus_tile._is_online = source_tile._is_online
            self.focus_tile._last_rendered_seq = source_tile._last_rendered_seq
        else:
            self.focus_tile._qimage = None
            self.focus_tile._is_online = source_tile._is_online if source_tile else False

        if not self._is_streaming_active or camera_id in self.stopped_cameras:
            self.focus_tile.set_stopped()

        self.focus_tile.update()

        # Switch stack to Focus Container (Page 1)
        self.container_stack.setCurrentIndex(1)
        self.mode_label.setVisible(False)
        self.btn_16.setVisible(False)
        self.btn_25.setVisible(False)
        self.btn_36.setVisible(False)
        self.btn_restore.setVisible(True)

        # Dynamically throttle stream workers to ONLY this camera
        if self._is_streaming_active and self.master_timer.isActive():
            active_ids = [camera_id] if camera_id not in self.stopped_cameras else []
            self.worker_pool.set_active_cameras(
                active_camera_ids=active_ids,
                cameras_map=self.cameras,
                is_main_stream=False
            )
        logger.info(f"Grid maximized cleanly to Camera {camera_id} (1x1 Focus).")

    def restore_grid(self) -> None:
        """Restores the multi-grid view from single-camera maximized mode."""
        if self.container_stack.currentIndex() == 0 and self.maximized_cam_id is None:
            return

        self.maximized_cam_id = None
        self.container_stack.setCurrentIndex(0)
        self.btn_restore.setVisible(False)
        self.mode_label.setVisible(True)
        self.btn_16.setVisible(True)
        self.btn_25.setVisible(True)
        self.btn_36.setVisible(True)

        # Resume stream workers for all visible grid slots
        active_ids = [cid for cid in self.custom_order[:self.current_mode] if cid > 0]

        if self._is_streaming_active and self.master_timer.isActive():
            self.worker_pool.set_active_cameras(
                active_camera_ids=[cid for cid in active_ids if cid not in self.stopped_cameras],
                cameras_map=self.cameras,
                is_main_stream=False
            )
        logger.info(f"Grid restored cleanly to {self.current_mode}-camera mode.")

    def _on_aspect_ratio_combo_changed(self, index: int) -> None:
        """Handles combo box selection change."""
        mode_map = {0: "auto", 1: "16:9", 2: "4:3", 3: "stretch"}
        selected_mode = mode_map.get(index, "auto")
        self.set_aspect_ratio_mode(selected_mode)

    def set_aspect_ratio_mode(self, mode: str) -> None:
        """Applies aspect ratio mode to all grid tiles and focus tile."""
        if mode not in ("auto", "16:9", "4:3", "stretch"):
            return
        self.current_aspect_ratio_mode = mode
        for tile in self.tiles.values():
            tile.set_aspect_ratio_mode(mode)
        self.focus_tile.set_aspect_ratio_mode(mode)
        logger.info(f"Aspect ratio mode set to: {mode}")

    def _on_osd_combo_changed(self, index: int) -> None:
        """Handles OSD mode combo box selection change."""
        mode_map = {0: "smart", 1: "hover", 2: "hidden"}
        selected_mode = mode_map.get(index, "smart")
        self.set_osd_mode(selected_mode)

    def set_osd_mode(self, mode: str) -> None:
        """Applies OSD visibility mode ('smart', 'hover', 'hidden') to all tiles."""
        if mode not in ("smart", "hover", "hidden"):
            return
        self.current_osd_mode = mode
        for tile in self.tiles.values():
            tile.set_osd_mode(mode)
        self.focus_tile.set_osd_mode(mode)
        logger.info(f"OSD mode set to: {mode}")

    def set_fullscreen_state(self, is_fullscreen: bool) -> None:
        """Updates toolbar fullscreen button text and styling."""
        if is_fullscreen:
            self.btn_fullscreen.setText("🗗 Normal (Esc)")
            self.btn_fullscreen.setToolTip("Kembali ke Window Normal (Esc)")
            self.btn_fullscreen.setStyleSheet("""
                QPushButton {
                    background-color: #D97706;
                    color: #FFFFFF;
                    border: 1px solid #F59E0B;
                    border-radius: 5px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #B45309;
                }
            """)
        else:
            self.btn_fullscreen.setText("⛶ Fullscreen")
            self.btn_fullscreen.setToolTip("Mode Layar Penuh (F11)")
            self.btn_fullscreen.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #2DD4BF;
                    border: 1px solid #0D9488;
                    border-radius: 5px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0D9488;
                    color: #FFFFFF;
                }
            """)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Forwards ESC and F11 to parent window if received."""
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_F11):
            parent_win = self.window()
            if parent_win and hasattr(parent_win, "keyPressEvent"):
                parent_win.keyPressEvent(event)
                event.accept()
                return
        super().keyPressEvent(event)

    def start_streaming(self) -> None:
        """Starts RTSP stream ingestion and master UI timer."""
        self._is_streaming_active = True
        self.stopped_cameras.clear()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_pill.setText("● LIVE (15 FPS)")
        self.status_pill.setStyleSheet("color: #34D399; font-size: 11px; font-weight: bold; margin-left: 8px;")

        self.master_timer.start()

        if self.container_stack.currentIndex() == 1 and self.maximized_cam_id is not None:
            active_ids = [self.maximized_cam_id]
        else:
            active_ids = [cid for cid in self.custom_order[:self.current_mode] if cid > 0]

        for tile in self.tiles.values():
            tile._is_stopped = False
        self.focus_tile._is_stopped = False

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
        self.focus_tile.set_stopped()

        logger.info("Grid streaming stopped.")

    def _on_master_timer_tick(self) -> None:
        """Pulls latest frames for visible cameras and updates tiles in batch (skips unchanged frames)."""
        if not self.isVisible() or not self._is_streaming_active:
            return

        if self.container_stack.currentIndex() == 1 and self.maximized_cam_id is not None:
            # Maximized mode: update only the focus tile if not stopped
            if self.maximized_cam_id in self.stopped_cameras:
                return
            cam_data = self.frame_store.get_frame_with_seq(self.maximized_cam_id)
            if cam_data:
                frame, seq, is_online = cam_data
                self.focus_tile.set_frame_if_new(frame, seq=seq, is_online=is_online)
            else:
                self.focus_tile.set_offline()
        else:
            # Grid mode: update all grid tiles (skipping stopped cameras)
            visible_ids = [cid for cid in self.tiles.keys() if cid not in self.stopped_cameras and cid > 0]
            data_map = self.frame_store.get_visible_frames_with_seq(visible_ids)

            for cam_id, tile in self.tiles.items():
                if cam_id in self.stopped_cameras:
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
            if self.container_stack.currentIndex() == 1 and self.maximized_cam_id is not None:
                active_ids = [self.maximized_cam_id] if self.maximized_cam_id not in self.stopped_cameras else []
                self.worker_pool.set_active_cameras(
                    active_camera_ids=active_ids,
                    cameras_map=self.cameras,
                    is_main_stream=False
                )
            else:
                self.set_grid_mode(self.current_mode)

    def update_cameras(self, cameras: List[Camera]) -> None:
        """Dynamically updates camera dictionary and refreshes visible grid layout."""
        self.cameras = {cam.id: cam for cam in cameras}
        valid_cam_ids = set(self.cameras.keys())
        # Preserve custom slot order, keeping existing valid cameras and placeholder IDs
        self.custom_order = [
            cid for cid in self.custom_order
            if cid in valid_cam_ids or cid < 0
        ]
        # Append newly added cameras
        for cid in sorted(valid_cam_ids):
            if cid not in self.custom_order:
                self.custom_order.append(cid)
        self.set_grid_mode(self.current_mode)

    def toggle_camera_stream(self, camera_id: int) -> None:
        """Toggles RTSP stream ingestion independently for a single camera feed."""
        if camera_id <= 0:
            return

        tile = self.tiles.get(camera_id)

        if camera_id in self.stopped_cameras:
            # Resume stream for this camera
            self.stopped_cameras.discard(camera_id)
            cam = self.cameras.get(camera_id)
            if cam and self._is_streaming_active:
                is_focus_view = (self.container_stack.currentIndex() == 1)
                is_this_cam_focused = (self.maximized_cam_id == camera_id)
                if not is_focus_view or is_this_cam_focused:
                    self.worker_pool.start_camera_worker(camera_id, cam, is_main_stream=False)

            if tile:
                tile._is_stopped = False
                tile.update()
            if self.focus_tile.camera_id == camera_id:
                self.focus_tile._is_stopped = False
                self.focus_tile.update()
            logger.info(f"Stream manually resumed for Camera {camera_id}.")
        else:
            # Stop stream for this camera
            self.stopped_cameras.add(camera_id)
            self.worker_pool.stop_camera_worker(camera_id)
            self.frame_store.clear_camera(camera_id)

            if tile:
                tile.set_stopped()
            if self.focus_tile.camera_id == camera_id:
                self.focus_tile.set_stopped()
            logger.info(f"Stream manually stopped for Camera {camera_id}.")
