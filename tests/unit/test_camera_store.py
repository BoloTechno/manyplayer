import os
import tempfile
import pytest
from src.domain.entities import Camera
from src.core.camera_store import CameraStore
from src.core.frame_store import SharedFrameStore


def test_camera_store_load_and_save():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        store = CameraStore(tmp_path)
        cams = [
            Camera(id=1, name="Cam 1", sub_stream_url="rtsp://sub1", main_stream_url="rtsp://main1", is_counter_target="Cam 1"),
            Camera(id=2, name="Cam 2", sub_stream_url="rtsp://sub2", main_stream_url="rtsp://main2", is_counter_target="Cam 2"),
            Camera(id=3, name="Cam 3", sub_stream_url="rtsp://sub3", main_stream_url="rtsp://main3")
        ]
        store.save_cameras(cams)

        loaded = store.load_cameras()
        assert len(loaded) == 3
        assert loaded[0].id == 1
        assert loaded[0].name == "Cam 1"
        assert loaded[0].is_counter_target == "Cam 1"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_camera_store_corrupt_file_recovery():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp.write(b"{ this is invalid corrupted json content !!!")
        tmp_path = tmp.name

    try:
        store = CameraStore(tmp_path)
        # Should gracefully return empty list instead of crashing
        loaded = store.load_cameras()
        assert loaded == []

        # Saving over corrupt file should safely rewrite valid content atomically
        cams = [Camera(id=1, name="Recovered Cam", sub_stream_url="", main_stream_url="")]
        store.save_cameras(cams)
        reloaded = store.load_cameras()
        assert len(reloaded) == 1
        assert reloaded[0].name == "Recovered Cam"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        if os.path.exists(f"{tmp_path}.tmp"):
            os.remove(f"{tmp_path}.tmp")



def test_camera_store_auto_inits_from_example_template():
    with tempfile.TemporaryDirectory() as tmpdir:
        example_path = os.path.join(tmpdir, "cameras.example.json")
        target_path = os.path.join(tmpdir, "cameras.json")

        # Create example template
        import json
        with open(example_path, "w", encoding="utf-8") as f:
            json.dump([
                {
                    "id": 1,
                    "name": "Template Camera",
                    "sub_stream_url": "rtsp://username:password@192.168.1.100:554/sub",
                    "main_stream_url": "rtsp://username:password@192.168.1.100:554/main",
                    "is_counter_target": None
                }
            ], f)

        assert not os.path.exists(target_path)

        store = CameraStore(target_path)
        loaded = store.load_cameras()

        # Target file must now exist as a copy of the example template
        assert os.path.exists(target_path)
        assert len(loaded) == 1
        assert loaded[0].id == 1
        assert loaded[0].name == "Template Camera"


def test_shared_frame_store_with_sequence_caching():
    store = SharedFrameStore()
    assert store.get_frame(1) is None
    assert store.is_online(1) is False

    dummy_frame1 = b"fake_frame_bytes_1"
    seq1 = store.put_frame(camera_id=1, frame=dummy_frame1, is_online=True)
    assert seq1 == 1

    frame, seq, is_online = store.get_frame_with_seq(1)
    assert frame == dummy_frame1
    assert seq == 1
    assert is_online is True

    # Push second frame
    dummy_frame2 = b"fake_frame_bytes_2"
    seq2 = store.put_frame(camera_id=1, frame=dummy_frame2, is_online=True)
    assert seq2 == 2

    frame, seq, is_online = store.get_frame_with_seq(1)
    assert frame == dummy_frame2
    assert seq == 2

    # Batch visible frames with sequence
    batch = store.get_visible_frames_with_seq([1, 2])
    assert batch[1][0] == dummy_frame2
    assert batch[1][1] == 2
    assert batch[1][2] is True
    assert batch[2][0] is None
    assert batch[2][1] == 0
    assert batch[2][2] is False

    store.clear()
    assert store.get_frame(1) is None
