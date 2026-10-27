import numpy as np
import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage
from src.presentation.widgets.video_tile import VideoTile
from src.presentation.grid_view import GridView
from src.core.frame_store import SharedFrameStore
from src.core.worker_pool import StreamWorkerPool
from src.domain.entities import Camera


@pytest.fixture
def sample_cameras():
    return [
        Camera(id=i, name=f"Camera {i}", stream_url=f"mock://cam{i}")
        for i in range(1, 26)
    ]


def test_video_tile_aspect_ratio_16_9(qapp):
    """Verifies that a 16:9 frame (e.g. 640x360) preserves its 16:9 aspect ratio without distortion."""
    tile = VideoTile(camera_id=1, camera_name="Camera 1")
    tile.resize(400, 300)

    # 16:9 synthetic frame
    frame_16_9 = np.zeros((360, 640, 3), dtype=np.uint8)
    tile.set_frame_if_new(frame_16_9, seq=1, is_online=True)

    rect = tile.get_target_video_rect()
    # Aspect ratio should be 16:9 (within 1% margin)
    computed_aspect = rect.width() / float(rect.height())
    assert abs(computed_aspect - (16.0 / 9.0)) < 0.02
    assert rect.width() <= 400
    assert rect.height() <= 300
    assert tile.get_aspect_ratio_string() == "16:9"


def test_video_tile_aspect_ratio_4_3(qapp):
    """Verifies that a 4:3 frame (e.g. 640x480) preserves its 4:3 aspect ratio without distortion/gepeng."""
    tile = VideoTile(camera_id=2, camera_name="Camera 2")
    tile.resize(400, 300)

    # 4:3 synthetic frame
    frame_4_3 = np.zeros((480, 640, 3), dtype=np.uint8)
    tile.set_frame_if_new(frame_4_3, seq=1, is_online=True)

    rect = tile.get_target_video_rect()
    # Aspect ratio should be 4:3 (within 1% margin)
    computed_aspect = rect.width() / float(rect.height())
    assert abs(computed_aspect - (4.0 / 3.0)) < 0.02
    assert rect.width() <= 400
    assert rect.height() <= 300
    assert tile.get_aspect_ratio_string() == "4:3"


def test_video_tile_aspect_ratio_modes(qapp):
    """Verifies manual override modes: forced 16:9, forced 4:3, and stretch."""
    tile = VideoTile(camera_id=3, camera_name="Camera 3")
    tile.resize(500, 300)

    # Supply 4:3 frame
    frame_4_3 = np.zeros((480, 640, 3), dtype=np.uint8)
    tile.set_frame_if_new(frame_4_3, seq=1, is_online=True)

    # Force 16:9
    tile.set_aspect_ratio_mode("16:9")
    rect_16_9 = tile.get_target_video_rect()
    assert abs((rect_16_9.width() / float(rect_16_9.height())) - (16.0 / 9.0)) < 0.02

    # Force 4:3
    tile.set_aspect_ratio_mode("4:3")
    rect_4_3 = tile.get_target_video_rect()
    assert abs((rect_4_3.width() / float(rect_4_3.height())) - (4.0 / 3.0)) < 0.02

    # Force Stretch
    tile.set_aspect_ratio_mode("stretch")
    rect_stretch = tile.get_target_video_rect()
    assert rect_stretch == QRect(0, 0, 500, 300)


def test_grid_view_aspect_ratio_integration(qapp, sample_cameras):
    """Verifies that GridView correctly changes aspect ratio mode for all tiles and focus tile."""
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    assert grid_view.current_aspect_ratio_mode == "auto"
    assert all(t.aspect_ratio_mode == "auto" for t in grid_view.tiles.values())
    assert grid_view.focus_tile.aspect_ratio_mode == "auto"

    # Switch to 4:3 mode via combo box index 2
    grid_view.combo_aspect.setCurrentIndex(2)
    assert grid_view.current_aspect_ratio_mode == "4:3"
    assert all(t.aspect_ratio_mode == "4:3" for t in grid_view.tiles.values())
    assert grid_view.focus_tile.aspect_ratio_mode == "4:3"

    # Switch grid mode to 25; new tiles must inherit the 4:3 mode
    grid_view.set_grid_mode(25)
    assert len(grid_view.tiles) == 25
    assert all(t.aspect_ratio_mode == "4:3" for t in grid_view.tiles.values())

    grid_view.close()
