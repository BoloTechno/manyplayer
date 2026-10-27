import os
import tempfile
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QComboBox

from src.domain.entities import Camera
from src.core.camera_store import CameraStore
from src.presentation.widgets.video_tile import VideoTile
from src.presentation.dialogs.camera_config_dialog import CameraConfigDialog
from src.presentation.grid_view import GridView
from src.core.frame_store import SharedFrameStore
from src.core.worker_pool import StreamWorkerPool


def test_camera_entity_orientation_defaults():
    cam = Camera(id=1, name="Cam 1", stream_url="rtsp://test")
    assert cam.rotation == 0
    assert cam.flip_h is False

    cam_custom = Camera(id=2, name="Cam 2", stream_url="rtsp://test2", rotation=90, flip_h=True)
    assert cam_custom.rotation == 90
    assert cam_custom.flip_h is True


def test_camera_store_orientation_persistence():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        store = CameraStore(tmp_path)
        cams = [
            Camera(id=1, name="Normal", stream_url="rtsp://1", rotation=0, flip_h=False),
            Camera(id=2, name="Rotate 90", stream_url="rtsp://2", rotation=90, flip_h=False),
            Camera(id=3, name="Rotate 180 + Flip", stream_url="rtsp://3", rotation=180, flip_h=True),
            Camera(id=4, name="Rotate 270", stream_url="rtsp://4", rotation=270, flip_h=False),
        ]
        store.save_cameras(cams)

        loaded = store.load_cameras()
        assert len(loaded) == 4

        assert loaded[0].rotation == 0
        assert loaded[0].flip_h is False

        assert loaded[1].rotation == 90
        assert loaded[1].flip_h is False

        assert loaded[2].rotation == 180
        assert loaded[2].flip_h is True

        assert loaded[3].rotation == 270
        assert loaded[3].flip_h is False
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_video_tile_frame_rotation_and_flip(qapp):
    tile = VideoTile(camera_id=1, camera_name="Test Cam")
    assert tile.rotation == 0
    assert tile.flip_h is False

    # Create dummy 16:9 frame (height=360, width=640, 3 channels)
    # Distinct top-left corner marker to test flip and rotation
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    frame[0:10, 0:10] = [255, 0, 0]  # Blue in BGR

    # Test Normal
    tile.set_frame_if_new(frame, seq=1, is_online=True)
    assert tile._qimage is not None
    assert tile._qimage.width() == 640
    assert tile._qimage.height() == 360

    # Test 90° Clockwise
    tile.set_orientation(90, False)
    assert tile.rotation == 90
    assert tile.flip_h is False
    assert tile._qimage.width() == 360
    assert tile._qimage.height() == 640

    # Test 180°
    tile.set_orientation(180, False)
    assert tile.rotation == 180
    assert tile._qimage.width() == 640
    assert tile._qimage.height() == 360

    # Test 270° Counter-Clockwise
    tile.set_orientation(270, False)
    assert tile.rotation == 270
    assert tile._qimage.width() == 360
    assert tile._qimage.height() == 640

    # Test Flip Horizontal
    tile.set_orientation(0, True)
    assert tile.rotation == 0
    assert tile.flip_h is True
    assert tile._qimage.width() == 640
    assert tile._qimage.height() == 360


def test_video_tile_target_rect_portrait_when_rotated_90(qapp):
    tile = VideoTile(camera_id=1, camera_name="Test Cam")
    tile.resize(800, 600)

    # 16:9 Landscape frame
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    tile.set_frame_if_new(frame, seq=1, is_online=True)

    # Normal 16:9 in Fit mode
    rect_normal = tile.get_target_video_rect()
    assert rect_normal.width() > rect_normal.height()

    # Rotated 90° -> Inverted aspect ratio (9:16 portrait)
    tile.set_orientation(90, False)
    rect_rotated = tile.get_target_video_rect()
    assert rect_rotated.height() > rect_rotated.width()


