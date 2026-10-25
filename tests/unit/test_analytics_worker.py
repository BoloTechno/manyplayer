import time
import numpy as np
from unittest.mock import MagicMock
from src.domain.geometry import Point, LineSegment
from src.domain.entities import CounterState
from src.domain.crossing_service import LineCrossingService
from src.core.frame_store import SharedFrameStore
from src.core.ai_detector import Detection
from src.core.ai_tracker import SimpleTracker
from src.core.analytics_worker import AnalyticsWorker


def test_analytics_worker_execution_loop():
    frame_store = SharedFrameStore()
    tripwire = LineSegment(Point(0.1, 0.5), Point(0.9, 0.5))
    counter_state = CounterState()
    crossing_service = LineCrossingService(tripwire=tripwire.scale(640, 360), counter_state=counter_state)
    tracker = SimpleTracker()

    mock_detector = MagicMock()
    # Mock detection of a person at x1=200, y1=100, x2=250, y2=200
    mock_detector.detect.return_value = [
        Detection(x1=200.0, y1=100.0, x2=250.0, y2=200.0, confidence=0.85, class_id=0)
    ]

    worker = AnalyticsWorker(
        camera_id=1,
        frame_store=frame_store,
        detector=mock_detector,
        crossing_service=crossing_service,
        tracker=tracker,
        normalized_tripwire=tripwire,
        target_fps=30
    )

    # Put a dummy frame into shared storage
    dummy_frame = np.zeros((360, 640, 3), dtype=np.uint8)
    frame_store.put_frame(1, dummy_frame, is_online=True)

    worker.start()
    time.sleep(0.1)  # Allow worker to run one cycle

    # Check that detector and tracker were invoked
    tracks, dims = worker.get_latest_tracks()
    assert len(tracks) == 1
    assert tracks[0][0] == 1  # Track ID 1
    assert dims == (640, 360)

    # Test reset state
    worker.reset_state()
    tracks_after_reset, _ = worker.get_latest_tracks()
    assert len(tracks_after_reset) == 0

    worker.stop()
    worker.join(timeout=1.0)
    assert not worker.is_alive()
