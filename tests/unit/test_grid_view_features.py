import pytest
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QMouseEvent
from src.domain.entities import Camera
from src.core.frame_store import SharedFrameStore
from src.core.worker_pool import StreamWorkerPool
from src.presentation.grid_view import GridView


@pytest.fixture
def sample_cameras():
    return [
        Camera(id=i, name=f"Camera {i}", sub_stream_url=f"mock://cam{i}", main_stream_url=f"mock://cam{i}")
        for i in range(1, 17)
    ]


def test_grid_view_start_stop(qapp, sample_cameras):
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    # Initial state: active
    assert grid_view._is_streaming_active is True
    assert grid_view.btn_start.isEnabled() is False
    assert grid_view.btn_stop.isEnabled() is True
    assert grid_view.master_timer.isActive() is True

    # Stop streaming
    grid_view.stop_streaming()
    assert grid_view._is_streaming_active is False
    assert grid_view.btn_start.isEnabled() is True
    assert grid_view.btn_stop.isEnabled() is False
    assert grid_view.master_timer.isActive() is False
    assert all(t._is_stopped for t in grid_view.tiles.values())

    # Start streaming
    grid_view.start_streaming()
    assert grid_view._is_streaming_active is True
    assert grid_view.btn_start.isEnabled() is False
    assert grid_view.btn_stop.isEnabled() is True
    assert grid_view.master_timer.isActive() is True

    grid_view.close()


def test_grid_view_maximize_restore(qapp, sample_cameras):
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    assert grid_view.maximized_cam_id is None
    assert grid_view.btn_restore.isVisible() is False
    assert len(grid_view.tiles) == 16

    # Maximize Camera 1
    grid_view.toggle_maximize_camera(1)
    assert grid_view.maximized_cam_id == 1
    assert grid_view.container_stack.currentIndex() == 1
    assert grid_view.focus_tile.camera_id == 1
    assert grid_view.btn_restore.isVisible() is True

    # Double click again restores grid
    grid_view.toggle_maximize_camera(1)
    assert grid_view.maximized_cam_id is None
    assert grid_view.container_stack.currentIndex() == 0
    assert grid_view.btn_restore.isVisible() is False

    # Maximize Camera 2 and restore using btn_restore
    grid_view.toggle_maximize_camera(2)
    assert grid_view.maximized_cam_id == 2
    assert grid_view.container_stack.currentIndex() == 1
    assert grid_view.focus_tile.camera_id == 2
    grid_view.restore_grid()
    assert grid_view.maximized_cam_id is None
    assert grid_view.container_stack.currentIndex() == 0
    assert grid_view.btn_restore.isVisible() is False

    grid_view.close()


def test_video_tile_double_click_signal(qapp):
    from src.presentation.widgets.video_tile import VideoTile

    tile = VideoTile(camera_id=5, camera_name="Test Cam")
    received_ids = []
    tile.double_clicked.connect(lambda cid: received_ids.append(cid))

    # Simulate double click event
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonDblClick,
        QPointF(10.0, 10.0),
        QPointF(10.0, 10.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    tile.mouseDoubleClickEvent(event)

    assert received_ids == [5]
