import logging
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSplitter
)
from PySide6.QtCore import Qt, QTimer
from src.domain.geometry import Point, LineSegment
from src.domain.entities import Camera, CounterState
from src.domain.crossing_service import LineCrossingService
from src.core.frame_store import SharedFrameStore
from src.core.worker_pool import StreamWorkerPool
from src.core.ai_detector import PersonDetector
from src.core.ai_tracker import SimpleTracker
from src.core.analytics_worker import AnalyticsWorker
from src.presentation.widgets.video_tile import VideoTile
from src.presentation.widgets.hud_overlay import HUDOverlay

logger = logging.getLogger(__name__)


class SingleCounterCameraWidget(QWidget):
    """Combines VideoTile, HUDOverlay, and background AnalyticsWorker for one camera."""

    def __init__(
        self,
        camera: Camera,
        normalized_tripwire: LineSegment,
        frame_store: SharedFrameStore,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.camera = camera
        self.normalized_tripwire = normalized_tripwire
        self.frame_store = frame_store

        # Each camera gets its own dedicated PersonDetector instance (Resolves Audit Finding 2)
        self.detector = PersonDetector(conf_threshold=0.45)

        self.counter_state = CounterState()
        # Initialize crossing service with scaled default (will be dynamically updated per frame)
        self.crossing_service = LineCrossingService(
            tripwire=self.normalized_tripwire.scale(640, 360),
            counter_state=self.counter_state
        )
        self.tracker = SimpleTracker(max_disappeared_frames=15, max_distance=60.0)

        # Background AI Analytics Worker (Isolates YOLO from GUI thread)
        self.analytics_worker = AnalyticsWorker(
            camera_id=camera.id,
            frame_store=frame_store,
            detector=self.detector,
            crossing_service=self.crossing_service,
            tracker=self.tracker,
            normalized_tripwire=self.normalized_tripwire,
            target_fps=15
        )

        # Base Video Tile (80x45 min size for responsive grid)
        self.video_tile = VideoTile(camera_id=camera.id, camera_name=f"COUNTER: {camera.name}", parent=self)
        # Transparent HUD Overlay on top
        self.hud = HUDOverlay(normalized_tripwire=self.normalized_tripwire, counter_state=self.counter_state, parent=self)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.video_tile.setGeometry(0, 0, self.width(), self.height())
        self.hud.setGeometry(0, 0, self.width(), self.height())

    def start_worker(self) -> None:
        """Starts a fresh analytics worker, ensuring any previous thread is fully stopped (Resolves Audit Finding 5)."""
        if self.analytics_worker.is_alive():
            self.analytics_worker.stop()
            self.analytics_worker.join(timeout=0.5)

        self.detector.load_model()
        self.analytics_worker = AnalyticsWorker(
            camera_id=self.camera.id,
            frame_store=self.frame_store,
            detector=self.detector,
            crossing_service=self.crossing_service,
            tracker=self.tracker,
            normalized_tripwire=self.normalized_tripwire,
            target_fps=15
        )
        self.analytics_worker.start()

    def stop_worker(self) -> None:
        """Stops the worker thread cleanly and joins (Resolves Audit Finding 5)."""
        if self.analytics_worker.is_alive():
            self.analytics_worker.stop()
            self.analytics_worker.join(timeout=0.5)

    def update_ui_tick(self) -> None:
        """Called by UI timer: fast painting without blocking inference."""
        frame, seq, is_online = self.frame_store.get_frame_with_seq(self.camera.id)
        self.video_tile.set_frame_if_new(frame, seq=seq, is_online=is_online)

        # Fetch latest bounding boxes & resolution from background worker
        tracks, frame_dims = self.analytics_worker.get_latest_tracks()
        self.hud.set_tracked_boxes(tracks, frame_dims=frame_dims)
        self.hud.update_stats()

    def reset_counter(self) -> None:
        self.analytics_worker.reset_state()
        self.hud.set_tracked_boxes([])
        self.hud.update_stats()


class CounterView(QWidget):
    """Menu 2: AI People Counter for 1 or 2 cameras with fluid On-Screen Display HUD."""

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

        # Select target counter cameras specifically by label (Resolves Review Finding 2)
        cam1_targets = [c for c in cameras if c.is_counter_target == "Cam 1"]
        cam2_targets = [c for c in cameras if c.is_counter_target == "Cam 2"]
        self.cam1 = cam1_targets[0] if cam1_targets else (cameras[0] if cameras else Camera(1, "Cam 1", "", ""))
        self.cam2 = cam2_targets[0] if cam2_targets else (cameras[1] if len(cameras) > 1 else Camera(2, "Cam 2", "", ""))

        self._setup_ui()
        self._setup_render_timer()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Header Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        title = QLabel("AI PEOPLE COUNTER (ANALITIK)")
        title.setStyleSheet("color: #38BDF8; font-size: 14px; font-weight: bold;")
        toolbar.addWidget(title)

        toolbar.addStretch()

        # View Mode Toggle: [ 1 Kamera ] vs [ 2 Kamera Split ]
        self.btn_single = QPushButton("1 Kamera (Fokus)")
        self.btn_dual = QPushButton("2 Kamera (Split)")
        self.btn_reset = QPushButton("🔄 Reset Angka Counter")

        for btn in (self.btn_single, self.btn_dual):
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

        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                border: 1px solid #EF4444;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
        """)
        self.btn_reset.clicked.connect(self.reset_all_counters)

        self.btn_single.clicked.connect(lambda: self.set_view_mode(1))
        self.btn_dual.clicked.connect(lambda: self.set_view_mode(2))
        self.btn_dual.setChecked(True)

        toolbar.addWidget(self.btn_single)
        toolbar.addWidget(self.btn_dual)
        toolbar.addWidget(self.btn_reset)

        main_layout.addLayout(toolbar)

        # Video Display Container
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #334155; width: 3px; }")

        # Normalized tripwires across lower 65% of screen (Resolves Audit Finding 1)
        tripwire1 = LineSegment(Point(0.15, 0.65), Point(0.85, 0.65))
        self.cam_widget_1 = SingleCounterCameraWidget(
            camera=self.cam1,
            normalized_tripwire=tripwire1,
            frame_store=self.frame_store,
            parent=self
        )
        self.splitter.addWidget(self.cam_widget_1)

        # Camera 2 Widget
        tripwire2 = LineSegment(Point(0.15, 0.65), Point(0.85, 0.65))
        self.cam_widget_2 = SingleCounterCameraWidget(
            camera=self.cam2,
            normalized_tripwire=tripwire2,
            frame_store=self.frame_store,
            parent=self
        )
        self.splitter.addWidget(self.cam_widget_2)

        main_layout.addWidget(self.splitter, stretch=1)

    def _setup_render_timer(self) -> None:
        """Fast UI repaint timer at 15 FPS (66ms) - completely decoupled from AI inference."""
        self.render_timer = QTimer(self)
        self.render_timer.setInterval(66)
        self.render_timer.timeout.connect(self._on_render_timer_tick)

    def set_view_mode(self, mode: int) -> None:
        """Switches between 1-Camera Focused view and 2-Camera Split Screen."""
        if mode == 1:
            self.cam_widget_2.setVisible(False)
            self.cam_widget_2.stop_worker()
            self.btn_single.setChecked(True)
            self.btn_dual.setChecked(False)
            active_ids = [self.cam1.id]
        else:
            self.cam_widget_2.setVisible(True)
            if self.isVisible():
                self.cam_widget_2.start_worker()
            self.btn_single.setChecked(False)
            self.btn_dual.setChecked(True)
            active_ids = [self.cam1.id, self.cam2.id]

        # Ingest Main-stream (high quality) for active counter cameras
        self.worker_pool.set_active_cameras(
            active_camera_ids=active_ids,
            cameras_map=self.cameras,
            is_main_stream=True
        )

    def _on_render_timer_tick(self) -> None:
        """Pulls latest state and repaints UI without running heavy inference."""
        if not self.isVisible():
            return

        self.cam_widget_1.update_ui_tick()
        if self.cam_widget_2.isVisible():
            self.cam_widget_2.update_ui_tick()

    def reset_all_counters(self) -> None:
        """Resets both camera counters to zero."""
        self.cam_widget_1.reset_counter()
        self.cam_widget_2.reset_counter()

    def activate_analytics(self) -> None:
        """Activates AI background workers and UI timer when Tab 2 is opened."""
        logger.info("Activating AI People Counter background workers...")
        self.cam_widget_1.start_worker()
        if self.cam_widget_2.isVisible():
            self.cam_widget_2.start_worker()

        self.render_timer.start()
        mode = 1 if not self.cam_widget_2.isVisible() else 2
        self.set_view_mode(mode)

    def pause_analytics(self) -> None:
        """Stops AI background workers and pauses timer when navigating away from Tab 2."""
        logger.info("Pausing AI People Counter workers to save CPU...")
        self.render_timer.stop()
        self.cam_widget_1.stop_worker()
        self.cam_widget_2.stop_worker()

    def update_cameras(self, cameras: List[Camera]) -> None:
        """Updates counter cameras reference and refreshes widgets."""
        self.cameras = {cam.id: cam for cam in cameras}
        old_cam1_id = self.cam1.id
        old_cam2_id = self.cam2.id

        # Select target counter cameras specifically by label (Resolves Review Finding 2)
        cam1_targets = [c for c in cameras if c.is_counter_target == "Cam 1"]
        cam2_targets = [c for c in cameras if c.is_counter_target == "Cam 2"]
        self.cam1 = cam1_targets[0] if cam1_targets else (cameras[0] if cameras else Camera(1, "Cam 1", "", ""))
        self.cam2 = cam2_targets[0] if cam2_targets else (cameras[1] if len(cameras) > 1 else Camera(2, "Cam 2", "", ""))

        was_running = self.render_timer.isActive()
        if was_running:
            self.cam_widget_1.stop_worker()
            self.cam_widget_2.stop_worker()

        # Update widget 1
        self.cam_widget_1.camera = self.cam1
        self.cam_widget_1.video_tile.camera_id = self.cam1.id
        self.cam_widget_1.video_tile.camera_name = f"COUNTER: {self.cam1.name}"
        self.cam_widget_1.analytics_worker.camera_id = self.cam1.id
        if old_cam1_id != self.cam1.id:
            # Reassigned camera starts with fresh headcount (Resolves Review Finding 5)
            self.cam_widget_1.reset_counter()
        self.cam_widget_1.video_tile.update()

        # Update widget 2
        self.cam_widget_2.camera = self.cam2
        self.cam_widget_2.video_tile.camera_id = self.cam2.id
        self.cam_widget_2.video_tile.camera_name = f"COUNTER: {self.cam2.name}"
        self.cam_widget_2.analytics_worker.camera_id = self.cam2.id
        if old_cam2_id != self.cam2.id:
            # Reassigned camera starts with fresh headcount (Resolves Review Finding 5)
            self.cam_widget_2.reset_counter()
        self.cam_widget_2.video_tile.update()

        if was_running:
            self.cam_widget_1.start_worker()
            if self.cam_widget_2.isVisible():
                self.cam_widget_2.start_worker()
            active_ids = [self.cam1.id] if not self.cam_widget_2.isVisible() else [self.cam1.id, self.cam2.id]
            self.worker_pool.set_active_cameras(active_ids, self.cameras, is_main_stream=True)
