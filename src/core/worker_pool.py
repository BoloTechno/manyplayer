import logging
from typing import Dict, List, Set
from src.domain.entities import Camera
from src.core.frame_store import SharedFrameStore
from src.core.stream_worker import StreamWorker

logger = logging.getLogger(__name__)


class StreamWorkerPool:
    """Manages active RTSP stream worker threads with dynamic throttling.
    
    Ensures that only cameras currently visible on screen (e.g. 16, 25, or 36)
    have running threads, conserving CPU and bandwidth.
    """

    def __init__(self, frame_store: SharedFrameStore, target_fps: int = 15, is_mock: bool = False):
        self.frame_store = frame_store
        self.target_fps = target_fps
        self.is_mock = is_mock
        self._workers: Dict[int, StreamWorker] = {}

    def set_active_cameras(
        self,
        active_camera_ids: List[int],
        cameras_map: Dict[int, Camera],
        is_main_stream: bool = False
    ) -> None:
        """Dynamically adjusts running workers to match the currently visible camera set."""
        if self.is_mock:
            return

        target_ids: Set[int] = set(active_camera_ids)
        current_ids: Set[int] = set(self._workers.keys())

        # Check for active cameras whose RTSP URL has changed
        url_changed_ids: Set[int] = set()
        for cid in current_ids.intersection(target_ids):
            cam = cameras_map.get(cid)
            worker = self._workers.get(cid)
            if cam and worker:
                expected_url = cam.get_stream_url(is_main=is_main_stream)
                if worker.stream_url != expected_url:
                    url_changed_ids.add(cid)

        # Stop workers for cameras that are no longer visible OR whose URL changed
        to_stop = (current_ids - target_ids) | url_changed_ids
        for cid in to_stop:
            worker = self._workers.pop(cid, None)
            if worker:
                logger.info(f"Throttling: Stopping worker for Camera {cid} (URL changed or invisible)")
                worker.stop()

        # Start workers for newly visible cameras OR cameras whose URL changed
        to_start = (target_ids - current_ids) | url_changed_ids
        for cid in to_start:
            cam = cameras_map.get(cid)
            if not cam:
                continue

            url = cam.get_stream_url(is_main=is_main_stream)
            if not url or not url.strip():
                logger.debug(f"Throttling: Skipping Camera {cid} (URL is empty)")
                continue

            logger.info(f"Throttling: Starting worker for Camera {cid} -> {url}")
            worker = StreamWorker(
                camera_id=cid,
                stream_url=url,
                frame_store=self.frame_store,
                target_fps=self.target_fps
            )
            worker.start()
            self._workers[cid] = worker

    def stop_camera_worker(self, camera_id: int) -> None:
        """Stops worker for a single camera independently."""
        worker = self._workers.pop(camera_id, None)
        if worker:
            logger.info(f"Stopping worker for Camera {camera_id} independently.")
            worker.stop()

    def start_camera_worker(
        self,
        camera_id: int,
        camera: Camera,
        is_main_stream: bool = False
    ) -> bool:
        """Starts worker for a single camera independently if not already running."""
        if self.is_mock or camera_id in self._workers:
            return False

        url = camera.get_stream_url(is_main=is_main_stream)
        if not url or not url.strip():
            logger.warning(f"Cannot start worker for Camera {camera_id}: URL is empty.")
            return False

        logger.info(f"Starting independent worker for Camera {camera_id} -> {url}")
        worker = StreamWorker(
            camera_id=camera_id,
            stream_url=url,
            frame_store=self.frame_store,
            target_fps=self.target_fps
        )
        worker.start()
        self._workers[camera_id] = worker
        return True

    def is_worker_running(self, camera_id: int) -> bool:
        """Checks if a worker thread is running for the given camera ID."""
        worker = self._workers.get(camera_id)
        return worker is not None and worker.is_alive()

    def stop_all(self) -> None:
        """Stops all running camera workers cleanly."""
        logger.info(f"Stopping all {len(self._workers)} active stream workers...")
        for cid, worker in list(self._workers.items()):
            worker.stop()
        self._workers.clear()
        self.frame_store.clear()

    @property
    def active_count(self) -> int:
        return len(self._workers)
