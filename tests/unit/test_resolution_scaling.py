import pytest
from src.domain.geometry import Point, LineSegment, Direction, determine_crossing_direction
from src.domain.entities import CounterState
from src.domain.crossing_service import LineCrossingService


def test_normalized_tripwire_scales_to_1080p():
    """Validates that a normalized tripwire scales correctly to Full HD 1080p (Audit Finding 1)."""
    norm_line = LineSegment(Point(0.15, 0.65), Point(0.85, 0.65))

    # Scale to 1080p frame (1920x1080)
    tripwire_1080p = norm_line.scale(1920, 1080)
    assert tripwire_1080p.p1.x == 1920 * 0.15  # 288.0
    assert tripwire_1080p.p1.y == 1080 * 0.65  # 702.0
    assert tripwire_1080p.p2.x == 1920 * 0.85  # 1632.0
    assert tripwire_1080p.p2.y == 1080 * 0.65  # 702.0

    # Person walks through center of 1080p frame: from (960, 650) to (960, 750)
    p_prev = Point(960, 650)
    p_curr = Point(960, 750)

    direction = determine_crossing_direction(tripwire_1080p, p_prev, p_curr)
    assert direction == Direction.IN

    # Person walks outside the door in 1080p (x=1800)
    p_outside_prev = Point(1800, 650)
    p_outside_curr = Point(1800, 750)
    dir_outside = determine_crossing_direction(tripwire_1080p, p_outside_prev, p_outside_curr)
    assert dir_outside == Direction.NONE


def test_normalized_tripwire_scales_to_4k():
    """Validates that a normalized tripwire scales correctly to 4K Ultra HD (3840x2160)."""
    norm_line = LineSegment(Point(0.15, 0.65), Point(0.85, 0.65))
    tripwire_4k = norm_line.scale(3840, 2160)

    # Person walks out through 4K frame: from (1920, 1500) to (1920, 1300)
    p_prev = Point(1920, 1500)
    p_curr = Point(1920, 1300)

    direction = determine_crossing_direction(tripwire_4k, p_prev, p_curr)
    assert direction == Direction.OUT


def test_memory_bounded_tracked_person():
    """Validates that TrackedPerson maintains O(1) memory bound (Audit Finding 4)."""
    from src.domain.entities import TrackedPerson

    person = TrackedPerson(id=1)
    assert person.previous_position is None
    assert person.current_position is None

    # Simulate 1,000 frames of movement
    for f in range(1000):
        person.add_position(Point(f, f + 10), frame_number=f)

    # Coordinates must reflect strictly the last two frames
    assert person.current_position == Point(999, 1009)
    assert person.previous_position == Point(998, 1008)
    # Confirm no list is growing in memory
    assert not hasattr(person, "history")


def test_tracker_search_radius_scaling():
    """Validates that tracker search radius adapts to 1080p and 4K resolutions."""
    import numpy as np
    from unittest.mock import MagicMock
    from src.core.frame_store import SharedFrameStore
    from src.core.ai_tracker import SimpleTracker
    from src.core.analytics_worker import AnalyticsWorker

    frame_store = SharedFrameStore()
    tripwire = LineSegment(Point(0.15, 0.65), Point(0.85, 0.65))
    tracker = SimpleTracker(max_distance=60.0)
    mock_detector = MagicMock()
    mock_detector.detect.return_value = []

    worker = AnalyticsWorker(
        camera_id=1,
        frame_store=frame_store,
        detector=mock_detector,
        crossing_service=LineCrossingService(tripwire=tripwire.scale(640, 360)),
        tracker=tracker,
        normalized_tripwire=tripwire,
        target_fps=30
    )

    # 1080p frame (1920x1080)
    frame_1080p = np.zeros((1080, 1920, 3), dtype=np.uint8)
    frame_store.put_frame(1, frame_1080p, is_online=True)

    worker.start()
    import time
    time.sleep(0.1)

    # Verify tracker max_distance was scaled to 1920px (60.0 * 1920 / 640 = 180.0)
    assert tracker.max_distance == pytest.approx(180.0)

    # 4K frame (3840x2160)
    frame_4k = np.zeros((2160, 3840, 3), dtype=np.uint8)
    frame_store.put_frame(1, frame_4k, is_online=True)
    time.sleep(0.1)

    assert tracker.max_distance == pytest.approx(360.0)

    worker.stop()
    worker.join(timeout=1.0)
