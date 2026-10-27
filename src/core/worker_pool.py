import logging
import threading
from typing import Dict, List, Set
from src.domain.entities import Camera
from src.core.frame_store import SharedFrameStore
from src.core.stream_worker import StreamWorker

logger = logging.getLogger(__name__)


class StreamWorkerPool:
    """Manages active RTSP stream worker threads with dynamic throttling and stream deduplication.
    
    Features:
    - Deduplication / Fan-out: When multiple cameras share the exact same RTSP URL, only 1 physical
      network connection is opened, and incoming frames are distributed across all matching camera slots.
    - Dynamic Throttling: Only cameras currently visible on screen have running streams.
    - Zero Bandwidth Waste: Prevents breaching IP camera hardware connection limits (e.g. Hikvision 453).
    """

    def __init__(self, frame_store: SharedFrameStore, target_fps: int = 15, is_mock: bool = False):
        self.frame_store = frame_store
        self.target_fps = target_fps
        self.is_mock = is_mock
        self._workers: Dict[int, StreamWorker] = {}
        self._unique_workers: Dict[str, StreamWorker] = {}

    def set_active_cameras(
        self,
        active_camera_ids: List[int],
        cameras_map: Dict[int, Camera],
        is_main_stream: bool = False
    ) -> None:
        """Dynamically adjusts running workers to match the currently visible camera set with deduplication."""
        if self.is_mock:
            return

        # 1. Group active camera IDs by desired stream URL
        desired_url_to_cids: Dict[str, Set[int]] = {}
        for cid in active_camera_ids:
            cam = cameras_map.get(cid)
            if not cam:
                continue
            url = cam.get_stream_url(is_main=is_main_stream)
            if not url or not url.strip():
                continue
            if url not in desired_url_to_cids:
                desired_url_to_cids[url] = set()
            desired_url_to_cids[url].add(cid)

        # 2. Stop workers for URLs that are no longer requested
        current_urls = set(self._unique_workers.keys())
        desired_urls = set(desired_url_to_cids.keys())

        for url in (current_urls - desired_urls):
            worker = self._unique_workers.pop(url, None)
            if worker:
                logger.info(f"Throttling: Stopping worker for unused URL: {url}")
                worker.stop()

        # 3. Check existing workers: if dead, evict to trigger a restart; otherwise update IDs
        for url in list(current_urls & desired_urls):
            worker = self._unique_workers[url]
            if not worker.is_alive():
                logger.warning(f"Throttling: Worker for {url} is dead. Evicting for restart...")
                self._unique_workers.pop(url, None)
                current_urls.discard(url)
            else:
                worker.set_camera_ids(desired_url_to_cids[url])

        # 4. Start new workers for newly requested (or revived dead) URLs
        for url in (desired_urls - current_urls):
            cids = desired_url_to_cids[url]
            logger.info(f"Throttling: Starting shared StreamWorker for cameras {sorted(cids)} -> {url}")
            worker = StreamWorker(
                camera_id=sorted(cids),
                stream_url=url,
                frame_store=self.frame_store,
                target_fps=self.target_fps
            )
            worker.start()
            self._unique_workers[url] = worker

        # 5. Rebuild camera_id to worker mapping
        self._workers.clear()
        for url, cids in desired_url_to_cids.items():
            worker = self._unique_workers.get(url)
            if worker:
                for cid in cids:
                    self._workers[cid] = worker

    def stop_camera_worker(self, camera_id: int) -> None:
        """Stops streaming for a single camera independently."""
        worker = self._workers.pop(camera_id, None)
        if not worker:
            return

        worker.remove_camera_id(camera_id)
        self.frame_store.clear_camera(camera_id)
        logger.info(f"Camera {camera_id} detached from stream {worker.stream_url}.")

        # If no other camera is using this stream, stop the physical worker
        if not worker.get_camera_ids():
            logger.info(f"No cameras remaining for {worker.stream_url}. Stopping worker.")
            self._unique_workers.pop(worker.stream_url, None)
            worker.stop()
            if worker.is_alive() and threading.current_thread() != worker:
                worker.join(timeout=0.5)

    def start_camera_worker(
        self,
        camera_id: int,
        camera: Camera,
        is_main_stream: bool = False
    ) -> bool:
        """Starts streaming for a single camera independently, reusing existing stream if available."""
        if self.is_mock:
            return True

        if camera_id in self._workers:
            existing_w = self._workers[camera_id]
            if existing_w.is_alive() and camera_id in existing_w.get_camera_ids():
                return True
            self._workers.pop(camera_id, None)

        url = camera.get_stream_url(is_main=is_main_stream)
        if not url or not url.strip():
            logger.warning(f"Cannot start worker for Camera {camera_id}: URL is empty.")
            return False

        if url in self._unique_workers:
            worker = self._unique_workers[url]
            if worker.is_alive():
                # Attach to existing shared worker (Instant start, 0 network reconnect!)
                worker.add_camera_id(camera_id)
                self._workers[camera_id] = worker
                logger.info(f"Camera {camera_id} attached to existing active worker for {url}.")
                return True
            else:
                logger.warning(f"Existing worker for {url} is dead. Evicting and restarting...")
                dead_w = self._unique_workers.pop(url, None)
                if dead_w and dead_w.is_alive() and threading.current_thread() != dead_w:
                    dead_w.join(timeout=0.3)

        # Otherwise launch a new worker for this URL
        logger.info(f"Starting new worker for Camera {camera_id} -> {url}")
        worker = StreamWorker(
            camera_id=camera_id,
            stream_url=url,
            frame_store=self.frame_store,
            target_fps=self.target_fps
        )
        worker.start()
        self._unique_workers[url] = worker
        self._workers[camera_id] = worker
        return True

    def is_worker_running(self, camera_id: int) -> bool:
        """Checks if a worker thread is running and feeding the given camera ID."""
        worker = self._workers.get(camera_id)
        return worker is not None and worker.is_alive() and camera_id in worker.get_camera_ids()

    def stop_all(self, timeout: float = 0.3) -> None:
        """Stops all running camera workers cleanly and waits for threads to terminate."""
        logger.info(f"Stopping all {len(self._unique_workers)} active unique stream workers...")
        workers = list(self._unique_workers.values())
        for worker in workers:
            worker.stop()
        for worker in workers:
            if worker.is_alive() and threading.current_thread() != worker:
                worker.join(timeout=timeout)
        self._unique_workers.clear()
        self._workers.clear()
        self.frame_store.clear()

    @property
    def active_count(self) -> int:
        """Returns the number of camera slots actively receiving streams."""
        return len(self._workers)

    @property
    def unique_worker_count(self) -> int:
        """Returns the number of actual physical network stream workers running."""
        return len(self._unique_workers)
