import logging
from typing import List, Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from src.domain.entities import Camera
from src.core.camera_store import CameraStore
from src.core.frame_store import SharedFrameStore
from src.core.worker_pool import StreamWorkerPool
from src.presentation.grid_view import GridView
from src.presentation.counter_view import CounterView
from src.presentation.dialogs.camera_config_dialog import CameraConfigDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main Application Window implementing clean tab navigation and state decoupling."""

    cameras_changed = Signal(list)  # Emitted when cameras configuration is modified live

    def __init__(
        self,
        cameras: List[Camera],
        frame_store: SharedFrameStore,
        worker_pool: StreamWorkerPool,
        camera_store: Optional[CameraStore] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.cameras = cameras
        self.frame_store = frame_store
        self.worker_pool = worker_pool
        self.camera_store = camera_store or CameraStore()

        self.setWindowTitle("ManyPlayer - CCTV Video Wall & AI People Counter")
        self.setStyleSheet("background-color: #0F172A; color: #F8FAFC;")

        # Responsive sizing according to primary screen work area
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_w = min(1280, int(avail.width() * 0.95))
            target_h = min(720, int(avail.height() * 0.92))
            self.resize(target_w, target_h)
            pos_x = avail.x() + (avail.width() - target_w) // 2
            pos_y = avail.y() + (avail.height() - target_h) // 2
            self.move(pos_x, pos_y)
        else:
            self.resize(1024, 600)

        self.setMinimumSize(700, 450)

        self._setup_ui()
        self.switch_to_tab(0)  # Start on Tab 0 (Grid Monitor)

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Global Navigation Bar (Compact & Responsive)
        self.navbar = QFrame()
        self.navbar.setFixedHeight(46)
        self.navbar.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border-bottom: 2px solid #334155;
            }
        """)
        nav_layout = QHBoxLayout(self.navbar)
        nav_layout.setContentsMargins(12, 6, 12, 6)
        nav_layout.setSpacing(8)

        # Application Logo / Title
        app_title = QLabel("MANYPLAYER")
        app_title.setStyleSheet("color: #38BDF8; font-size: 14px; font-weight: 900; letter-spacing: 1px;")
        nav_layout.addWidget(app_title)

        nav_layout.addSpacing(10)

        # Tab Navigation Buttons
        self.btn_tab_grid = QPushButton("📹 GRID MONITOR")
        self.btn_tab_counter = QPushButton("👥 PEOPLE COUNTER")

        for btn in (self.btn_tab_grid, self.btn_tab_counter):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #94A3B8;
                    border: none;
                    border-radius: 6px;
                    padding: 0 12px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #334155;
                    color: #FFFFFF;
                }
                QPushButton:checked {
                    background-color: #0284C7;
                    color: #FFFFFF;
                }
            """)

        self.btn_tab_grid.clicked.connect(lambda: self.switch_to_tab(0))
        self.btn_tab_counter.clicked.connect(lambda: self.switch_to_tab(1))

        nav_layout.addWidget(self.btn_tab_grid)
        nav_layout.addWidget(self.btn_tab_counter)

        nav_layout.addStretch()

        # Fullscreen Toggle Button
        self.btn_fullscreen = QPushButton("⛶ FULLSCREEN")
        self.btn_fullscreen.setToolTip("Mode Layar Penuh (F11)")
        self.btn_fullscreen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fullscreen.setFixedHeight(32)
        self.btn_fullscreen.setStyleSheet("""
            QPushButton {
                background-color: #0F766E;
                color: #2DD4BF;
                border: 1px solid #14B8A6;
                border-radius: 6px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0D9488;
                color: #FFFFFF;
            }
        """)
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        nav_layout.addWidget(self.btn_fullscreen)

        # Camera Management Button
        self.btn_manage_cameras = QPushButton("⚙️ KELOLA KAMERA")
        self.btn_manage_cameras.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_manage_cameras.setFixedHeight(32)
        self.btn_manage_cameras.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #38BDF8;
                border: 1px solid #0284C7;
                border-radius: 6px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0284C7;
                color: #FFFFFF;
            }
        """)
        self.btn_manage_cameras.clicked.connect(self.open_camera_management_dialog)
        nav_layout.addWidget(self.btn_manage_cameras)

        nav_layout.addSpacing(6)

        # System Status Pill
        self.status_pill = QLabel("● AKTIF")
        self.status_pill.setStyleSheet("color: #4ADE80; font-size: 10px; font-weight: bold; padding-right: 4px;")
        nav_layout.addWidget(self.status_pill)

        root_layout.addWidget(self.navbar)

        # 2. Main Stacked Pages
        self.stack = QStackedWidget(self)

        # Page 0: Grid View (Menu 1)
        self.grid_view = GridView(self.cameras, self.frame_store, self.worker_pool, parent=self)
        self.grid_view.fullscreen_requested.connect(self.toggle_fullscreen)
        self.stack.addWidget(self.grid_view)

        # Page 1: Counter View (Menu 2)
        self.counter_view = CounterView(self.cameras, self.frame_store, self.worker_pool, parent=self)
        self.stack.addWidget(self.counter_view)

        root_layout.addWidget(self.stack, stretch=1)

    def switch_to_tab(self, index: int) -> None:
        """Switches active page with strict resource decoupling."""
        self.stack.setCurrentIndex(index)

        if index == 0:
            # Menu 1 Active: Multi-Grid Monitor
            self.btn_tab_grid.setChecked(True)
            self.btn_tab_counter.setChecked(False)

            # Suspend AI processing to guarantee 0% AI CPU load during 36-cam grid
            self.counter_view.pause_analytics()
            # Resume Grid rendering & camera workers
            self.grid_view.resume_rendering()
            logger.info("Switched to Tab 1: Multi-Grid Monitor (AI paused).")

        elif index == 1:
            # Menu 2 Active: People Counter
            self.btn_tab_grid.setChecked(False)
            self.btn_tab_counter.setChecked(True)

            # Pause grid rendering & stop 36 grid workers
            self.grid_view.pause_rendering()
            # Activate AI analytics for the 1 or 2 selected counter cameras
            self.counter_view.activate_analytics()
            logger.info("Switched to Tab 2: People Counter (Grid workers throttled).")

    def open_camera_management_dialog(self) -> None:
        """Opens modal dialog for managing RTSP camera streams."""
        dialog = CameraConfigDialog(self.cameras, camera_store=self.camera_store, parent=self)
        dialog.cameras_updated.connect(self.on_cameras_updated)
        dialog.exec()

    def on_cameras_updated(self, new_cameras: List[Camera]) -> None:
        """Handles live update of cameras configuration without restarting the application."""
        self.cameras = new_cameras
        self.grid_view.update_cameras(new_cameras)
        self.counter_view.update_cameras(new_cameras)
        self.cameras_changed.emit(new_cameras)
        logger.info(f"Live camera configuration updated: {len(new_cameras)} cameras registered.")

    def toggle_fullscreen(self) -> None:
        """Toggles between fullscreen and normal/maximized windowed mode."""
        if self.isFullScreen():
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    def enter_fullscreen(self) -> None:
        """Enters fullscreen mode with navbar hidden for pure 100% video wall screen area."""
        self.navbar.setVisible(False)
        self.showFullScreen()
        self.btn_fullscreen.setText("🗗 NORMAL")
        self.grid_view.set_fullscreen_state(True)
        logger.info("Entered Fullscreen mode (Navbar hidden).")

    def exit_fullscreen(self) -> None:
        """Exits fullscreen mode and restores normal/maximized window and navbar."""
        self.navbar.setVisible(True)
        self.showMaximized()
        self.btn_fullscreen.setText("⛶ FULLSCREEN")
        self.grid_view.set_fullscreen_state(False)
        logger.info("Exited Fullscreen mode (Navbar restored).")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Global key event handler for ESC (tiered restore) and F11 (fullscreen toggle)."""
        if event.key() == Qt.Key.Key_Escape:
            # Tier 1: If camera is maximized in GridView, first restore to multi-grid
            if self.stack.currentIndex() == 0 and self.grid_view.maximized_cam_id is not None:
                self.grid_view.restore_grid()
                event.accept()
                return

            # Tier 2: If in Fullscreen mode, restore normal window and navbar
            if self.isFullScreen():
                self.exit_fullscreen()
                event.accept()
                return

        elif event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
            event.accept()
            return

        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        """Handles graceful application shutdown on Windows."""
        logger.info("Shutting down ManyPlayer application...")
        self.grid_view.pause_rendering()
        self.counter_view.pause_analytics()
        self.worker_pool.stop_all()
        event.accept()
