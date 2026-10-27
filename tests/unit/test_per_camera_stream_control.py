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
        Camera(id=i, name=f"Camera {i}", stream_url=f"mock://cam{i}")
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

    # Stop Camera 2 while focused: must remain in Focus Mode (currentIndex == 1)
    grid_view.toggle_camera_stream(2)
    assert grid_view.container_stack.currentIndex() == 1
    assert grid_view.maximized_cam_id == 2
    assert 2 in grid_view.stopped_cameras
    assert grid_view.focus_tile._is_stopped is True

    # Restore grid: tile 2 in grid should also be stopped
    grid_view.restore_grid()
    assert grid_view.container_stack.currentIndex() == 0
    assert grid_view.tiles[2]._is_stopped is True

    grid_view.close()


def test_global_stop_then_per_camera_resume(qapp, sample_cameras):
    """Verifies that after global stop, right-clicking 'Mulai Siaran' on a single camera resumes it properly."""
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    # Initial state: streaming is active
    assert grid_view._is_streaming_active is True
    assert grid_view.master_timer.isActive() is True
    assert grid_view.btn_stop.isEnabled() is True
    assert grid_view.btn_start.isEnabled() is False

    # 1. User stops streaming globally
    grid_view.stop_streaming()
    assert grid_view._is_streaming_active is False
    assert grid_view.master_timer.isActive() is False
    assert len(grid_view.stopped_cameras) == 16
    assert all(grid_view.tiles[cid]._is_stopped for cid in range(1, 17))
    assert grid_view.btn_start.isEnabled() is True
    assert grid_view.btn_stop.isEnabled() is False
    assert "DIHENTIKAN" in grid_view.status_pill.text()

    # 2. User right-clicks Camera 1 and clicks 'Mulai Siaran Kamera Ini'
    grid_view.toggle_camera_stream(1)

    # Verification: Camera 1 is resumed, master timer started, global streaming re-activated
    assert grid_view._is_streaming_active is True
    assert grid_view.master_timer.isActive() is True
    assert 1 not in grid_view.stopped_cameras
    assert grid_view.tiles[1]._is_stopped is False
    assert "LIVE" in grid_view.status_pill.text()

    # All other 15 cameras must remain stopped
    for cid in range(2, 17):
        assert cid in grid_view.stopped_cameras
        assert grid_view.tiles[cid]._is_stopped is True

    # Toolbar state: both [▶ Mulai] (to resume remaining) and [⏹ Stop] (to stop live) must be enabled
    assert grid_view.btn_start.isEnabled() is True
    assert grid_view.btn_stop.isEnabled() is True

    grid_view.close()


def test_stream_worker_instant_frame_seeding():
    """Verifies that subscribing a camera ID to an active StreamWorker immediately seeds the latest frame."""
    import numpy as np
    from src.core.stream_worker import StreamWorker

    frame_store = SharedFrameStore()
    worker = StreamWorker(camera_id=1, stream_url="mock://cam", frame_store=frame_store)

    # Simulate cached latest frame
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    worker._latest_frame = dummy_frame

    # Subscribe camera 2 to this existing worker
    worker.add_camera_id(2)

    # FrameStore must immediately have camera 2 online with the cached frame
    frame, seq, is_online = frame_store.get_frame_with_seq(2)
    assert is_online is True
    assert frame is not None
    assert np.array_equal(frame, dummy_frame)


def test_stream_worker_invalidates_latest_frame_on_release():
    """Verifies that release_capture clears the cached frame to avoid stale seeding on disconnect."""
    import numpy as np
    from src.core.stream_worker import StreamWorker

    frame_store = SharedFrameStore()
    worker = StreamWorker(camera_id=1, stream_url="mock://cam", frame_store=frame_store)
    worker._latest_frame = np.zeros((100, 100, 3), dtype=np.uint8)

    # Release capture (simulating disconnect or teardown)
    worker._release_capture()
    assert worker._latest_frame is None

    # Adding a camera now should not seed any stale frame
    worker.add_camera_id(3)
    assert frame_store.get_frame(3) is None


def test_focus_mode_toolbar_status_updates(qapp, sample_cameras):
    """Verifies that toolbar status pill and buttons accurately track the single focused camera in Focus Mode."""
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    # 1. Maximize Camera 2
    grid_view.maximize_camera(2)
    assert grid_view.container_stack.currentIndex() == 1
    assert "LIVE" in grid_view.status_pill.text()
    assert grid_view.btn_stop.isEnabled() is True
    assert grid_view.btn_start.isEnabled() is False

    # 2. Stop Camera 2 while in focus
    grid_view.toggle_camera_stream(2)
    assert 2 in grid_view.stopped_cameras
    assert "DIHENTIKAN" in grid_view.status_pill.text()
    assert grid_view.btn_start.isEnabled() is True
    assert grid_view.btn_stop.isEnabled() is False

    # 3. Resume Camera 2
    grid_view.toggle_camera_stream(2)
    assert 2 not in grid_view.stopped_cameras
    assert "LIVE" in grid_view.status_pill.text()
    assert grid_view.btn_stop.isEnabled() is True
    assert grid_view.btn_start.isEnabled() is False

    # 4. Restore grid
    grid_view.restore_grid()
    assert grid_view.container_stack.currentIndex() == 0
    assert "LIVE" in grid_view.status_pill.text()

    grid_view.close()
