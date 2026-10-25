import logging
import threading
from typing import List, Tuple, Optional
from dataclasses import dataclass
from src.domain.geometry import Point

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """Bounding box detection result."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int

    @property
    def foot_point(self) -> Point:
        """Calculates the bottom-center point representing the feet of the person."""
        return Point(x=(self.x1 + self.x2) / 2.0, y=self.y2)

    @property
    def center_point(self) -> Point:
        """Calculates the center of the bounding box."""
        return Point(x=(self.x1 + self.x2) / 2.0, y=(self.y1 + self.y2) / 2.0)


class PersonDetector:
    """Wrapper around YOLOv8n object detector for person detection.
    
    Thread-safe and optimized for CPU inference on Windows with automatic fallback.
    """

    def __init__(self, model_name_or_path: str = "yolov8n.pt", conf_threshold: float = 0.45):
        self.model_path = model_name_or_path
        self.conf_threshold = conf_threshold
        self._model = None
        self._is_loaded = False
        self._lock = threading.Lock()

    def load_model(self) -> bool:
        """Loads the YOLO model into memory thread-safely."""
        with self._lock:
            if self._is_loaded and self._model is not None:
                return True
            try:
                from ultralytics import YOLO
                logger.info(f"Loading YOLO model from: {self.model_path}")
                self._model = YOLO(self.model_path)
                self._is_loaded = True
                logger.info("YOLO model loaded successfully.")
                return True
            except Exception as e:
                logger.warning(f"Failed to load Ultralytics YOLO model: {e}. AI detection will be disabled.")
                self._is_loaded = False
                return False

    def detect(self, frame) -> List[Detection]:
        """Detects person objects in a BGR video frame thread-safely."""
        with self._lock:
            if not self._is_loaded or self._model is None:
                return []

            try:
                # classes=[0] filters exclusively for person (COCO class 0)
                results = self._model(
                    frame,
                    classes=[0],
                    conf=self.conf_threshold,
                    verbose=False
                )

                detections: List[Detection] = []
                if results and len(results) > 0:
                    boxes = results[0].boxes
                    if boxes is not None and len(boxes) > 0:
                        xyxy = boxes.xyxy.cpu().numpy()
                        confs = boxes.conf.cpu().numpy()
                        cls_ids = boxes.cls.cpu().numpy().astype(int)

                        for box, conf, cid in zip(xyxy, confs, cls_ids):
                            detections.append(Detection(
                                x1=float(box[0]),
                                y1=float(box[1]),
                                x2=float(box[2]),
                                y2=float(box[3]),
                                confidence=float(conf),
                                class_id=int(cid)
                            ))

                return detections
            except Exception as e:
                logger.error(f"Error during YOLO inference: {e}")
                return []
