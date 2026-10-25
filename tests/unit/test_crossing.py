import pytest
from src.domain.geometry import Point, LineSegment, Direction
from src.domain.entities import CounterState
from src.domain.crossing_service import LineCrossingService


def test_line_crossing_service_count():
    doorway = LineSegment(Point(100, 300), Point(500, 300))
    counter = CounterState()
    service = LineCrossingService(tripwire=doorway, counter_state=counter, debounce_frames=5)

    # Person 1 enters: moves from 250, 280 to 250, 320 (crossing y=300 top to bottom)
    dir1 = service.update_person(person_id=1, foot_position=Point(250, 280), frame_number=1)
    assert dir1 == Direction.NONE
    assert counter.entered == 0

    dir2 = service.update_person(person_id=1, foot_position=Point(250, 320), frame_number=2)
    assert dir2 == Direction.IN
    assert counter.entered == 1
    assert counter.exited == 0
    assert counter.current_inside == 1

    # Person 1 lingers inside near the line: moves to (250, 310) at frame 3 (does not cross back)
    dir3 = service.update_person(person_id=1, foot_position=Point(250, 310), frame_number=3)
    assert dir3 == Direction.NONE
    assert counter.entered == 1

    # Person 2 enters in frame 10 (separate person ID)
    service.update_person(person_id=2, foot_position=Point(300, 280), frame_number=10)
    dir4 = service.update_person(person_id=2, foot_position=Point(300, 320), frame_number=11)
    assert dir4 == Direction.IN
    assert counter.entered == 2
    assert counter.current_inside == 2

    # Person 1 moves deeper inside: at frame 15 pos=(250, 350), frame 20 pos=(250, 340)
    service.update_person(person_id=1, foot_position=Point(250, 350), frame_number=15)
    service.update_person(person_id=1, foot_position=Point(250, 340), frame_number=20)

    # Person 1 now exits: moves from (250, 340) to (250, 260) at frame 25 (crossing y=300 bottom to top)
    dir5 = service.update_person(person_id=1, foot_position=Point(250, 260), frame_number=25)
    assert dir5 == Direction.OUT
    assert counter.entered == 2
    assert counter.exited == 1
    assert counter.current_inside == 1

    # Reset test
    service.reset()
    assert counter.entered == 0
    assert counter.exited == 0
    assert counter.current_inside == 0


def test_debounce_blocks_immediate_recount():
    doorway = LineSegment(Point(100, 300), Point(500, 300))
    counter = CounterState()
    service = LineCrossingService(tripwire=doorway, counter_state=counter, debounce_frames=10)

    # Person enters at frame 1 -> frame 2
    service.update_person(person_id=5, foot_position=Point(250, 280), frame_number=1)
    dir_in = service.update_person(person_id=5, foot_position=Point(250, 320), frame_number=2)
    assert dir_in == Direction.IN
    assert counter.entered == 1

    # Immediately steps back across in frame 3 (delta frames = 1 < debounce 10)
    dir_out_blocked = service.update_person(person_id=5, foot_position=Point(250, 280), frame_number=3)
    assert dir_out_blocked == Direction.NONE
    assert counter.exited == 0  # blocked by debounce


def test_track_cleanup():
    doorway = LineSegment(Point(100, 300), Point(500, 300))
    service = LineCrossingService(tripwire=doorway, max_idle_frames=30)

    service.update_person(person_id=99, foot_position=Point(200, 200), frame_number=1)
    assert 99 in service._tracks

    # Cleanup at frame 10 (not yet 30 frames idle)
    service.cleanup_old_tracks(current_frame=10)
    assert 99 in service._tracks

    # Cleanup at frame 40 (39 frames idle > max_idle_frames 30)
    service.cleanup_old_tracks(current_frame=40)
    assert 99 not in service._tracks
