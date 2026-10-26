import pytest
from PySide6.QtCore import Qt
from src.domain.entities import Camera
from src.core.frame_store import SharedFrameStore
from src.core.worker_pool import StreamWorkerPool
from src.presentation.grid_view import GridView
from src.presentation.widgets.video_tile import VideoTile


@pytest.fixture
def sample_cameras():
    return [
        Camera(id=i, name=f"Camera {i}", sub_stream_url=f"mock://cam{i}", main_stream_url=f"mock://cam{i}")
        for i in range(1, 17)
    ]


def test_video_tile_stream_signals(qapp):
    tile = VideoTile(camera_id=1, camera_name="Front Gate")
    received = []
    tile.toggle_stream_requested.connect(lambda cid: received.append(cid))

    tile.toggle_stream_requested.emit(1)
    assert received == [1]

    # Verify tile set_stopped & set_offline behavior
    tile.set_stopped()
    assert tile._is_stopped is True

    # set_offline should not override _is_stopped
    tile.set_offline()
    assert tile._is_stopped is True


def test_toggle_individual_camera_stream(qapp, sample_cameras):
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    # Initial state: 16 cameras active, stopped_cameras empty
    assert len(grid_view.stopped_cameras) == 0
    assert grid_view.tiles[1]._is_stopped is False
    assert grid_view.tiles[2]._is_stopped is False

    # Stop Camera 1 individually
    grid_view.toggle_camera_stream(1)
    assert 1 in grid_view.stopped_cameras
    assert grid_view.tiles[1]._is_stopped is True
    # Camera 2 should remain running
    assert 2 not in grid_view.stopped_cameras
    assert grid_view.tiles[2]._is_stopped is False

    # Resume Camera 1 individually
    grid_view.toggle_camera_stream(1)
    assert 1 not in grid_view.stopped_cameras
    assert grid_view.tiles[1]._is_stopped is False

    grid_view.close()


def test_stopped_cameras_persisted_on_grid_layout_change(qapp, sample_cameras):
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    # Stop Camera 1 and Camera 3
    grid_view.toggle_camera_stream(1)
    grid_view.toggle_camera_stream(3)
    assert grid_view.stopped_cameras == {1, 3}

    # Switch to 25-camera layout
    grid_view.set_grid_mode(25)
    assert grid_view.stopped_cameras == {1, 3}
    assert grid_view.tiles[1]._is_stopped is True
    assert grid_view.tiles[3]._is_stopped is True
    assert grid_view.tiles[2]._is_stopped is False

    grid_view.close()


def test_global_start_resets_stopped_cameras(qapp, sample_cameras):
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    grid_view.toggle_camera_stream(1)
    assert 1 in grid_view.stopped_cameras
    assert grid_view.tiles[1]._is_stopped is True

    # User clicks global [ ▶ Mulai ]
    grid_view.start_streaming()
    assert len(grid_view.stopped_cameras) == 0
    assert grid_view.tiles[1]._is_stopped is False

    grid_view.close()


def test_focus_mode_toggle_stream(qapp, sample_cameras):
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    # Maximize Camera 2
    grid_view.maximize_camera(2)
    assert grid_view.container_stack.currentIndex() == 1
    assert grid_view.focus_tile.camera_id == 2
    assert grid_view.focus_tile._is_stopped is False

    # Stop Camera 2 while focused
    grid_view.toggle_camera_stream(2)
    assert 2 in grid_view.stopped_cameras
    assert grid_view.focus_tile._is_stopped is True

    # Restore grid: tile 2 in grid should also be stopped
    grid_view.restore_grid()
    assert grid_view.container_stack.currentIndex() == 0
    assert grid_view.tiles[2]._is_stopped is True

    grid_view.close()
