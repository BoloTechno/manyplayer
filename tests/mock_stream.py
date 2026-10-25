import time
import math
from typing import Tuple, Optional
import numpy as np
import cv2


class MockFrameGenerator:
    """Generates synthetic video frames for local offline testing.
    
    Can simulate:
    - Normal CCTV feed with camera name, timestamp, and animated grid background.
    - Person walk simulation crossing from top to bottom (for testing people counter).
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

    def generate_person_crossing_frame(
        self,
        camera_name: str,
        doorway_y: int = 180,
        door_x1: int = 150,
        door_x2: int = 490
    ) -> Tuple[np.ndarray, Optional[Tuple[int, int]]]:
        """Generates a frame with a simulated person moving downwards through the doorway.
        
        Returns:
            (frame, (foot_x, foot_y))
        """
        self._frame_count += 1
        frame = np.full((self.height, self.width, 3), (30, 35, 40), dtype=np.uint8)

        # Draw Doorway Virtual Tripwire Line
        cv2.line(frame, (door_x1, doorway_y), (door_x2, doorway_y), (0, 255, 255), 2)
        cv2.putText(frame, "VIRTUAL TRIPWIRE", (door_x1, doorway_y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

        # Simulate person walking from top (y=60) to bottom (y=300) in a 60-frame loop
        cycle_pos = (self._frame_count % 90) / 90.0
        person_y = int(60 + cycle_pos * 240)
        person_x = int(self.width / 2)

        # Draw Person (Head, Body, Bounding Box)
        box_w, box_h = 50, 110
        top_left = (person_x - box_w // 2, person_y - box_h)
        bottom_right = (person_x + box_w // 2, person_y)

        # Bounding box
        cv2.rectangle(frame, top_left, bottom_right, (0, 255, 0), 2)
        cv2.putText(frame, "Person: 0.94", (top_left[0], top_left[1] - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1, cv2.LINE_AA)

        # Foot centroid point
        foot_point = (person_x, person_y)
        cv2.circle(frame, foot_point, 5, (0, 0, 255), -1)

        # Header
        cv2.rectangle(frame, (0, 0), (self.width, 30), (20, 25, 30), -1)
        cv2.putText(frame, f"AI COUNTER TEST | {camera_name}", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        return frame, foot_point
