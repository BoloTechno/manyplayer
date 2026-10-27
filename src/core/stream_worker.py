import os
import time
import logging
import threading
from typing import Optional
import cv2
from src.core.frame_store import SharedFrameStore
from src.core.rtsp_bridge import RTSPStreamBridge

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
    - Fan-out / Deduplication: Capable of publishing frames to multiple camera IDs simultaneously.
    - Zero Latency: Reads packets continuously without sleeping to prevent buffer bloat.
    - Anti-Hang: 5-second socket timeout prevents thread blocking on disconnect.
    - Auto-reconnect: Automatically retries connection if stream drops.
    """

    def __init__(
        self,
        camera_id: int | list | set,
        stream_url: str,
        frame_store: SharedFrameStore,
        target_fps: int = 15,
        reconnect_interval_sec: float = 5.0
    ):
        if isinstance(camera_id, (list, set, tuple)):
            self.camera_ids = set(camera_id)
            self.camera_id = min(self.camera_ids) if self.camera_ids else 0
        else:
            self.camera_id = camera_id
            self.camera_ids = {camera_id}

        super().__init__(daemon=True, name=f"StreamWorker-{self.camera_id}")
        self.stream_url = stream_url
        self.frame_store = frame_store
        self.reconnect_interval_sec = reconnect_interval_sec
        self._cam_lock = threading.Lock()
        self._running = False
        self._cap = None
        self._bridge = None
        self._latest_frame = None

    def add_camera_id(self, camera_id: int) -> None:
        """Adds a camera ID to receive frames from this stream."""
        with self._cam_lock:
            self.camera_ids.add(camera_id)
            if self._latest_frame is not None:
                self.frame_store.put_frame(camera_id, frame=self._latest_frame, is_online=True)

    def remove_camera_id(self, camera_id: int) -> None:
        """Removes a camera ID from receiving frames."""
        with self._cam_lock:
            self.camera_ids.discard(camera_id)

    def set_camera_ids(self, camera_ids: set) -> None:
        """Sets the active set of camera IDs."""
        with self._cam_lock:
            self.camera_ids = set(camera_ids)
            if self.camera_ids:
                self.camera_id = min(self.camera_ids)
            if self._latest_frame is not None:
                for cid in self.camera_ids:
                    self.frame_store.put_frame(cid, frame=self._latest_frame, is_online=True)

    def get_camera_ids(self) -> list:
        """Returns snapshot of current camera IDs subscribed to this stream."""
        with self._cam_lock:
            return list(self.camera_ids)

    def run(self) -> None:
        """Main streaming loop with fan-out to all subscribed camera IDs."""
        self._running = True
        self._bridge, target_url = RTSPStreamBridge.create_if_needed(self.stream_url)
        logger.info(f"StreamWorker started for cameras {self.get_camera_ids()} -> {self.stream_url}")

        try:
            while self._running:
                subscribed = self.get_camera_ids()
                if not subscribed:
                    logger.info(f"StreamWorker for {self.stream_url} has no active cameras, exiting.")
                    break

                for cid in subscribed:
                    self.frame_store.put_frame(cid, frame=None, is_online=False)

                logger.info(f"Connecting StreamWorker (Cameras: {subscribed}) to {self.stream_url}...")

                # OpenCV VideoCapture with TCP & timeout options (using sanitized URL if bridged)
                self._cap = cv2.VideoCapture(target_url, cv2.CAP_FFMPEG)
                if not self._cap or not self._cap.isOpened():
                    logger.warning(f"Cameras {subscribed} connection failed. Retrying in {self.reconnect_interval_sec}s...")
                    self._safe_sleep(self.reconnect_interval_sec)
                    continue

                logger.info(f"Cameras {subscribed} connected successfully.")

                # Frame ingestion loop: read continuously to drain network socket buffer immediately
                while self._running:
                    subscribed = self.get_camera_ids()
                    if not subscribed:
                        break

                    ret, frame = self._cap.read()
                    if not ret or frame is None:
                        logger.warning(f"Cameras {subscribed} stream lost or read timed out.")
                        break

                    self._latest_frame = frame
                    # Overwrite latest frame in shared memory for ALL subscribed camera IDs (Zero Latency)
                    for cid in subscribed:
                        self.frame_store.put_frame(cid, frame=frame, is_online=True)

                # Cleanup connection before reconnecting or exiting
                self._release_capture()
                if self._running:
                    for cid in self.get_camera_ids():
                        self.frame_store.put_frame(cid, frame=None, is_online=False)
                    self._safe_sleep(self.reconnect_interval_sec)
        except Exception as e:
            logger.error(f"Unexpected error in StreamWorker for {self.stream_url}: {e}", exc_info=True)
        finally:
            self._release_capture()
            bridge = self._bridge
            self._bridge = None
            if bridge is not None:
                bridge.close()
            logger.info(f"StreamWorker for {self.stream_url} stopped cleanly.")

    def stop(self) -> None:
        """Requests graceful shutdown of the worker thread.
        
        Capture release is performed safely on the worker's own thread to prevent
        cross-thread OpenCV segmentation faults.
        """
        self._running = False
        bridge = self._bridge
        self._bridge = None
        if bridge is not None:
            bridge.close()

    def _release_capture(self) -> None:
        self._latest_frame = None
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
