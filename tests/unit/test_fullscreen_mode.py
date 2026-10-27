import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from src.presentation.main_window import MainWindow
from src.core.frame_store import SharedFrameStore
from src.core.worker_pool import StreamWorkerPool
from src.domain.entities import Camera


@pytest.fixture
def sample_cameras():
    return [
        Camera(id=i, name=f"Camera {i:02d}", stream_url=f"mock://cam{i}")
        for i in range(1, 17)
    ]


def test_fullscreen_toggle_state(qapp, sample_cameras):
    """Verifies that entering fullscreen updates state, and exiting restores it."""
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    window = MainWindow(sample_cameras, frame_store, worker_pool)
    window.show()

    # Initial state
    assert window.isFullScreen() is False
    assert "Fullscreen" in window.grid_view.btn_fullscreen.text()

    # Enter Fullscreen
    window.enter_fullscreen()
    assert window.isFullScreen() is True
    assert "Normal" in window.grid_view.btn_fullscreen.text()

    # Exit Fullscreen
    window.exit_fullscreen()
    assert window.isFullScreen() is False
    assert "Fullscreen" in window.grid_view.btn_fullscreen.text()

    window.close()


def test_fullscreen_f11_shortcut(qapp, sample_cameras):
    """Verifies that F11 key toggles fullscreen mode."""
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    window = MainWindow(sample_cameras, frame_store, worker_pool)
    window.show()

    # Press F11 -> Fullscreen
    f11_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_F11, Qt.KeyboardModifier.NoModifier)
    window.keyPressEvent(f11_event)
    assert window.isFullScreen() is True
    assert "Normal" in window.grid_view.btn_fullscreen.text()

    # Press F11 again -> Exit Fullscreen
    window.keyPressEvent(f11_event)
    assert window.isFullScreen() is False
    assert "Fullscreen" in window.grid_view.btn_fullscreen.text()

    window.close()


def test_tiered_escape_key_navigation(qapp, sample_cameras):
    """Verifies tiered ESC navigation:
    1. First ESC restores 1x1 focused camera back to multi-grid.
    2. Second ESC exits Fullscreen mode back to normal windowed.
    """
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    window = MainWindow(sample_cameras, frame_store, worker_pool)
    window.show()

    # Enter Fullscreen
    window.enter_fullscreen()
    assert window.isFullScreen() is True

    # Maximize Camera 1 (1x1 Focus Mode) while in Fullscreen
    window.grid_view.toggle_maximize_camera(1)
    assert window.grid_view.maximized_cam_id == 1
    assert window.grid_view.container_stack.currentIndex() == 1

    esc_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)

    # 1st ESC press: Must restore grid view, remaining in Fullscreen
    window.keyPressEvent(esc_event)
    assert window.grid_view.maximized_cam_id is None
    assert window.grid_view.container_stack.currentIndex() == 0
    assert window.isFullScreen() is True

    # 2nd ESC press: Must exit Fullscreen
    window.keyPressEvent(esc_event)
    assert window.isFullScreen() is False
    assert "Fullscreen" in window.grid_view.btn_fullscreen.text()

    window.close()


def test_grid_view_toolbar_fullscreen_button(qapp, sample_cameras):
    """Verifies that clicking the fullscreen button on GridView toolbar toggles window fullscreen."""
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    window = MainWindow(sample_cameras, frame_store, worker_pool)
    window.show()

    assert window.isFullScreen() is False

    # Click GridView toolbar fullscreen button
    window.grid_view.btn_fullscreen.click()
    assert window.isFullScreen() is True
    assert "Normal" in window.grid_view.btn_fullscreen.text()

    # Click GridView toolbar fullscreen button again (now showing Normal)
    window.grid_view.btn_fullscreen.click()
    assert window.isFullScreen() is False
    assert "Fullscreen" in window.grid_view.btn_fullscreen.text()

    window.close()
