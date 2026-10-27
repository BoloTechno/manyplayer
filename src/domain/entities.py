from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Camera:
    """Entity representing an IP Camera RTSP feed."""
    id: int
    name: str
    stream_url: str = ""
    rotation: int = 0  # 0, 90, 180, 270 (degrees clockwise)
    flip_h: bool = False  # Horizontal mirror flip

    def get_stream_url(self) -> str:
        """Returns the RTSP stream URL for ingestion."""
        return self.stream_url

