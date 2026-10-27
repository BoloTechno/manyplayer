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
        Camera(id=i, name=f"Camera {i}", stream_url=f"mock://cam{i}")
        for i in range(1, 17)
    ]


def test_grid_view_start_stop(qapp, sample_cameras):
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    # Initial state: Standby (waits for user to click Mulai)
    assert grid_view._is_streaming_active is False
    assert grid_view.btn_start.isEnabled() is True
    assert grid_view.btn_stop.isEnabled() is False
    assert grid_view.master_timer.isActive() is False
    assert "STANDBY" in grid_view.status_pill.text()
    assert all(t._is_stopped for t in grid_view.tiles.values())

    # User starts streaming
    grid_view.start_streaming()
    assert grid_view._is_streaming_active is True
    assert grid_view.btn_start.isEnabled() is False
    assert grid_view.btn_stop.isEnabled() is True
    assert grid_view.master_timer.isActive() is True
    assert "LIVE" in grid_view.status_pill.text()

    # User stops streaming
    grid_view.stop_streaming()
    assert grid_view._is_streaming_active is False
    assert grid_view.btn_start.isEnabled() is True
    assert grid_view.btn_stop.isEnabled() is False
    assert grid_view.master_timer.isActive() is False
    assert "DIHENTIKAN" in grid_view.status_pill.text()
    assert all(t._is_stopped for t in grid_view.tiles.values())

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
    assert grid_view.btn_16.isVisible() is False
    assert grid_view.mode_label.isVisible() is False

    # Double click again restores grid
    grid_view.toggle_maximize_camera(1)
    assert grid_view.maximized_cam_id is None
    assert grid_view.container_stack.currentIndex() == 0
    assert grid_view.btn_restore.isVisible() is False
    assert grid_view.btn_16.isVisible() is True
    assert grid_view.mode_label.isVisible() is True

    # Maximize Camera 2 and restore using btn_restore
    grid_view.toggle_maximize_camera(2)
    assert grid_view.maximized_cam_id == 2
    assert grid_view.container_stack.currentIndex() == 1
    assert grid_view.focus_tile.camera_id == 2
    grid_view.restore_grid()
    assert grid_view.maximized_cam_id is None
    assert grid_view.container_stack.currentIndex() == 0
    assert grid_view.btn_restore.isVisible() is False
    assert grid_view.btn_16.isVisible() is True
    assert grid_view.mode_label.isVisible() is True

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


def test_main_window_screen_resolution_bounds(qapp, sample_cameras):
    """Verifies MainWindow sizes within screen resolution and does not stretch on camera maximize."""
    from src.presentation.main_window import MainWindow
    from PySide6.QtWidgets import QApplication

    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    window = MainWindow(sample_cameras, frame_store, worker_pool)
    window.show()

    screen = QApplication.primaryScreen()
    if screen:
        avail = screen.availableGeometry()
        assert window.width() <= avail.width()
        assert window.height() <= avail.height()

    initial_size = window.size()

    # Maximize camera
    window.grid_view.toggle_maximize_camera(1)
    # Size must not expand beyond screen or initial window bounds
    assert window.size().width() <= (avail.width() if screen else 1920)
    assert window.size().height() <= (avail.height() if screen else 1080)
    assert window.size() == initial_size

    # Restore camera
    window.grid_view.restore_grid()
    assert window.size() == initial_size

    window.close()


def test_video_tile_click_selection(qapp):
    """Verifies that mouse click on VideoTile emits clicked signal and updates selection."""
    from src.presentation.widgets.video_tile import VideoTile

    tile = VideoTile(camera_id=7, camera_name="Corridor Cam")
    assert tile._is_selected is False

    clicked_ids = []
    tile.clicked.connect(lambda cid: clicked_ids.append(cid))

    # Simulate single click
    press_ev = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(10.0, 10.0),
        QPointF(10.0, 10.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    tile.mousePressEvent(press_ev)

    assert clicked_ids == [7]
    tile.set_selected(True)
    assert tile._is_selected is True


def test_grid_view_camera_selection(qapp, sample_cameras):
    """Verifies that selecting a camera updates active border highlight across the grid."""
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    # Default: Camera 1 is selected
    assert grid_view.selected_cam_id == 1
    assert grid_view.tiles[1]._is_selected is True
    assert all(not t._is_selected for cid, t in grid_view.tiles.items() if cid != 1)

    # Select Camera 3
    grid_view.select_camera(3)
    assert grid_view.selected_cam_id == 3
    assert grid_view.tiles[3]._is_selected is True
    assert grid_view.tiles[1]._is_selected is False

    # Switch grid mode to 25; selection of Camera 3 is preserved
    grid_view.set_grid_mode(25)
    assert grid_view.selected_cam_id == 3
    assert grid_view.tiles[3]._is_selected is True
    assert grid_view.tiles[1]._is_selected is False

    grid_view.close()
