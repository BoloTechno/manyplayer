import os
import time
import logging
import threading
from typing import Optional
from src.core.frame_store import SharedFrameStore

logger = logging.getLogger(__name__)

# Enforce OpenCV FFmpeg RTSP options globally: TCP mode + 5 second socket timeout
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|"      # Use TCP to prevent UDP packet loss and grey screens
    "stimeout;5000000|"        # Socket timeout in microseconds: 5,000,000 us = 5 seconds
    "max_delay;500000"         # Maximum buffering delay: 0.5s for true real-time streaming
)


class StreamWorker(threading.Thread):
    """Background worker thread that ingests an RTSP stream and updates the SharedFrameStore.
    
    Features:
    - Zero Latency: Reads packets continuously without sleeping to prevent buffer bloat.
    - Anti-Hang: 5-second socket timeout prevents thread blocking on disconnect.
    - Auto-reconnect: Automatically retries connection if stream drops.
    """

    def __init__(
        self,
        camera_id: int,
        stream_url: str,
        frame_store: SharedFrameStore,
        target_fps: int = 15,
        reconnect_interval_sec: float = 5.0
    ):
        super().__init__(daemon=True, name=f"StreamWorker-{camera_id}")
        self.camera_id = camera_id
        self.stream_url = stream_url
        self.frame_store = frame_store
        self.target_fps = target_fps
        self.reconnect_interval_sec = reconnect_interval_sec
        self._running = False
        self._cap = None

    def run(self) -> None:
        """Main streaming loop."""
        import cv2

        self._running = True
        logger.info(f"StreamWorker {self.camera_id} started for: {self.stream_url}")

        while self._running:
            self.frame_store.put_frame(self.camera_id, frame=None, is_online=False)
            logger.info(f"Connecting Camera {self.camera_id} to {self.stream_url}...")

            # OpenCV VideoCapture with TCP & timeout options
            self._cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
            if not self._cap or not self._cap.isOpened():
                logger.warning(f"Camera {self.camera_id} connection failed. Retrying in {self.reconnect_interval_sec}s...")
                self._safe_sleep(self.reconnect_interval_sec)
                continue

            logger.info(f"Camera {self.camera_id} connected successfully.")

            # Frame ingestion loop: read continuously to drain network socket buffer immediately
            while self._running:
                ret, frame = self._cap.read()
                if not ret or frame is None:
                    logger.warning(f"Camera {self.camera_id} stream lost or read timed out.")
                    break

                # Overwrite latest frame in shared memory immediately (Zero Latency)
                self.frame_store.put_frame(self.camera_id, frame=frame, is_online=True)

            # Cleanup connection before reconnecting or exiting
            self._release_capture()
            if self._running:
                self.frame_store.put_frame(self.camera_id, frame=None, is_online=False)
                self._safe_sleep(self.reconnect_interval_sec)

        self._release_capture()
        logger.info(f"StreamWorker {self.camera_id} stopped cleanly.")

    def stop(self) -> None:
        """Requests graceful shutdown of the worker thread."""
        self._running = False
        self._release_capture()

    def _release_capture(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

    def _safe_sleep(self, seconds: float) -> None:
        """Sleeps in short slices so stop() is responsive."""
        end_time = time.time() + seconds
        while self._running and time.time() < end_time:
            time.sleep(0.1)
