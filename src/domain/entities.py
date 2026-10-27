from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class Camera:
    """Entity representing an IP Camera RTSP feed."""
    id: int
    name: str
    stream_url: str = ""
    sub_stream_url: str = ""
    main_stream_url: str = ""
    is_counter_target: Optional[str] = None

    def __post_init__(self):
        if not self.stream_url:
            self.stream_url = self.sub_stream_url or self.main_stream_url or ""
        if not self.sub_stream_url:
            self.sub_stream_url = self.stream_url
        if not self.main_stream_url:
            self.main_stream_url = self.stream_url

    def get_stream_url(self, is_main: bool = False) -> str:
        """Returns the RTSP stream URL for ingestion."""
        return self.stream_url
