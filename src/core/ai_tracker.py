import math
from typing import Dict, List, Tuple
from src.domain.geometry import Point
from src.core.ai_detector import Detection


class SimpleTracker:
    """Lightweight Euclidean centroid tracker for associating person detections across frames.
    
    Assigns persistent IDs to bounding boxes based on minimum distance matching.
    Zero external dependencies, highly resilient.
    """

    def __init__(self, max_disappeared_frames: int = 30, max_distance: float = 80.0):
        self.next_object_id = 1
        self.objects: Dict[int, Point] = {}
        self.disappeared: Dict[int, int] = {}
        self.max_disappeared_frames = max_disappeared_frames
        self.max_distance = max_distance

    def update(self, detections: List[Detection]) -> List[Tuple[int, Detection]]:
        """Updates tracks with new detections for the current frame.
        
        Returns:
            List of (track_id, detection) pairs.
        """
        # If no detections, increment disappeared count for all tracked objects
        if len(detections) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared_frames:
                    self._deregister(object_id)
            return []

        # Current input centroids (using feet position for tracking ground contact)
        input_points = [d.foot_point for d in detections]

        # If currently tracking no objects, register all detections as new
        if len(self.objects) == 0:
            results: List[Tuple[int, Detection]] = []
            for i, pt in enumerate(input_points):
                oid = self._register(pt)
                results.append((oid, detections[i]))
            return results

        # Match existing tracked objects to input centroids using distance
        object_ids = list(self.objects.keys())
        object_points = list(self.objects.values())

        # Compute distance matrix
        matched_pairs: List[Tuple[int, Detection]] = []
        used_rows = set()
        used_cols = set()

        # Simple greedy nearest-neighbor matching
        distances = []
        for row, oid in enumerate(object_ids):
            for col, in_pt in enumerate(input_points):
                dist = object_points[row].distance_to(in_pt)
                distances.append((dist, row, col))

        distances.sort(key=lambda x: x[0])

        for dist, row, col in distances:
            if row in used_rows or col in used_cols:
                continue
            if dist > self.max_distance:
                continue

            oid = object_ids[row]
            self.objects[oid] = input_points[col]
            self.disappeared[oid] = 0
            matched_pairs.append((oid, detections[col]))

            used_rows.add(row)
            used_cols.add(col)

        # Handle unmatched existing objects
        for row, oid in enumerate(object_ids):
            if row not in used_rows:
                self.disappeared[oid] += 1
                if self.disappeared[oid] > self.max_disappeared_frames:
                    self._deregister(oid)

        # Register new objects for unmatched input detections
        for col, in_pt in enumerate(input_points):
            if col not in used_cols:
                oid = self._register(in_pt)
                matched_pairs.append((oid, detections[col]))

        return matched_pairs

    def _register(self, point: Point) -> int:
        oid = self.next_object_id
        self.next_object_id += 1
        self.objects[oid] = point
        self.disappeared[oid] = 0
        return oid

    def _deregister(self, object_id: int) -> None:
        if object_id in self.objects:
            del self.objects[object_id]
        if object_id in self.disappeared:
            del self.disappeared[object_id]

    def reset(self) -> None:
        self.next_object_id = 1
        self.objects.clear()
        self.disappeared.clear()
