import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF
from PySide6.QtGui import QEnterEvent
from src.presentation.widgets.video_tile import VideoTile
from src.presentation.grid_view import GridView
from src.core.frame_store import SharedFrameStore
from src.core.worker_pool import StreamWorkerPool
from src.domain.entities import Camera


@pytest.fixture
def sample_cameras():
    return [
        Camera(id=i, name=f"Camera {i:02d}", stream_url=f"mock://cam{i}")
        for i in range(1, 26)
    ]


def test_video_tile_osd_visibility_modes(qapp):
    """Verifies OSD visibility for smart, hover, and hidden modes."""
    tile = VideoTile(camera_id=1, camera_name="Lobby Cam")

    # 1. Smart mode: visible by default
    assert tile.osd_mode == "smart"
    assert tile.should_show_osd() is True

    # 2. Hover mode: only visible when hovered
    tile.set_osd_mode("hover")
    assert tile.osd_mode == "hover"
    assert tile.should_show_osd() is False

    # Simulate mouse enter
    pt = QPointF(10.0, 10.0)
    enter_ev = QEnterEvent(pt, pt, pt)
    tile.enterEvent(enter_ev)
    assert tile._is_hovered is True
    assert tile.should_show_osd() is True

    # Simulate mouse leave
    leave_ev = QEvent(QEvent.Type.Leave)
    tile.leaveEvent(leave_ev)
    assert tile._is_hovered is False
    assert tile.should_show_osd() is False

    # 3. Hidden mode: never visible
    tile.set_osd_mode("hidden")
    assert tile.osd_mode == "hidden"
    assert tile.should_show_osd() is False
    tile.enterEvent(enter_ev)
    assert tile.should_show_osd() is False


def test_video_tile_osd_smart_margin_placement(qapp):
    """Verifies that in smart mode with top letterbox, title is placed outside video frame."""
    tile = VideoTile(camera_id=2, camera_name="Entrance Cam")
    # Set tile to a tall geometry (400 width x 400 height) with 16:9 frame (640x360)
    tile.resize(400, 400)
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    tile.set_frame_if_new(frame, seq=1, is_online=True)

    target_rect = tile.get_target_video_rect()
    # 16:9 frame in 400x400 cell produces a top letterbox margin of ~88px
    assert target_rect.top() > 20

    # Ensure should_show_osd is active
    assert tile.should_show_osd() is True


def test_grid_view_osd_mode_propagation(qapp, sample_cameras):
    """Verifies that GridView toolbar combo box propagates OSD mode to all tiles and focus tile."""
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    assert grid_view.current_osd_mode == "smart"
    assert all(t.osd_mode == "smart" for t in grid_view.tiles.values())
    assert grid_view.focus_tile.osd_mode == "smart"

    # Switch combo box to index 1 ("Saat Hover")
    grid_view.combo_osd.setCurrentIndex(1)
    assert grid_view.current_osd_mode == "hover"
    assert all(t.osd_mode == "hover" for t in grid_view.tiles.values())
    assert grid_view.focus_tile.osd_mode == "hover"

    # Switch combo box to index 2 ("Sembunyi")
    grid_view.combo_osd.setCurrentIndex(2)
    assert grid_view.current_osd_mode == "hidden"
    assert all(t.osd_mode == "hidden" for t in grid_view.tiles.values())
    assert grid_view.focus_tile.osd_mode == "hidden"

    # Switch layout to 25; new tiles must inherit the active OSD mode
    grid_view.set_grid_mode(25)
    assert len(grid_view.tiles) == 25
    assert all(t.osd_mode == "hidden" for t in grid_view.tiles.values())

    grid_view.close()
