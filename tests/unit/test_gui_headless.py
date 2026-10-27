import os
import pytest


def test_gui_components_initialization(qapp):
    try:
        from src.domain.entities import Camera
        from src.core.frame_store import SharedFrameStore
        from src.core.worker_pool import StreamWorkerPool
        from src.presentation.widgets.video_tile import VideoTile
        from src.presentation.grid_view import GridView
        from src.presentation.main_window import MainWindow
    except ImportError:
        pytest.skip("PySide6 not yet installed in test environment")

    app = qapp

    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)

    cams = [
        Camera(id=1, name="Camera 1", stream_url=""),
        Camera(id=2, name="Camera 2", stream_url="")
    ]

    # Test VideoTile
    tile = VideoTile(camera_id=1, camera_name="Test Cam")
    assert tile.camera_id == 1
    assert tile._is_online is False

    # Test MainWindow & GridView instantiation
    window = MainWindow(cameras=cams, frame_store=frame_store, worker_pool=worker_pool)
    assert window.grid_view is not None
    assert window.centralWidget() == window.grid_view

    # Test grid mode switching
    window.grid_view.set_grid_mode(16)
    assert len(window.grid_view.tiles) == 16
    assert window.grid_view.current_mode == 16

    # Test live camera update via on_cameras_updated
    assert hasattr(window.grid_view, "btn_manage_cameras")
    new_cams = [
        Camera(id=1, name="Updated Gate", stream_url="rtsp://new1"),
        Camera(id=2, name="Updated Lobby", stream_url="rtsp://new2")
    ]
    window.on_cameras_updated(new_cams)
    assert window.grid_view.cameras[1].name == "Updated Gate"

    # Test GridView with non-contiguous custom camera IDs (Audit Finding 1)
    custom_cams = [
        Camera(id=101, name="Custom Cam 101", stream_url=""),
        Camera(id=102, name="Custom Cam 102", stream_url=""),
        Camera(id=205, name="Custom Cam 205", stream_url="")
    ]
    custom_grid = GridView(custom_cams, frame_store=frame_store, worker_pool=worker_pool)
    custom_grid.set_grid_mode(16)
    assert len(custom_grid.tiles) == 16
    assert 101 in custom_grid.tiles
    assert 102 in custom_grid.tiles
    assert 205 in custom_grid.tiles
    assert custom_grid.tiles[101].camera_name == "Custom Cam 101"

    custom_grid.pause_rendering()
    window.grid_view.pause_rendering()
    worker_pool.stop_all()
