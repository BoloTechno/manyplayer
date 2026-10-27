import sys
import os

# Automatically add project root to Python search path so `python src/main.py` works out of the box
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# If launched by system python without dependencies, auto-delegate to local .venv
try:
    import PySide6
except ImportError:
    venv_python = (
        os.path.join(project_root, ".venv", "Scripts", "python.exe")
        if sys.platform == "win32"
        else os.path.join(project_root, ".venv", "bin", "python")
    )
    if os.path.isfile(venv_python) and sys.executable != venv_python:
        os.execv(venv_python, [venv_python] + sys.argv)

import logging
from PySide6.QtWidgets import QApplication
from src.core.camera_store import CameraStore
from src.core.frame_store import SharedFrameStore
from src.core.worker_pool import StreamWorkerPool
from src.presentation.main_window import MainWindow

# Configure clean logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(threadName)s) %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("ManyPlayer")


def main() -> None:
    """Composition Root: Assembles dependencies and launches the Windows desktop application."""
    logger.info("Initializing ManyPlayer Desktop Application...")

    use_mock = "--mock" in sys.argv

    # 1. Load Camera Configuration (handles PyInstaller standalone deployment)
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "cameras.json")
    camera_store = CameraStore(config_path)
    cameras = camera_store.load_cameras()
    logger.info(f"Loaded {len(cameras)} camera configurations from {config_path}")

    # 2. Initialize Shared Storage and Worker Pool
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, target_fps=15, is_mock=use_mock)
    cameras_holder = [cameras]

    # If --mock flag is passed, run offline simulation feeder
    if use_mock:
        logger.info("Running in SIMULATION MODE (--mock): Generating synthetic camera feeds...")
        import threading
        import time
        from tests.mock_stream import MockFrameGenerator

        mock_gen = MockFrameGenerator()

        def mock_feeder_loop():
            while True:
                # Generate frames for all currently configured cameras
                for c in cameras_holder[0]:
                    frame = mock_gen.generate_grid_frame(c.id, c.name)
                    frame_store.put_frame(c.id, frame, is_online=True)
                time.sleep(1.0 / 15.0)

        feeder_thread = threading.Thread(target=mock_feeder_loop, daemon=True, name="MockFeeder")
        feeder_thread.start()

    # 3. Initialize Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("ManyPlayer")
    app.setOrganizationName("BoloTechno")
    app.setOrganizationDomain("BoloTechno.com")

    icon_path = os.path.join(base_dir, "assets", "logo.png")
    if os.path.isfile(icon_path):
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(icon_path))

    # 4. Construct and Show Main Window
    window = MainWindow(
        cameras=cameras,
        frame_store=frame_store,
        worker_pool=worker_pool,
        camera_store=camera_store
    )

    if use_mock:
        # Keep mock feeder synchronized cleanly via Qt Signal (Resolves Audit Finding 6)
        def update_mock_cameras(new_cams):
            cameras_holder[0] = new_cams
        window.cameras_changed.connect(update_mock_cameras)

    window.showMaximized()

    logger.info("ManyPlayer UI started successfully.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
