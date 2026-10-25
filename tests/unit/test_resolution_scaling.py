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
