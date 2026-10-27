import time
import math
from typing import Tuple, Optional
import numpy as np
import cv2


class MockFrameGenerator:
    """Generates synthetic video frames for local offline testing.
    
    Simulates normal CCTV feed with camera name, timestamp, and animated grid background.
    """

    def __init__(self, width: int = 640, height: int = 360):
        self.width = width
        self.height = height
        self._frame_count = 0

    def generate_grid_frame(self, camera_id: int, camera_name: str):
        """Generates a synthetic camera frame with timestamp and animated pattern."""
        self._frame_count += 1
        # Dark slate background
        frame = np.full((self.height, self.width, 3), (25, 30, 35), dtype=np.uint8)

        # Draw moving radar-style line across bottom
        t = time.time()
        scan_x = int((math.sin(t * 2 + camera_id) * 0.45 + 0.5) * self.width)
        cv2.line(frame, (scan_x, self.height - 40), (scan_x, self.height - 10), (0, 200, 100), 2)

        # Grid box border
        cv2.rectangle(frame, (2, 2), (self.width - 3, self.height - 3), (60, 70, 80), 1)

        # Camera Header Badge
        cv2.rectangle(frame, (0, 0), (self.width, 32), (35, 45, 55), -1)
        cv2.putText(
            frame,
            f"CAM {camera_id:02d}: {camera_name}",
            (10, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

        # Live Timestamp
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            frame,
            f"LIVE | {timestamp_str}",
            (self.width - 190, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 180),
            1,
            cv2.LINE_AA
        )

        # Center camera identifier circle
        center = (self.width // 2, self.height // 2)
        cv2.circle(frame, center, 40, (45, 55, 65), -1)
        cv2.putText(
            frame,
            f"#{camera_id}",
            (center[0] - 18, center[1] + 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (200, 210, 220),
            2,
            cv2.LINE_AA
        )

        return frame

