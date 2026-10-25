import pytest
from src.domain.geometry import (
    Point,
    LineSegment,
    Direction,
    segments_intersect,
    determine_crossing_direction
)


def test_segment_intersection():
    # Cross intersection
    seg1 = LineSegment(Point(0, 0), Point(10, 10))
    seg2 = LineSegment(Point(0, 10), Point(10, 0))
    assert segments_intersect(seg1, seg2) is True

    # Parallel segments
    seg3 = LineSegment(Point(0, 0), Point(10, 0))
    seg4 = LineSegment(Point(0, 5), Point(10, 5))
    assert segments_intersect(seg3, seg4) is False

    # Disjoint non-parallel segments
    seg5 = LineSegment(Point(0, 0), Point(5, 5))
    seg6 = LineSegment(Point(6, 6), Point(10, 10))
    assert segments_intersect(seg5, seg6) is False


def test_crossing_direction_in_and_out():
    # Horizontal tripwire across a doorway from x=100 to x=500 at y=300
    doorway = LineSegment(Point(100, 300), Point(500, 300))

    # Person walks through doorway: from (300, 250) to (300, 350) [top to bottom]
    p_prev = Point(300, 250)
    p_curr = Point(300, 350)
    direction = determine_crossing_direction(doorway, p_prev, p_curr)
    assert direction == Direction.IN

    # Person walks out through doorway: from (300, 350) to (300, 250) [bottom to top]
    direction_out = determine_crossing_direction(doorway, p_curr, p_prev)
    assert direction_out == Direction.OUT


def test_finite_segment_bounds_check_review_finding_1():
    """Validates that a person walking OUTSIDE the doorway endpoints does NOT trigger a count.
    
    This directly prevents the false-positive bug found in the technical review.
    """
    # Doorway tripwire is between x=100 and x=500 at y=300
    doorway = LineSegment(Point(100, 300), Point(500, 300))

    # Person walks at x=700 (outside the doorway wall) from y=250 to y=350
    # Under an infinite line test, this would falsely trigger IN!
    # Under our finite segment test, it MUST return NONE.
    p_outside_prev = Point(700, 250)
    p_outside_curr = Point(700, 350)

    direction = determine_crossing_direction(doorway, p_outside_prev, p_outside_curr)
    assert direction == Direction.NONE


def test_person_walking_parallel_does_not_cross():
    doorway = LineSegment(Point(100, 300), Point(500, 300))

    # Person walks along the wall parallel to the tripwire
    p_prev = Point(150, 280)
    p_curr = Point(350, 280)

    direction = determine_crossing_direction(doorway, p_prev, p_curr)
    assert direction == Direction.NONE
