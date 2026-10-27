from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Camera:
    """Entity representing an IP Camera RTSP feed."""
    id: int
    name: str
    stream_url: str = ""

    def get_stream_url(self) -> str:
        """Returns the RTSP stream URL for ingestion."""
        return self.stream_url

