import pytest
from src.domain.geometry import Point
from src.core.ai_detector import Detection
from src.core.ai_tracker import SimpleTracker


def test_tracker_assigns_persistent_ids():
    tracker = SimpleTracker(max_disappeared_frames=5, max_distance=50.0)

    # Frame 1: Person A at (100, 200)
    det1 = Detection(x1=80, y1=100, x2=120, y2=200, confidence=0.9, class_id=0)
    tracks_f1 = tracker.update([det1])
    assert len(tracks_f1) == 1
    id1, _ = tracks_f1[0]
    assert id1 == 1

    # Frame 2: Person A moves slightly to (105, 205)
    det2 = Detection(x1=85, y1=105, x2=125, y2=205, confidence=0.88, class_id=0)
    tracks_f2 = tracker.update([det2])
    assert len(tracks_f2) == 1
    id2, _ = tracks_f2[0]
    assert id2 == 1  # Retains ID 1

    # Frame 3: New Person B enters at (300, 200)
    det3 = Detection(x1=280, y1=100, x2=320, y2=200, confidence=0.92, class_id=0)
    tracks_f3 = tracker.update([det2, det3])
    assert len(tracks_f3) == 2
    assert tracks_f3[0][0] == 1  # Person A is still 1
    assert tracks_f3[1][0] == 2  # Person B gets ID 2


def test_tracker_deregisters_lost_objects():
    tracker = SimpleTracker(max_disappeared_frames=2, max_distance=50.0)
    det1 = Detection(x1=80, y1=100, x2=120, y2=200, confidence=0.9, class_id=0)
    tracker.update([det1])
    assert 1 in tracker.objects

    # Disappear for 1 frame
    tracker.update([])
    assert 1 in tracker.objects

    # Disappear for 2 frames
    tracker.update([])
    assert 1 in tracker.objects

    # Disappear for 3 frames (> max_disappeared 2) -> deregistered
    tracker.update([])
    assert 1 not in tracker.objects
