from unittest.mock import MagicMock, patch
from src.domain.entities import Camera
from src.core.frame_store import SharedFrameStore
from src.core.worker_pool import StreamWorkerPool


def test_worker_pool_reloads_on_url_change():
    frame_store = SharedFrameStore()
    pool = StreamWorkerPool(frame_store=frame_store, is_mock=False)

    cam1_v1 = Camera(1, "Cam 1", "rtsp://old_url/stream")
    cam1_v2 = Camera(1, "Cam 1", "rtsp://new_url/stream")

    with patch("src.core.worker_pool.StreamWorker") as MockWorker:
        worker_v1 = MagicMock()
        worker_v1.stream_url = "rtsp://old_url/stream"

        worker_v2 = MagicMock()
        worker_v2.stream_url = "rtsp://new_url/stream"

        MockWorker.side_effect = [worker_v1, worker_v2]

        # 1. First activation with old URL
        pool.set_active_cameras([1], {1: cam1_v1})
        assert pool.active_count == 1
        assert pool._workers[1] == worker_v1
        worker_v1.start.assert_called_once()

        # 2. Second activation with updated URL
        pool.set_active_cameras([1], {1: cam1_v2})
        assert pool.active_count == 1
        worker_v1.stop.assert_called_once()  # Old worker stopped
        assert pool._workers[1] == worker_v2  # Replaced with new worker
        worker_v2.start.assert_called_once()  # New worker started

    pool.stop_all()
