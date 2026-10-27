import pytest
from PySide6.QtCore import Qt, QPointF, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from src.domain.entities import Camera
from src.core.frame_store import SharedFrameStore
from src.core.worker_pool import StreamWorkerPool
from src.presentation.grid_view import GridView
from src.presentation.widgets.video_tile import VideoTile


@pytest.fixture
def sample_cameras():
    return [
        Camera(
            id=i,
            name=f"Camera {i:02d}",
            stream_url=f"mock://cam{i}"
        )
        for i in range(1, 17)
    ]


def test_video_tile_drag_enter_and_leave(qapp):
    """Tests dragEnterEvent highlighting and dragLeaveEvent cleanup."""
    tile = VideoTile(camera_id=2, camera_name="Camera 02")
    assert tile._is_drop_target is False

    # 1. Matching MIME data from another camera (ID 1)
    mime = QMimeData()
    mime.setData("application/x-manyplayer-cam-id", b"1")
    enter_ev = QDragEnterEvent(
        QPointF(10.0, 10.0),
        Qt.DropAction.MoveAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    tile.dragEnterEvent(enter_ev)
    assert enter_ev.isAccepted() is True
    assert tile._is_drop_target is True

    # 2. Drag leave clears target highlight
    leave_ev = QDragLeaveEvent()
    tile.dragLeaveEvent(leave_ev)
    assert tile._is_drop_target is False

    # 3. Same camera ID (ID 2) drag ignored
    mime_self = QMimeData()
    mime_self.setData("application/x-manyplayer-cam-id", b"2")
    enter_self = QDragEnterEvent(
        QPointF(10.0, 10.0),
        Qt.DropAction.MoveAction,
        mime_self,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    tile.dragEnterEvent(enter_self)
    assert enter_self.isAccepted() is False
    assert tile._is_drop_target is False

    # 4. Unknown MIME format ignored
    mime_other = QMimeData()
    mime_other.setText("some-other-data")
    enter_other = QDragEnterEvent(
        QPointF(10.0, 10.0),
        Qt.DropAction.MoveAction,
        mime_other,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    tile.dragEnterEvent(enter_other)
    assert enter_other.isAccepted() is False
    assert tile._is_drop_target is False

    tile.deleteLater()


def test_video_tile_drop_event_emits_swap_requested(qapp):
    """Tests dropEvent triggers swap_requested with correct source and target IDs."""
    tile = VideoTile(camera_id=4, camera_name="Camera 04")
    emitted_signals = []
    tile.swap_requested.connect(lambda src, dst: emitted_signals.append((src, dst)))

    mime = QMimeData()
    mime.setData("application/x-manyplayer-cam-id", b"1")
    drop_ev = QDropEvent(
        QPointF(20.0, 20.0),
        Qt.DropAction.MoveAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )

    tile.dropEvent(drop_ev)
    assert drop_ev.isAccepted() is True
    assert tile._is_drop_target is False
    assert emitted_signals == [(1, 4)]

    tile.deleteLater()


def test_grid_view_swap_camera_slots(qapp, sample_cameras):
    """Tests instant widget swapping in QGridLayout and custom_order synchronization."""
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    # Initial order should match sorted camera IDs [1, 2, 3, 4, ...]
    assert grid_view.custom_order[0] == 1
    assert grid_view.custom_order[3] == 4

    tile_cam1 = grid_view.tiles[1]
    tile_cam4 = grid_view.tiles[4]

    # Verify initial layout positions in 4x4 (Row 0 Col 0 vs Row 0 Col 3)
    assert grid_view.grid_layout.itemAtPosition(0, 0).widget() == tile_cam1
    assert grid_view.grid_layout.itemAtPosition(0, 3).widget() == tile_cam4

    # Swap Camera 1 and Camera 4
    grid_view.swap_camera_slots(1, 4)

    # 1. custom_order updated
    assert grid_view.custom_order[0] == 4
    assert grid_view.custom_order[3] == 1

    # 2. QGridLayout widget items swapped
    assert grid_view.grid_layout.itemAtPosition(0, 0).widget() == tile_cam4
    assert grid_view.grid_layout.itemAtPosition(0, 3).widget() == tile_cam1

    # 3. Selected camera is now Camera 1 (the moved camera)
    assert grid_view.selected_cam_id == 1
    assert tile_cam1._is_selected is True
    assert tile_cam4._is_selected is False

    # 4. Stream workers still active for visible cameras
    visible_cams = set(grid_view.custom_order[:16])
    assert 1 in visible_cams and 4 in visible_cams

    grid_view.close()


def test_grid_view_swap_with_placeholder_slot(qapp, sample_cameras):
    """Tests swapping an active camera into an empty placeholder slot in 25-mode."""
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    # Switch to 25-mode (sample_cameras has 16, so slots 16-24 are placeholder slots)
    grid_view.set_grid_mode(25)
    assert len(grid_view.custom_order) >= 25

    placeholder_id = grid_view.custom_order[16]
    assert placeholder_id < 0  # Placeholder slot has negative ID

    tile_cam1 = grid_view.tiles[1]
    tile_placeholder = grid_view.tiles[placeholder_id]

    # In 5x5:
    # Slot 0 is Row 0 Col 0
    # Slot 16 is Row 3 Col 1 (16 // 5 = 3, 16 % 5 = 1)
    assert grid_view.grid_layout.itemAtPosition(0, 0).widget() == tile_cam1
    assert grid_view.grid_layout.itemAtPosition(3, 1).widget() == tile_placeholder

    # Swap Camera 1 into Slot 16
    grid_view.swap_camera_slots(1, placeholder_id)

    # Verify custom_order
    assert grid_view.custom_order[0] == placeholder_id
    assert grid_view.custom_order[16] == 1

    # Verify grid layout positions
    assert grid_view.grid_layout.itemAtPosition(0, 0).widget() == tile_placeholder
    assert grid_view.grid_layout.itemAtPosition(3, 1).widget() == tile_cam1

    grid_view.close()


def test_grid_view_custom_order_preserved_across_mode_switches(qapp, sample_cameras):
    """Tests that swapped order is retained when switching between 16, 25, and 36 modes."""
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    # Swap 2 and 3 in 16-mode
    grid_view.swap_camera_slots(2, 3)
    assert grid_view.custom_order[1] == 3
    assert grid_view.custom_order[2] == 2

    # Switch to 25-mode
    grid_view.set_grid_mode(25)
    assert grid_view.custom_order[1] == 3
    assert grid_view.custom_order[2] == 2

    # Switch to 36-mode
    grid_view.set_grid_mode(36)
    assert grid_view.custom_order[1] == 3
    assert grid_view.custom_order[2] == 2

    # Switch back to 16-mode
    grid_view.set_grid_mode(16)
    assert grid_view.custom_order[1] == 3
    assert grid_view.custom_order[2] == 2
    assert grid_view.grid_layout.itemAtPosition(0, 1).widget().camera_id == 3
    assert grid_view.grid_layout.itemAtPosition(0, 2).widget().camera_id == 2

    grid_view.close()


def test_grid_view_update_cameras_preserves_custom_order(qapp, sample_cameras):
    """Tests that adding or updating cameras retains previous custom ordering."""
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, is_mock=True)
    grid_view = GridView(sample_cameras, frame_store, worker_pool)
    grid_view.show()

    # Swap Camera 1 and Camera 2
    grid_view.swap_camera_slots(1, 2)
    assert grid_view.custom_order[0] == 2
    assert grid_view.custom_order[1] == 1

    # Update cameras with an additional Camera 17
    new_cameras = list(sample_cameras) + [
        Camera(id=17, name="Camera 17", stream_url="mock://cam17")
    ]
    grid_view.update_cameras(new_cameras)

    # Swapped positions for 1 and 2 must be preserved
    assert grid_view.custom_order[0] == 2
    assert grid_view.custom_order[1] == 1
    # Camera 17 should be appended
    assert 17 in grid_view.custom_order

    grid_view.close()
