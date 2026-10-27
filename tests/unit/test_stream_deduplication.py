import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from src.domain.entities import Camera
from src.core.frame_store import SharedFrameStore
from src.core.stream_worker import StreamWorker
from src.core.worker_pool import StreamWorkerPool


def test_stream_worker_fan_out_delivery():
    """Tests that a single StreamWorker delivers frames to all subscribed camera IDs in SharedFrameStore."""
    frame_store = SharedFrameStore()
    worker = StreamWorker(
        camera_id=[1, 2, 3],
        stream_url="mock://test_stream",
        frame_store=frame_store
    )

    assert set(worker.get_camera_ids()) == {1, 2, 3}

    # Simulate delivering a frame
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    for cid in worker.get_camera_ids():
        frame_store.put_frame(cid, dummy_frame, is_online=True)

    f1 = frame_store.get_frame(1)
    f2 = frame_store.get_frame(2)
    f3 = frame_store.get_frame(3)

    assert f1 is not None and f1.shape == (100, 100, 3)
    assert f2 is not None and f2.shape == (100, 100, 3)
    assert f3 is not None and f3.shape == (100, 100, 3)


def test_stream_worker_pool_deduplication():
    """Tests that StreamWorkerPool deduplicates identical RTSP URLs into 1 physical worker."""
    frame_store = SharedFrameStore()
    pool = StreamWorkerPool(frame_store=frame_store, is_mock=False)

    # 16 cameras: 1-10 share URL A, 11-15 share URL B, 16 has URL C
    cameras_map = {}
    for i in range(1, 11):
        cameras_map[i] = Camera(i, f"Cam {i}", "rtsp://camera_a/stream")
    for i in range(11, 16):
        cameras_map[i] = Camera(i, f"Cam {i}", "rtsp://camera_b/stream")
    cameras_map[16] = Camera(16, "Cam 16", "rtsp://camera_c/stream")

    with patch("src.core.worker_pool.StreamWorker") as MockWorker:
        def make_mock(camera_id, stream_url, *args, **kwargs):
            mock = MagicMock()
            mock.stream_url = stream_url
            mock.camera_ids = set(camera_id) if isinstance(camera_id, (list, set)) else {camera_id}
            mock.get_camera_ids.return_value = list(mock.camera_ids)
            return mock

        MockWorker.side_effect = make_mock

        pool.set_active_cameras(list(range(1, 17)), cameras_map)

        # 16 camera slots active in pool
        assert pool.active_count == 16
        # Only 3 physical workers created for the 3 unique URLs
        assert pool.unique_worker_count == 3

        # Cameras 1 through 10 share the exact same worker instance
        worker_a = pool._workers[1]
        for cid in range(1, 11):
            assert pool._workers[cid] is worker_a

        # Cameras 11 through 15 share worker B
        worker_b = pool._workers[11]
        assert worker_b is not worker_a
        for cid in range(11, 16):
            assert pool._workers[cid] is worker_b

        # Camera 16 has unique worker C
        worker_c = pool._workers[16]
        assert worker_c is not worker_a and worker_c is not worker_b

    pool.stop_all()


def test_stream_worker_pool_single_camera_stop_and_resume():
    """Tests that stopping one camera does not terminate shared worker if other cameras still use it."""
    frame_store = SharedFrameStore()
    pool = StreamWorkerPool(frame_store=frame_store, is_mock=False)

    cam1 = Camera(1, "Cam 1", "rtsp://shared/stream")
    cam2 = Camera(2, "Cam 2", "rtsp://shared/stream")
    cameras_map = {1: cam1, 2: cam2}

    with patch("src.core.worker_pool.StreamWorker") as MockWorker:
        mock = MagicMock()
        mock.stream_url = "rtsp://shared/stream"
        mock.camera_ids = {1, 2}
        mock.get_camera_ids.side_effect = lambda: list(mock.camera_ids)
        mock.remove_camera_id.side_effect = lambda cid: mock.camera_ids.discard(cid)
        mock.add_camera_id.side_effect = lambda cid: mock.camera_ids.add(cid)
        MockWorker.return_value = mock

        pool.set_active_cameras([1, 2], cameras_map)
        assert pool.active_count == 2
        assert pool.unique_worker_count == 1

        # Stop Camera 1 independently
        pool.stop_camera_worker(1)
        assert pool.active_count == 1
        assert pool.unique_worker_count == 1
        mock.stop.assert_not_called()  # Worker still running for Camera 2!

        # Stop Camera 2 independently (now 0 cameras remaining)
        pool.stop_camera_worker(2)
        assert pool.active_count == 0
        assert pool.unique_worker_count == 0
        mock.stop.assert_called_once()  # Now physical worker stops cleanly!

    pool.stop_all()


