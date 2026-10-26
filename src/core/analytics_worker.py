import time
import logging
import threading
from typing import List, Tuple, Optional
from src.domain.geometry import LineSegment
from src.domain.crossing_service import LineCrossingService
from src.core.frame_store import SharedFrameStore
from src.core.ai_detector import PersonDetector, Detection
from src.core.ai_tracker import SimpleTracker

logger = logging.getLogger(__name__)


class AnalyticsWorker(threading.Thread):
    """Background worker thread that runs YOLO detection and tracking asynchronously.
    
    Prevents heavy AI forward passes from running on the main Qt GUI thread,
    guaranteeing 60 FPS UI responsiveness on Windows.
    """

    def __init__(
        self,
        camera_id: int,
        frame_store: SharedFrameStore,
        detector: PersonDetector,
        crossing_service: LineCrossingService,
        tracker: SimpleTracker,
        normalized_tripwire: Optional[LineSegment] = None,
        target_fps: int = 15
    ):
        super().__init__(daemon=True, name=f"AnalyticsWorker-{camera_id}")
        self.camera_id = camera_id
        self.frame_store = frame_store
        self.detector = detector
        self.crossing_service = crossing_service
        self.tracker = tracker
        self.normalized_tripwire = normalized_tripwire
        self.target_fps = target_fps
        self.interval = 1.0 / target_fps

        self._running = False
        self._last_seq = -1
        self._frame_count = 0
        self._lock = threading.Lock()
        self._latest_tracks: List[Tuple[int, Detection]] = []
        self._frame_dims: Tuple[int, int] = (640, 360)

    def run(self) -> None:
        self._running = True
        logger.info(f"AnalyticsWorker started for Camera {self.camera_id}")

        # Asynchronously load YOLO model in background thread to prevent UI freezing
        self.detector.load_model()

        while self._running:
            loop_start = time.time()

            frame, seq, is_online = self.frame_store.get_frame_with_seq(self.camera_id)

            if frame is not None and is_online and seq != self._last_seq:
                self._last_seq = seq
                self._frame_count += 1
                frame_h, frame_w = frame.shape[:2]

                # Dynamically scale tripwire to the incoming camera frame resolution (Resolves Audit Finding 1)
                if self.normalized_tripwire:
                    self.crossing_service.tripwire = self.normalized_tripwire.scale(frame_w, frame_h)

                # 1. Run YOLO Object Detection (Isolated in this thread)
                detections = self.detector.detect(frame)

                # 2. Update Multi-Object Tracker
                tracked_pairs = self.tracker.update(detections)

                # 3. Update Line Crossing Domain Service
                for track_id, det in tracked_pairs:
                    self.crossing_service.update_person(
                        person_id=track_id,
                        foot_position=det.foot_point,
                        frame_number=self._frame_count
                    )

                self.crossing_service.cleanup_old_tracks(self._frame_count)

                with self._lock:
                    self._latest_tracks = tracked_pairs
                    self._frame_dims = (frame_w, frame_h)

            # Regulate analytics loop rate
            elapsed = time.time() - loop_start
            if elapsed < self.interval:
                time.sleep(max(0.005, self.interval - elapsed))

        logger.info(f"AnalyticsWorker stopped for Camera {self.camera_id}")

    def stop(self) -> None:
        self._running = False

    def get_latest_tracks(self) -> Tuple[List[Tuple[int, Detection]], Tuple[int, int]]:
        with self._lock:
            return list(self._latest_tracks), self._frame_dims

    def reset_state(self) -> None:
        with self._lock:
            self.crossing_service.reset()
            self.tracker.reset()
            self._latest_tracks.clear()
