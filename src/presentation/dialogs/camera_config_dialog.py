import logging
import os
from typing import List, Optional, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QHeaderView,
    QComboBox, QMessageBox, QAbstractItemView, QFrame
)
from PySide6.QtCore import Qt, Signal, QThread
from src.domain.entities import Camera
from src.core.camera_store import CameraStore

logger = logging.getLogger(__name__)


class ConnectionTesterThread(QThread):
    """Background thread to test RTSP stream connectivity without freezing UI."""
    test_finished = Signal(bool, str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        if not self.url or self.url.strip() == "":
            self.test_finished.emit(False, "URL RTSP kosong.")
            return

        # Fast path for offline mock
        if self.url.startswith("mock://"):
            self.test_finished.emit(True, "Feed simulasi (Mock) siap digunakan.")
            return

        try:
            import cv2
            # Force TCP transport with 3.0-second socket timeout and preserve max_delay (Resolves Review Finding 3)
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                "rtsp_transport;tcp|"
                "stimeout;3000000|"
                "max_delay;500000"
            )
            cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    h, w = frame.shape[:2]
                    self.test_finished.emit(True, f"Koneksi RTSP Berhasil!\nResolusi feed: {w}x{h}")
                else:
                    self.test_finished.emit(False, "Koneksi RTSP terbuka namun tidak ada frame yang diterima.")
            else:
                self.test_finished.emit(False, "Gagal terhubung ke RTSP feed (koneksi timeout atau ditolak).")
        except Exception as e:
            self.test_finished.emit(False, f"Terjadi kesalahan saat menguji RTSP:\n{e}")


