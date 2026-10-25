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
        self._mock_active_ids: Set[int] = set()

    def set_active_cameras(
        self,
        active_camera_ids: List[int],
        cameras_map: Dict[int, Camera],
        is_main_stream: bool = False
    ) -> None:
        """Dynamically adjusts running workers to match the currently visible camera set."""
        if self.is_mock:
            self._mock_active_ids = set(active_camera_ids)
            return

        target_ids: Set[int] = set(active_camera_ids)
        current_ids: Set[int] = set(self._workers.keys())

        # Stop workers for cameras that are no longer visible
        to_stop = current_ids - target_ids
        for cid in to_stop:
            worker = self._workers.pop(cid, None)
            if worker:
                logger.info(f"Throttling: Stopping worker for invisible Camera {cid}")
                worker.stop()

        # Start workers for newly visible cameras
        to_start = target_ids - current_ids
        for cid in to_start:
            cam = cameras_map.get(cid)
            if not cam:
                continue

            url = cam.get_stream_url(is_main=is_main_stream)
            logger.info(f"Throttling: Starting worker for visible Camera {cid} -> {url}")
            worker = StreamWorker(
                camera_id=cid,
                stream_url=url,
                frame_store=self.frame_store,
                target_fps=self.target_fps
            )
            worker.start()
            self._workers[cid] = worker

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
