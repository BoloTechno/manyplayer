import os
import pytest
from unittest.mock import MagicMock, patch


def test_camera_config_dialog_initialization(qapp):
    from PySide6.QtWidgets import QComboBox
    from src.domain.entities import Camera
    from src.presentation.dialogs.camera_config_dialog import CameraConfigDialog

    cams = [
        Camera(1, "Gate Cam", "rtsp://192.168.1.10/sub", "rtsp://192.168.1.10/main", is_counter_target="Cam 1"),
        Camera(2, "Lobby Cam", "rtsp://192.168.1.11/sub", "rtsp://192.168.1.11/main", is_counter_target=None)
    ]

    dialog = CameraConfigDialog(cams)
    assert dialog.table.rowCount() == 2

    # Check row 0
    assert dialog.table.item(0, 0).text() == "1"
    assert dialog.table.item(0, 1).text() == "Gate Cam"
    assert dialog.table.item(0, 2).text() == "rtsp://192.168.1.10/sub"
    combo0 = dialog.table.cellWidget(0, 4)
    assert isinstance(combo0, QComboBox)
    assert combo0.currentText() == "Cam 1"

    # Check row 1
    assert dialog.table.item(1, 0).text() == "2"
    assert dialog.table.item(1, 1).text() == "Lobby Cam"
    combo1 = dialog.table.cellWidget(1, 4)
    assert isinstance(combo1, QComboBox)
    assert combo1.currentText() == "Tidak"


def test_camera_config_dialog_add_row(qapp):
    from src.domain.entities import Camera
    from src.presentation.dialogs.camera_config_dialog import CameraConfigDialog

    cams = [
        Camera(1, "Camera 01", "rtsp://test/1", "rtsp://test/1")
    ]
    dialog = CameraConfigDialog(cams)
    assert dialog.table.rowCount() == 1

    dialog.add_camera_row()
    assert dialog.table.rowCount() == 2
    assert dialog.table.item(1, 0).text() == "2"
    assert dialog.table.item(1, 1).text() == "Kamera 02"


def test_camera_config_dialog_delete_row(qapp):
    from PySide6.QtWidgets import QMessageBox
    from src.domain.entities import Camera
    from src.presentation.dialogs.camera_config_dialog import CameraConfigDialog

    cams = [
        Camera(1, "Cam 1", "rtsp://test/1", "rtsp://test/1"),
        Camera(2, "Cam 2", "rtsp://test/2", "rtsp://test/2")
    ]
    dialog = CameraConfigDialog(cams)
    assert dialog.table.rowCount() == 2

    # Select row 1
    dialog.table.selectRow(1)

    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
        dialog.delete_camera_row()

    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 0).text() == "1"


def test_camera_config_dialog_save_and_apply(qapp):
    from unittest.mock import MagicMock
    from src.domain.entities import Camera
    from src.presentation.dialogs.camera_config_dialog import CameraConfigDialog

    cams = [
        Camera(1, "Cam 1", "rtsp://test/1", "rtsp://test/1")
    ]
    mock_store = MagicMock()

    dialog = CameraConfigDialog(cams, camera_store=mock_store)

    signal_received = []
    dialog.cameras_updated.connect(lambda clist: signal_received.append(clist))

    # Edit row 0 name
    dialog.table.item(0, 1).setText("Renamed Cam 1")

    with patch.object(dialog, "accept"):
        dialog.save_and_apply()

    assert len(signal_received) == 1
    saved_list = signal_received[0]
    assert len(saved_list) == 1
    assert saved_list[0].id == 1
    assert saved_list[0].name == "Renamed Cam 1"
    mock_store.save_cameras.assert_called_once()


def test_camera_config_dialog_validation_duplicate_id(qapp):
    from PySide6.QtWidgets import QMessageBox
    from src.domain.entities import Camera
    from src.presentation.dialogs.camera_config_dialog import CameraConfigDialog

    cams = [
        Camera(1, "Cam 1", "rtsp://test/1", "rtsp://test/1")
    ]
    dialog = CameraConfigDialog(cams)
    dialog.add_camera_row()
    # Force duplicate ID
    dialog.table.item(1, 0).setText("1")

    with patch.object(QMessageBox, "warning") as mock_warn:
        dialog.save_and_apply()
        mock_warn.assert_called_once()


def test_connection_tester_thread_mock(qapp):
    from src.presentation.dialogs.camera_config_dialog import ConnectionTesterThread

    tester = ConnectionTesterThread("mock://test_feed")
    results = []
    tester.test_finished.connect(lambda ok, msg: results.append((ok, msg)))
    tester.run()

    assert len(results) == 1
    assert results[0][0] is True


def test_camera_config_dialog_cleanup_on_reject(qapp):
    from unittest.mock import MagicMock
    from src.domain.entities import Camera
    from src.presentation.dialogs.camera_config_dialog import CameraConfigDialog

    cams = [Camera(1, "Cam 1", "rtsp://test/1", "rtsp://test/1")]
    dialog = CameraConfigDialog(cams)

    mock_thread = MagicMock()
    mock_thread.isRunning.return_value = True
    dialog._tester_thread = mock_thread

    dialog.reject()
    mock_thread.wait.assert_called_once_with(500)

