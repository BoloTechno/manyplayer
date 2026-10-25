from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Direction(str, Enum):
    """Direction of movement relative to tripwire line."""
    IN = "IN"
    OUT = "OUT"
    NONE = "NONE"


@dataclass(frozen=True)
class Point:
    """2D Cartesian Coordinate."""
    x: float
    y: float

    def distance_to(self, other: Point) -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


@dataclass(frozen=True)
class LineSegment:
    """A finite line segment defined by two end points."""
    p1: Point
    p2: Point

    @property
    def length(self) -> float:
        return self.p1.distance_to(self.p2)


def ccw(a: Point, b: Point, c: Point) -> float:
    """Computes the 2D cross product of vector AB and AC.
    
    Positive if counter-clockwise, negative if clockwise, zero if collinear.
    """
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def segments_intersect(seg1: LineSegment, seg2: LineSegment) -> bool:
    """Checks whether two finite line segments seg1 and seg2 intersect.
    
    Handles strict interior intersections as well as edge-touching crossings.
    """
    a, b = seg1.p1, seg1.p2
    c, d = seg2.p1, seg2.p2

    ccw_abc = ccw(a, b, c)
    ccw_abd = ccw(a, b, d)
    ccw_cda = ccw(c, d, a)
    ccw_cdb = ccw(c, d, b)

    # General case: segments straddle each other
    if (
        ((ccw_abc > 0 and ccw_abd < 0) or (ccw_abc < 0 and ccw_abd > 0)) and
        ((ccw_cda > 0 and ccw_cdb < 0) or (ccw_cda < 0 and ccw_cdb > 0))
    ):
        return True

    # Special collinear or touching boundary cases
    def on_segment(p: Point, q: Point, r: Point) -> bool:
        """Returns True if point q lies on line segment pr."""
        return (
            min(p.x, r.x) <= q.x <= max(p.x, r.x) and
            min(p.y, r.y) <= q.y <= max(p.y, r.y)
        )

    if ccw_abc == 0 and on_segment(a, c, b):
        return True
    if ccw_abd == 0 and on_segment(a, d, b):
        return True
    if ccw_cda == 0 and on_segment(c, a, d):
        return True
    if ccw_cdb == 0 and on_segment(c, b, d):
        return True

    return False


def determine_crossing_direction(
    tripwire: LineSegment,
    p_prev: Point,
    p_curr: Point
) -> Direction:
    """Determines if the trajectory segment (p_prev -> p_curr) crosses the finite tripwire.
    
    If it intersects the finite segment:
      - Cross product > 0: Direction.IN
      - Cross product < 0: Direction.OUT
    Otherwise:
      - Direction.NONE
    """
    traj = LineSegment(p_prev, p_curr)

    # Must intersect the FINITE segment, not just the infinite line
    if not segments_intersect(tripwire, traj):
        return Direction.NONE

    # Vector of tripwire: P1 -> P2
    line_dx = tripwire.p2.x - tripwire.p1.x
    line_dy = tripwire.p2.y - tripwire.p1.y

    # Vector of movement: p_prev -> p_curr
    move_dx = p_curr.x - p_prev.x
    move_dy = p_curr.y - p_prev.y

    # 2D cross product: line x move
    cross = line_dx * move_dy - line_dy * move_dx

    if cross > 0:
        return Direction.IN
    elif cross < 0:
        return Direction.OUT
    return Direction.NONE
