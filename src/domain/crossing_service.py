from __future__ import annotations
from typing import Dict, Optional, Tuple
from src.domain.geometry import Point, LineSegment, Direction, determine_crossing_direction
from src.domain.entities import CounterState, TrackedPerson


class LineCrossingService:
    """Domain service managing tripwire line crossing evaluation, state memory, and debounce."""

    def __init__(
        self,
        tripwire: LineSegment,
        counter_state: Optional[CounterState] = None,
        max_idle_frames: int = 45,
        debounce_frames: int = 15
    ):
        self.tripwire = tripwire
        self.counter_state = counter_state or CounterState()
        self.max_idle_frames = max_idle_frames
        self.debounce_frames = debounce_frames
        self._tracks: Dict[int, TrackedPerson] = {}
        self._last_crossed_frame: Dict[int, int] = {}

    def update_person(
        self,
        person_id: int,
        foot_position: Point,
        frame_number: int
    ) -> Direction:
        """Updates a person's trajectory and evaluates if they crossed the tripwire.
        
        Returns:
            Direction.IN if crossed entering,
            Direction.OUT if crossed exiting,
            Direction.NONE if no crossing occurred or blocked by debounce.
        """
        if person_id not in self._tracks:
            person = TrackedPerson(id=person_id)
            self._tracks[person_id] = person
        else:
            person = self._tracks[person_id]

        person.add_position(foot_position, frame_number)

        # Need at least 2 points to check crossing
        if person.previous_position is None or person.current_position is None:
            return Direction.NONE

        # Debounce: check if this ID recently triggered a count
        last_crossed = self._last_crossed_frame.get(person_id)
        if last_crossed is not None and (frame_number - last_crossed) < self.debounce_frames:
            return Direction.NONE

        # Evaluate intersection against the finite line segment
        direction = determine_crossing_direction(
            self.tripwire,
            person.previous_position,
            person.current_position
        )

        if direction != Direction.NONE:
            # Prevent consecutive counts in the same direction for the same track (anti-lingering)
            if person.last_crossed_direction == direction:
                return Direction.NONE

            if direction == Direction.IN:
                self.counter_state.record_in()
            elif direction == Direction.OUT:
                self.counter_state.record_out()

            self._last_crossed_frame[person_id] = frame_number
            person.has_crossed = True
            person.last_crossed_direction = direction
            return direction

        return Direction.NONE

    def cleanup_old_tracks(self, current_frame: int) -> None:
        """Removes tracked people that haven't been detected for max_idle_frames."""
        stale_ids = [
            pid for pid, track in self._tracks.items()
            if (current_frame - track.last_seen_frame) > self.max_idle_frames
        ]
        for pid in stale_ids:
            del self._tracks[pid]
            if pid in self._last_crossed_frame:
                del self._last_crossed_frame[pid]

    def reset(self) -> None:
        """Resets the counter state and clears active tracks."""
        self.counter_state.reset()
        self._tracks.clear()
        self._last_crossed_frame.clear()
