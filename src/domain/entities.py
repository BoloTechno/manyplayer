from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from src.domain.geometry import Point


@dataclass
class Camera:
    """Entity representing an IP Camera RTSP feed."""
    id: int
    name: str
    sub_stream_url: str
    main_stream_url: str
    is_counter_target: Optional[str] = None  # e.g. "Cam 1", "Cam 2", or None

    def get_stream_url(self, is_main: bool = False) -> str:
        """Returns the appropriate stream URL depending on resolution requirement."""
        return self.main_stream_url if is_main else self.sub_stream_url


@dataclass
class CounterState:
    """Entity holding live real-time person count statistics."""
    entered: int = 0
    exited: int = 0

    @property
    def current_inside(self) -> int:
        """Net count of people currently inside the monitored area."""
        return self.entered - self.exited

    def record_in(self) -> None:
        """Increment count for an entering person."""
        self.entered += 1

    def record_out(self) -> None:
        """Increment count for an exiting person."""
        self.exited += 1

    def reset(self) -> None:
        """Reset all counters to zero."""
        self.entered = 0
        self.exited = 0


@dataclass
class TrackedPerson:
    """Entity representing an individual person tracked across video frames.
    
    Memory-bounded: stores only the previous and current coordinates (O(1) memory),
    preventing memory leaks during 24/7 continuous operation.
    """
    id: int
    prev_pos: Optional[Point] = None
    curr_pos: Optional[Point] = None
    last_seen_frame: int = 0
    has_crossed: bool = False

    def add_position(self, point: Point, frame_number: int) -> None:
        """Updates position tracking, keeping only the last two points."""
        self.prev_pos = self.curr_pos
        self.curr_pos = point
        self.last_seen_frame = frame_number

    @property
    def current_position(self) -> Optional[Point]:
        return self.curr_pos

    @property
    def previous_position(self) -> Optional[Point]:
        return self.prev_pos
