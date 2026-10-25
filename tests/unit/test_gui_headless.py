import os
import pytest


def test_gui_components_initialization(qapp):
    try:
        from src.domain.entities import Camera, CounterState
        from src.domain.geometry import Point, LineSegment
        from src.core.frame_store import SharedFrameStore
        from src.core.worker_pool import StreamWorkerPool
        from src.presentation.widgets.video_tile import VideoTile
        from src.presentation.widgets.hud_overlay import HUDOverlay
        from src.presentation.grid_view import GridView
        from src.presentation.counter_view import CounterView
        from src.presentation.main_window import MainWindow
    except ImportError:
        pytest.skip("PySide6 not yet installed in test environment")

    app = qapp

    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)

    cams = [
        Camera(id=1, name="Camera 1", sub_stream_url="", main_stream_url="", is_counter_target="Cam 1"),
        Camera(id=2, name="Camera 2", sub_stream_url="", main_stream_url="", is_counter_target="Cam 2")
    ]

    # Test VideoTile
    tile = VideoTile(camera_id=1, camera_name="Test Cam")
    assert tile.camera_id == 1
    assert tile._is_online is False

    # Test HUDOverlay
    tripwire = LineSegment(Point(0.1, 0.5), Point(0.9, 0.5))
    counter_state = CounterState(entered=10, exited=4)
    hud = HUDOverlay(normalized_tripwire=tripwire, counter_state=counter_state)
    assert hud.tripwire == tripwire
    assert hud.counter_state.current_inside == 6

    # Test MainWindow & GridView & CounterView instantiation
    window = MainWindow(cameras=cams, frame_store=frame_store, worker_pool=worker_pool)
    assert window.grid_view is not None
    assert window.counter_view is not None

    # Test switching tabs
    window.switch_to_tab(1)
    assert window.stack.currentIndex() == 1
    assert window.stack.currentWidget() == window.counter_view

    window.switch_to_tab(0)
    assert window.stack.currentIndex() == 0
    assert window.stack.currentWidget() == window.grid_view

    # Test grid mode switching
    window.grid_view.set_grid_mode(16)
    assert len(window.grid_view.tiles) == 16
    assert window.grid_view.current_mode == 16

    # Test live camera update via on_cameras_updated
    assert hasattr(window, "btn_manage_cameras")
    new_cams = [
        Camera(id=1, name="Updated Gate", sub_stream_url="rtsp://new1", main_stream_url="rtsp://new1"),
        Camera(id=2, name="Updated Lobby", sub_stream_url="rtsp://new2", main_stream_url="rtsp://new2")
    ]
    window.on_cameras_updated(new_cams)
    assert window.grid_view.cameras[1].name == "Updated Gate"
    assert window.counter_view.cameras[1].name == "Updated Gate"

    # Test CounterView camera assignment with out-of-order IDs (Finding 2)
    cams_out_of_order = [
        Camera(id=10, name="Cam 10", sub_stream_url="", main_stream_url="", is_counter_target="Cam 2"),
        Camera(id=25, name="Cam 25", sub_stream_url="", main_stream_url="", is_counter_target="Cam 1")
    ]
    test_counter_view = CounterView(cams_out_of_order, frame_store=frame_store, worker_pool=worker_pool)
    assert test_counter_view.cam1.id == 25
    assert test_counter_view.cam2.id == 10

    # Test headcount reset on camera swap (Finding 5)
    test_counter_view.cam_widget_1.counter_state.entered = 15
    assert test_counter_view.cam_widget_1.counter_state.entered == 15
    swapped_cams = [
        Camera(id=30, name="Cam 30", sub_stream_url="", main_stream_url="", is_counter_target="Cam 1"),
        Camera(id=10, name="Cam 10", sub_stream_url="", main_stream_url="", is_counter_target="Cam 2")
    ]
    test_counter_view.update_cameras(swapped_cams)
    assert test_counter_view.cam1.id == 30
    assert test_counter_view.cam_widget_1.counter_state.entered == 0  # Reset!

    # Test GridView with non-contiguous custom camera IDs (Audit Finding 1)
    custom_cams = [
        Camera(id=101, name="Custom Cam 101", sub_stream_url="", main_stream_url=""),
        Camera(id=102, name="Custom Cam 102", sub_stream_url="", main_stream_url=""),
        Camera(id=205, name="Custom Cam 205", sub_stream_url="", main_stream_url="")
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
    window.counter_view.pause_analytics()
    test_counter_view.pause_analytics()
    worker_pool.stop_all()