class CameraConfigDialog(QDialog):
    """Modal dialog for full CRUD management of RTSP camera streams."""

    cameras_updated = Signal(list)  # Emitted when new camera configuration is saved

    def __init__(
        self,
        cameras: List[Camera],
        camera_store: Optional[CameraStore] = None,
        parent: Optional[QDialog] = None
    ):
        super().__init__(parent)
        self.cameras = [
            Camera(
                id=c.id,
                name=c.name,
                sub_stream_url=c.sub_stream_url,
                main_stream_url=c.main_stream_url,
                is_counter_target=c.is_counter_target
            )
            for c in cameras
        ]
        self.camera_store = camera_store
        self.saved_cameras: List[Camera] = []
        self._tester_thread: Optional[ConnectionTesterThread] = None

        self.setWindowTitle("Pengaturan & Kelola Kamera RTSP - ManyPlayer")
        self.resize(1020, 600)
        self.setMinimumSize(850, 480)
        self._apply_dark_theme()
        self._setup_ui()
        self._populate_table()

    def _apply_dark_theme(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #F8FAFC;
            }
            QTableWidget {
                background-color: #1E293B;
                color: #F8FAFC;
                gridline-color: #334155;
                border: 1px solid #334155;
                border-radius: 8px;
                selection-background-color: #0284C7;
                selection-color: #FFFFFF;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 6px;
            }
            QHeaderView::section {
                background-color: #0F172A;
                color: #94A3B8;
                padding: 8px;
                font-size: 12px;
                font-weight: bold;
                border: none;
                border-bottom: 2px solid #334155;
                border-right: 1px solid #1E293B;
            }
            QScrollBar:vertical {
                background-color: #0F172A;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #334155;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #475569;
            }
        """)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        title_label = QLabel("⚙️ Kelola Alamat RTSP Kamera")
        title_label.setStyleSheet("color: #38BDF8; font-size: 18px; font-weight: 900;")
        header_layout.addWidget(title_label)

        desc_label = QLabel("Atur URL Sub-Stream (tampilan grid) dan Main-Stream (AI People Counter). Perubahan akan langsung aktif secara seketika.")
        desc_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        header_layout.addWidget(desc_label)

        main_layout.addLayout(header_layout)

        # 2. Action Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.btn_add = QPushButton("➕ Tambah Kamera")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setStyleSheet(self._button_style(bg="#0284C7", hover="#0369A1", text="#FFFFFF"))
        self.btn_add.clicked.connect(self.add_camera_row)

        self.btn_delete = QPushButton("🗑️ Hapus Kamera")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setStyleSheet(self._button_style(bg="#DC2626", hover="#B91C1C", text="#FFFFFF"))
        self.btn_delete.clicked.connect(self.delete_camera_row)

        self.btn_test = QPushButton("🔍 Uji Koneksi RTSP")
        self.btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test.setStyleSheet(self._button_style(bg="#334155", hover="#475569", text="#38BDF8"))
        self.btn_test.clicked.connect(self.test_selected_connection)

        toolbar.addWidget(self.btn_add)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_test)

        toolbar.addStretch()

        self.lbl_summary = QLabel("Total: 0 kamera")
        self.lbl_summary.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: bold;")
        toolbar.addWidget(self.lbl_summary)

        main_layout.addLayout(toolbar)

        # 3. Main Cameras Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "ID Slot",
            "Nama Kamera / Lokasi",
            "Sub-Stream URL (Grid 16/25/36)",
            "Main-Stream URL (AI Counter)",
            "Kamera AI Counter"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setColumnWidth(1, 180)

        main_layout.addWidget(self.table, stretch=1)

        # 4. Bottom Footer Toolbar
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(12)

        footer_hint = QLabel("💡 Tip: Gunakan Sub-Stream ringan (e.g. 360p/720p) pada Grid agar hemat CPU/RAM.")
        footer_hint.setStyleSheet("color: #64748B; font-size: 11px;")
        footer_layout.addWidget(footer_hint)

        footer_layout.addStretch()

        self.btn_cancel = QPushButton("✖ Batal")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet(self._button_style(bg="#334155", hover="#475569", text="#E2E8F0"))
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("💾 Simpan & Terapkan")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(self._button_style(bg="#059669", hover="#047857", text="#FFFFFF"))
        self.btn_save.clicked.connect(self.save_and_apply)

        footer_layout.addWidget(self.btn_cancel)
        footer_layout.addWidget(self.btn_save)

        main_layout.addLayout(footer_layout)

    def _button_style(self, bg: str, hover: str, text: str) -> str:
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {text};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:disabled {{
                background-color: #1E293B;
                color: #64748B;
            }}
        """

    def _style_combobox(self, combo: QComboBox) -> None:
        combo.setStyleSheet("""
            QComboBox {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1E293B;
                color: #F8FAFC;
                selection-background-color: #0284C7;
            }
        """)

    def _populate_table(self) -> None:
        self.table.setRowCount(len(self.cameras))
        for row, cam in enumerate(self.cameras):
            # ID Item
            item_id = QTableWidgetItem(str(cam.id))
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, item_id)

            # Name Item
            item_name = QTableWidgetItem(cam.name)
            self.table.setItem(row, 1, item_name)

            # Sub-Stream URL
            item_sub = QTableWidgetItem(cam.sub_stream_url)
            self.table.setItem(row, 2, item_sub)

            # Main-Stream URL
            item_main = QTableWidgetItem(cam.main_stream_url)
            self.table.setItem(row, 3, item_main)

            # Counter Target Combobox
            combo = QComboBox()
            combo.addItems(["Tidak", "Cam 1", "Cam 2"])
            if cam.is_counter_target == "Cam 1":
                combo.setCurrentIndex(1)
            elif cam.is_counter_target == "Cam 2":
                combo.setCurrentIndex(2)
            else:
                combo.setCurrentIndex(0)
            self._style_combobox(combo)
            self.table.setCellWidget(row, 4, combo)

        self._update_summary_label()

    def _update_summary_label(self) -> None:
        count = self.table.rowCount()
        self.lbl_summary.setText(f"Total: {count} kamera")

    def add_camera_row(self) -> None:
        """Appends a new camera row with auto-incremented ID."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        existing_ids = []
        for r in range(row):
            item = self.table.item(r, 0)
            if item and item.text().strip().isdigit():
                existing_ids.append(int(item.text().strip()))

        next_id = max(existing_ids, default=0) + 1

        item_id = QTableWidgetItem(str(next_id))
        item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 0, item_id)

        item_name = QTableWidgetItem(f"Kamera {next_id:02d}")
        self.table.setItem(row, 1, item_name)

        item_sub = QTableWidgetItem(f"rtsp://192.168.1.{100 + next_id}:554/ch1/sub")
        self.table.setItem(row, 2, item_sub)

        item_main = QTableWidgetItem(f"rtsp://192.168.1.{100 + next_id}:554/ch1/main")
        self.table.setItem(row, 3, item_main)

        combo = QComboBox()
        combo.addItems(["Tidak", "Cam 1", "Cam 2"])
        combo.setCurrentIndex(0)
        self._style_combobox(combo)
        self.table.setCellWidget(row, 4, combo)

        self.table.selectRow(row)
        self._update_summary_label()

    def delete_camera_row(self) -> None:
        """Deletes currently selected camera row."""
        selected_indexes = self.table.selectedIndexes()
        if not selected_indexes:
            QMessageBox.information(self, "Hapus Kamera", "Pilih baris kamera yang ingin dihapus terlebih dahulu.")
            return

        row = selected_indexes[0].row()
        cam_name = self.table.item(row, 1).text() if self.table.item(row, 1) else f"Row {row+1}"

        reply = QMessageBox.question(
            self,
            "Konfirmasi Hapus Kamera",
            f"Apakah Anda yakin ingin menghapus kamera '{cam_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.table.removeRow(row)
            self._update_summary_label()

    def test_selected_connection(self) -> None:
        """Tests RTSP stream connection for the selected row."""
        selected_indexes = self.table.selectedIndexes()
        if not selected_indexes:
            QMessageBox.information(self, "Uji Koneksi", "Pilih salah satu baris kamera untuk menguji koneksi RTSP.")
            return

        row = selected_indexes[0].row()
        col = selected_indexes[0].column()

        # If user specifically selected column 3 (Main-Stream), test main stream (Resolves Audit Finding 7)
        if col == 3:
            item_main = self.table.item(row, 3)
            url = item_main.text().strip() if item_main else ""
            stream_label = "Main-Stream"
        else:
            item_sub = self.table.item(row, 2)
            url = item_sub.text().strip() if item_sub else ""
            stream_label = "Sub-Stream"
            # Fallback to main stream if sub is blank
            if not url:
                item_main = self.table.item(row, 3)
                url = item_main.text().strip() if item_main else ""
                if url:
                    stream_label = "Main-Stream"

        if not url:
            QMessageBox.warning(self, "Uji Koneksi", f"Alamat RTSP {stream_label} pada baris terpilih masih kosong.")
            return

        self.btn_test.setEnabled(False)
        self.btn_test.setText("⏳ Menguji...")

        self._tester_thread = ConnectionTesterThread(url)
        self._tester_thread.test_finished.connect(self._on_test_finished)
        self._tester_thread.start()

    def _on_test_finished(self, success: bool, message: str) -> None:
        self.btn_test.setEnabled(True)
        self.btn_test.setText("🔍 Uji Koneksi RTSP")

        if success:
            QMessageBox.information(self, "Uji Koneksi Berhasil", message)
        else:
            QMessageBox.warning(self, "Uji Koneksi Gagal", message)

    def _cleanup_tester_thread(self) -> None:
        """Safely detaches and waits for tester thread to prevent Qt runtime crashes (Resolves Review Finding 4)."""
        if self._tester_thread and self._tester_thread.isRunning():
            try:
                self._tester_thread.test_finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._tester_thread.wait(500)

    def reject(self) -> None:
        self._cleanup_tester_thread()
        super().reject()

    def closeEvent(self, event) -> None:
        self._cleanup_tester_thread()
        super().closeEvent(event)

    def save_and_apply(self) -> None:
        """Validates all inputs, saves to JSON file, and emits cameras_updated signal."""
        new_cameras: List[Camera] = []
        seen_ids = set()
        cam1_count = 0
        cam2_count = 0

        for r in range(self.table.rowCount()):
            # 1. Validate ID
            item_id = self.table.item(r, 0)
            id_str = item_id.text().strip() if item_id else ""
            if not id_str.isdigit() or int(id_str) <= 0:
                QMessageBox.warning(self, "Validasi Gagal", f"Baris {r+1}: ID harus berupa angka bulat positif (> 0).")
                return
            cam_id = int(id_str)
            if cam_id in seen_ids:
                QMessageBox.warning(self, "Validasi Gagal", f"Baris {r+1}: ID {cam_id} sudah digunakan. ID tidak boleh duplikat.")
                return
            seen_ids.add(cam_id)

            # 2. Validate Name
            item_name = self.table.item(r, 1)
            name = item_name.text().strip() if item_name else ""
            if not name:
                QMessageBox.warning(self, "Validasi Gagal", f"Baris {r+1}: Nama kamera tidak boleh kosong.")
                return

            # 3. Validate Sub-Stream URL
            item_sub = self.table.item(r, 2)
            sub_url = item_sub.text().strip() if item_sub else ""
            if not sub_url:
                QMessageBox.warning(self, "Validasi Gagal", f"Baris {r+1}: Sub-Stream URL tidak boleh kosong.")
                return

            # 4. Main-Stream URL (fallback to sub_url if empty)
            item_main = self.table.item(r, 3)
            main_url = item_main.text().strip() if item_main else ""
            if not main_url:
                main_url = sub_url

            # 5. Counter Target Combobox
            combo = self.table.cellWidget(r, 4)
            target = None
            if isinstance(combo, QComboBox):
                target_text = combo.currentText()
                if target_text == "Cam 1":
                    target = "Cam 1"
                    cam1_count += 1
                elif target_text == "Cam 2":
                    target = "Cam 2"
                    cam2_count += 1

            if cam1_count > 1:
                QMessageBox.warning(self, "Validasi Gagal", "Maksimal hanya 1 kamera yang dapat ditugaskan sebagai 'Cam 1'.")
                return
            if cam2_count > 1:
                QMessageBox.warning(self, "Validasi Gagal", "Maksimal hanya 1 kamera yang dapat ditugaskan sebagai 'Cam 2'.")
                return

            new_cameras.append(Camera(
                id=cam_id,
                name=name,
                sub_stream_url=sub_url,
                main_stream_url=main_url,
                is_counter_target=target
            ))

        new_cameras.sort(key=lambda c: c.id)

        # Save to persistent storage if available
        if self.camera_store is not None:
            try:
                self.camera_store.save_cameras(new_cameras)
                logger.info(f"Saved {len(new_cameras)} cameras to {self.camera_store.file_path}")
            except Exception as e:
                logger.error(f"Failed to save cameras configuration: {e}")
                QMessageBox.critical(self, "Gagal Menyimpan", f"Gagal menyimpan ke file konfigurasi:\n{e}")
                return

        self.saved_cameras = new_cameras
        self.cameras_updated.emit(new_cameras)
        self.accept()