def test_stream_worker_pool_start_camera_worker_reuses_existing():
    """Tests starting a camera worker dynamically attaches to an existing worker if URL matches."""
    frame_store = SharedFrameStore()
    pool = StreamWorkerPool(frame_store=frame_store, is_mock=False)

    cam1 = Camera(1, "Cam 1", "rtsp://shared/stream")
    cam2 = Camera(2, "Cam 2", "rtsp://shared/stream")

    with patch("src.core.worker_pool.StreamWorker") as MockWorker:
        mock = MagicMock()
        mock.stream_url = "rtsp://shared/stream"
        mock.camera_ids = {1}
        mock.get_camera_ids.side_effect = lambda: list(mock.camera_ids)
        mock.add_camera_id.side_effect = lambda cid: mock.camera_ids.add(cid)
        MockWorker.return_value = mock

        # Start Camera 1
        res1 = pool.start_camera_worker(1, cam1)
        assert res1 is True
        assert pool.unique_worker_count == 1

        # Start Camera 2 (same URL)
        res2 = pool.start_camera_worker(2, cam2)
        assert res2 is True
        # Reuses existing physical worker!
        assert pool.unique_worker_count == 1
        assert pool._workers[1] is pool._workers[2]
        mock.add_camera_id.assert_called_with(2)

    pool.stop_all()


def test_stream_worker_pool_dead_worker_recovery():
    """Tests that a worker whose thread has died is automatically evicted and restarted."""
    frame_store = SharedFrameStore()
    pool = StreamWorkerPool(frame_store=frame_store, is_mock=False)

    cam1 = Camera(1, "Cam 1", "rtsp://camera_drop/stream")
    cameras_map = {1: cam1}

    worker_instances = []

    with patch("src.core.worker_pool.StreamWorker") as MockWorker:
        def make_worker(camera_id, stream_url, *args, **kwargs):
            mock = MagicMock()
            mock.stream_url = stream_url
            mock.camera_ids = {camera_id} if isinstance(camera_id, int) else set(camera_id)
            mock.get_camera_ids.side_effect = lambda: list(mock.camera_ids)
            mock.is_alive.return_value = True
            worker_instances.append(mock)
            return mock

        MockWorker.side_effect = make_worker

        # 1. Start worker normally
        pool.set_active_cameras([1], cameras_map)
        assert pool.unique_worker_count == 1
        first_worker = worker_instances[0]
        assert pool._unique_workers["rtsp://camera_drop/stream"] is first_worker

        # 2. Simulate worker thread death (e.g. unhandled crash or drop)
        first_worker.is_alive.return_value = False

        # 3. Call set_active_cameras again - should detect dead worker and create a replacement
        pool.set_active_cameras([1], cameras_map)
        assert len(worker_instances) == 2
        second_worker = worker_instances[1]
        assert second_worker is not first_worker
        assert pool._unique_workers["rtsp://camera_drop/stream"] is second_worker

        # 4. Also test start_camera_worker with a dead worker in _unique_workers
        second_worker.is_alive.return_value = False
        pool._workers.clear()  # Detach slot 1 to simulate standalone start
        pool.start_camera_worker(1, cam1)
        assert len(worker_instances) == 3
        third_worker = worker_instances[2]
        assert third_worker is not second_worker
        assert pool._unique_workers["rtsp://camera_drop/stream"] is third_worker

    pool.stop_all()