def test_video_tile_context_menu_rotation_actions(qapp):
    from unittest.mock import MagicMock, patch
    from PySide6.QtGui import QContextMenuEvent
    from PySide6.QtCore import QPoint

    tile = VideoTile(camera_id=1, camera_name="Test Cam")

    signals_emitted = []
    tile.orientation_changed.connect(lambda cid, rot, flip: signals_emitted.append((cid, rot, flip)))

    # 1. Directly test handler logic
    tile._on_rotation_action_triggered(180)
    assert tile.rotation == 180
    assert tile.flip_h is False
    assert len(signals_emitted) == 1
    assert signals_emitted[-1] == (1, 180, False)

    tile._on_mirror_action_triggered()
    assert tile.rotation == 180
    assert tile.flip_h is True
    assert len(signals_emitted) == 2
    assert signals_emitted[-1] == (1, 180, True)

    # 2. Test contextMenuEvent wiring and signal connections
    event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(10, 10))
    with patch("src.presentation.widgets.video_tile.QMenu") as MockMenu:
        mock_menu_inst = MagicMock()
        mock_submenu_inst = MagicMock()
        MockMenu.return_value = mock_menu_inst
        mock_menu_inst.addMenu.return_value = mock_submenu_inst
        mock_menu_inst.exec.return_value = None

        tile.contextMenuEvent(event)
        MockMenu.assert_called_once()
        mock_menu_inst.exec.assert_called_once()
        mock_menu_inst.addMenu.assert_called_once_with("🔄 Rotasi & Balik Kamera")


def test_grid_view_camera_orientation_changed(qapp):
    cameras = [
        Camera(id=1, name="Camera 1", stream_url="rtsp://1"),
        Camera(id=2, name="Camera 2", stream_url="rtsp://2")
    ]
    frame_store = SharedFrameStore()
    mock_pool = MagicMock(spec=StreamWorkerPool)
    mock_store = MagicMock(spec=CameraStore)

    grid = GridView(
        cameras=cameras,
        frame_store=frame_store,
        worker_pool=mock_pool,
        camera_store=mock_store
    )

    # Simulate orientation change on Camera 1 to 90 degrees
    grid.on_camera_orientation_changed(1, 90, True)

    assert grid.cameras[1].rotation == 90
    assert grid.cameras[1].flip_h is True
    mock_store.save_cameras.assert_called_once()

    # Verify tile orientation updated
    tile1 = grid.tiles.get(1)
    if tile1:
        assert tile1.rotation == 90
        assert tile1.flip_h is True

    # Test focus tile orientation updates when camera is maximized
    grid.maximize_camera(1)
    assert grid.focus_tile.rotation == 90
    assert grid.focus_tile.flip_h is True

    # Changing orientation while maximized
    grid.on_camera_orientation_changed(1, 270, False)
    assert grid.focus_tile.rotation == 270
    assert grid.focus_tile.flip_h is False


def test_camera_config_dialog_orientation_combo(qapp):
    cameras = [
        Camera(id=1, name="Camera 1", stream_url="rtsp://1", rotation=180, flip_h=True),
        Camera(id=2, name="Camera 2", stream_url="rtsp://2", rotation=0, flip_h=False),
    ]
    mock_store = MagicMock()
    dialog = CameraConfigDialog(cameras=cameras, camera_store=mock_store)

    assert dialog.table.rowCount() == 2
    assert dialog.table.columnCount() == 4

    combo_row0 = dialog.table.cellWidget(0, 3)
    assert isinstance(combo_row0, QComboBox)
    assert combo_row0.currentData() == (180, True)

    combo_row1 = dialog.table.cellWidget(1, 3)
    assert isinstance(combo_row1, QComboBox)
    assert combo_row1.currentData() == (0, False)

    # Change orientation of row 1 to 90°
    # Find index for (90, False)
    idx_90 = -1
    for i in range(combo_row1.count()):
        if combo_row1.itemData(i) == (90, False):
            idx_90 = i
            break
    assert idx_90 != -1
    combo_row1.setCurrentIndex(idx_90)

    # Save and apply
    with patch.object(dialog, "accept"):
        dialog.save_and_apply()

    assert len(dialog.saved_cameras) == 2
    assert dialog.saved_cameras[0].rotation == 180
    assert dialog.saved_cameras[0].flip_h is True
    assert dialog.saved_cameras[1].rotation == 90
    assert dialog.saved_cameras[1].flip_h is False
    mock_store.save_cameras.assert_called_once()
