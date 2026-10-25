import threading
from typing import Dict, List, Optional, Tuple, Any


class SharedFrameStore:
    """Thread-safe in-memory storage holding the latest frame and sequence number for each camera.
    
    Features:
    - Zero Latency: Always retains only the latest frame (LIFO).
    - Sequence Caching: Tracks monotonic sequence numbers per camera to prevent
      redundant QImage memory conversions in the UI loop.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._frames: Dict[int, Any] = {}
        self._sequences: Dict[int, int] = {}
        self._online_status: Dict[int, bool] = {}

    def put_frame(self, camera_id: int, frame: Any, is_online: bool = True) -> int:
        """Stores the latest frame and increments the camera's sequence number."""
        with self._lock:
            seq = self._sequences.get(camera_id, 0) + 1
            self._sequences[camera_id] = seq
            self._frames[camera_id] = frame
            self._online_status[camera_id] = is_online
            return seq

    def get_frame(self, camera_id: int) -> Optional[Any]:
        """Retrieves the latest frame for a specific camera."""
        with self._lock:
            return self._frames.get(camera_id)

    def get_frame_with_seq(self, camera_id: int) -> Tuple[Optional[Any], int, bool]:
        """Retrieves frame, sequence number, and online status in a single atomic lock."""
        with self._lock:
            return (
                self._frames.get(camera_id),
                self._sequences.get(camera_id, 0),
                self._online_status.get(camera_id, False)
            )

    def is_online(self, camera_id: int) -> bool:
        """Checks if the camera stream is currently active."""
        with self._lock:
            return self._online_status.get(camera_id, False)

    def get_visible_frames_with_seq(
        self,
        visible_camera_ids: List[int]
    ) -> Dict[int, Tuple[Optional[Any], int, bool]]:
        """Batch-retrieves frames, sequence numbers, and statuses for visible cameras."""
        with self._lock:
            return {
                cid: (
                    self._frames.get(cid),
                    self._sequences.get(cid, 0),
                    self._online_status.get(cid, False)
                )
                for cid in visible_camera_ids
            }

    def clear(self) -> None:
        """Clears all stored frames, sequence counters, and status."""
        with self._lock:
            self._frames.clear()
            self._sequences.clear()
            self._online_status.clear()
