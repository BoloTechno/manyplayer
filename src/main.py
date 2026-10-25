import sys
import os
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

    # 1. Load Camera Configuration
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "cameras.json")
    camera_store = CameraStore(config_path)
    cameras = camera_store.load_cameras()
    logger.info(f"Loaded {len(cameras)} camera configurations from {config_path}")

    # 2. Initialize Shared Storage and Worker Pool
    frame_store = SharedFrameStore()
    worker_pool = StreamWorkerPool(frame_store=frame_store, target_fps=15, is_mock=use_mock)

    # If --mock flag is passed, run offline simulation feeder
    if use_mock:
        logger.info("Running in SIMULATION MODE (--mock): Generating synthetic camera feeds...")
        import threading
        import time
        from tests.mock_stream import MockFrameGenerator

        mock_gen = MockFrameGenerator()

        def mock_feeder_loop():
            while True:
                # Generate frames for all 36 cameras
                for c in cameras:
                    if c.is_counter_target:
                        frame, _ = mock_gen.generate_person_crossing_frame(c.name)
                    else:
                        frame = mock_gen.generate_grid_frame(c.id, c.name)
                    frame_store.put_frame(c.id, frame, is_online=True)
                time.sleep(1.0 / 15.0)

        feeder_thread = threading.Thread(target=mock_feeder_loop, daemon=True, name="MockFeeder")
        feeder_thread.start()

    # 3. Initialize Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("ManyPlayer")
    app.setOrganizationName("ManyPlayer")

    # 4. Construct and Show Main Window
    window = MainWindow(
        cameras=cameras,
        frame_store=frame_store,
        worker_pool=worker_pool
    )
    window.show()

    logger.info("ManyPlayer UI started successfully.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
