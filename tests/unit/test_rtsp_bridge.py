import pytest
from src.core.rtsp_bridge import RTSPStreamBridge


def test_rtsp_bridge_create_if_needed_local():
    # Empty URL
    bridge, url = RTSPStreamBridge.create_if_needed("")
    assert bridge is None
    assert url == ""

    # Mock stream
    bridge, url = RTSPStreamBridge.create_if_needed("mock://camera_1")
    assert bridge is None
    assert url == "mock://camera_1"

    # Localhost stream
    bridge, url = RTSPStreamBridge.create_if_needed("rtsp://admin:pass@127.0.0.1:8554/live")
    assert bridge is None
    assert url == "rtsp://admin:pass@127.0.0.1:8554/live"


def test_rtsp_bridge_create_if_needed_remote():
    remote_url = "rtsp://user:secret@192.168.1.100:554/Streaming/Channels/102"
    bridge, target_url = RTSPStreamBridge.create_if_needed(remote_url)
    assert bridge is not None
    assert bridge.port > 0
    assert target_url.startswith(f"rtsp://user:secret@127.0.0.1:{bridge.port}/Streaming/Channels/102")
    bridge.close()


def test_rtsp_bridge_header_filtering():
    bridge = RTSPStreamBridge("127.0.0.1", 554)
    raw_response = (
        b"RTSP/1.0 401 Unauthorized\r\n"
        b"CSeq: 1\r\n"
        b'WWW-Authenticate: Digest realm="IP Camera", nonce="12345", algorithm="MD5", stale="FALSE"\r\n'
        b'WWW-Authenticate: Digest realm="IP Camera", nonce="12345", algorithm="SHA-256", stale="FALSE"\r\n'
        b"Date: Mon, 26 Oct 2026 12:00:00 GMT\r\n\r\n"
    )

    filtered = bridge._filter_headers(raw_response)
    assert b'algorithm="MD5"' in filtered
    assert b'algorithm="SHA-256"' not in filtered
    assert b"CSeq: 1" in filtered
    bridge.close()


def test_rtsp_bridge_close_terminates_active_sockets():
    import socket
    import threading
    import time

    mock_target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    mock_target.bind(("127.0.0.1", 0))
    mock_port = mock_target.getsockname()[1]
    mock_target.listen(1)

    bridge = RTSPStreamBridge("127.0.0.1", mock_port)

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", bridge.port))
    target_conn, _ = mock_target.accept()

    threads_before = threading.active_count()
    bridge.close()
    time.sleep(0.1)
    threads_after = threading.active_count()

    client.close()
    target_conn.close()
    mock_target.close()

    assert threads_after < threads_before
    assert len(bridge._active_sockets) == 0
