import os
import pytest

# Ensure headless Qt operation in Linux test environment
os.environ["QT_QPA_PLATFORM"] = "offscreen"


def test_gui_components_initialization():
    try:
        from PySide6.QtWidgets import QApplication
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

    # Initialize QApplication if not already running
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store)

    cams = [
        Camera(id=1, name="Camera 1", sub_stream_url="", main_stream_url="", is_counter_target="Cam 1"),
        Camera(id=2, name="Camera 2", sub_stream_url="", main_stream_url="", is_counter_target="Cam 2")
    ]

    # Test VideoTile
    tile = VideoTile(camera_id=1, camera_name="Test Cam")
    assert tile.camera_id == 1
    assert tile._is_online is False

    # Test HUDOverlay
    tripwire = LineSegment(Point(0, 50), Point(100, 50))
    counter_state = CounterState(entered=10, exited=4)
    hud = HUDOverlay(tripwire=tripwire, counter_state=counter_state)
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

    worker_pool.stop_all()
