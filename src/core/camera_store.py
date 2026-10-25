import json
import logging
import os
from typing import List, Optional
from src.domain.entities import Camera

logger = logging.getLogger(__name__)


class CameraStore:
    """Manages loading and saving the list of 36 RTSP cameras from a JSON file."""

    def __init__(self, file_path: str = "config/cameras.json"):
        self.file_path = file_path

    def load_cameras(self) -> List[Camera]:
        """Loads cameras from the JSON file. If file is missing or corrupt, returns empty list gracefully."""
        if not os.path.exists(self.file_path):
            return []

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            cameras: List[Camera] = []
            for item in data:
                cam = Camera(
                    id=int(item["id"]),
                    name=str(item["name"]),
                    sub_stream_url=str(item["sub_stream_url"]),
                    main_stream_url=str(item["main_stream_url"]),
                    is_counter_target=item.get("is_counter_target")
                )
                cameras.append(cam)

            return sorted(cameras, key=lambda c: c.id)
        except Exception as e:
            logger.error(f"Error loading camera configuration from {self.file_path}: {e}")
            return []

    def save_cameras(self, cameras: List[Camera]) -> None:
        """Atomically saves cameras to the JSON file to prevent file corruption on crash or power loss."""
        abs_path = os.path.abspath(self.file_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        data = [
            {
                "id": cam.id,
                "name": cam.name,
                "sub_stream_url": cam.sub_stream_url,
                "main_stream_url": cam.main_stream_url,
                "is_counter_target": cam.is_counter_target
            }
            for cam in sorted(cameras, key=lambda c: c.id)
        ]

        temp_path = f"{self.file_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_path, self.file_path)

    def get_counter_cameras(self) -> List[Camera]:
        """Returns cameras designated as counter targets (e.g. Cam 1, Cam 2)."""
        cameras = self.load_cameras()
        return [c for c in cameras if c.is_counter_target]
