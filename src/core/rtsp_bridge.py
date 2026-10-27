import socket
import logging
import threading
from urllib.parse import urlparse
from typing import Optional, Tuple, Set

logger = logging.getLogger(__name__)


class RTSPStreamBridge:
    """In-process loopback TCP bridge that sanitizes RTSP authentication headers.
    
    Resolves the FFmpeg/OpenCV compatibility issue where IP cameras (such as modern Hikvision)
    send dual WWW-Authenticate challenges (both MD5 and SHA-256). Since FFmpeg's
    built-in RTSP demuxer lacks RTSP SHA-256 digest support, parsing the secondary SHA-256
    header corrupts the auth state. This bridge filters out the unsupported SHA-256 challenge,
    allowing FFmpeg to authenticate directly and seamlessly via standard MD5 digest without
    external proxies or third-party servers.
    """

    def __init__(self, target_host: str, target_port: int):
        self.target_host = target_host
        self.target_port = target_port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("127.0.0.1", 0))
        self.port = self.server.getsockname()[1]
        self.server.listen(5)
        self.server.settimeout(0.5)
        self._running = True
        self._active_sockets: Set[socket.socket] = set()
        self._lock = threading.Lock()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name=f"RTSPBridge-{self.target_host}:{self.port}"
        )
        self._thread.start()

    @classmethod
    def create_if_needed(cls, url: str) -> Tuple[Optional["RTSPStreamBridge"], str]:
        """Creates a bridge if url is a remote RTSP stream; returns (bridge, target_url)."""
        if not url or not url.startswith("rtsp://"):
            return None, url
        try:
            parsed = urlparse(url)
            # Only bridge remote hosts (not loopback or local mock feeds)
            if not parsed.hostname or parsed.hostname in ("127.0.0.1", "localhost", "0.0.0.0"):
                return None, url

            bridge = cls(parsed.hostname, parsed.port or 554)
            sanitized_url = bridge.get_sanitized_url(url)
            return bridge, sanitized_url
        except Exception as e:
            logger.warning(f"Failed to initialize RTSPStreamBridge for {url}: {e}")
            return None, url

    def get_sanitized_url(self, original_url: str) -> str:
        parsed = urlparse(original_url)
        auth = ""
        if parsed.username:
            auth = parsed.username
            if parsed.password:
                auth += f":{parsed.password}"
            auth += "@"
        path_and_query = parsed.path or "/"
        if parsed.query:
            path_and_query += f"?{parsed.query}"
        return f"rtsp://{auth}127.0.0.1:{self.port}{path_and_query}"

    def _filter_headers(self, data: bytes) -> bytes:
        if b"WWW-Authenticate:" not in data or (b"SHA-256" not in data and b"sha-256" not in data):
            return data
        lines = data.split(b"\r\n")
        filtered = [
            line for line in lines
            if not (b"algorithm=\"SHA-256\"" in line or b"algorithm=\"sha-256\"" in line)
        ]
        return b"\r\n".join(filtered)

    def _forward(self, src: socket.socket, dst: socket.socket, filter_auth: bool = False) -> None:
        try:
            while self._running:
                data = src.recv(16384)
                if not data:
                    break
                if filter_auth:
                    data = self._filter_headers(data)
                dst.sendall(data)
        except Exception:
            pass
        finally:
            with self._lock:
                self._active_sockets.discard(src)
                self._active_sockets.discard(dst)
            try:
                src.close()
            except Exception:
                pass
            try:
                dst.close()
            except Exception:
                pass

    def _handle_client(self, client_sock: socket.socket) -> None:
        try:
            target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_sock.settimeout(5.0)
            target_sock.connect((self.target_host, self.target_port))
            target_sock.settimeout(None)
        except Exception as e:
            logger.debug(f"Bridge failed to connect to target {self.target_host}:{self.target_port}: {e}")
            client_sock.close()
            return

        with self._lock:
            if not self._running:
                client_sock.close()
                target_sock.close()
                return
            self._active_sockets.add(client_sock)
            self._active_sockets.add(target_sock)

        threading.Thread(
            target=self._forward,
            args=(client_sock, target_sock, False),
            daemon=True
        ).start()
        threading.Thread(
            target=self._forward,
            args=(target_sock, client_sock, True),
            daemon=True
        ).start()

    def _run(self) -> None:
        while self._running:
            try:
                cs, _ = self.server.accept()
                if not self._running:
                    cs.close()
                    break
                threading.Thread(
                    target=self._handle_client,
                    args=(cs,),
                    daemon=True,
                    name=f"RTSPBridgeHandler-{self.port}"
                ).start()
            except socket.timeout:
                continue
            except Exception:
                break

    def close(self) -> None:
        self._running = False
        try:
            self.server.close()
        except Exception:
            pass
        if hasattr(self, "_thread") and self._thread.is_alive() and threading.current_thread() != self._thread:
            self._thread.join(timeout=0.6)
        with self._lock:
            for s in list(self._active_sockets):
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    s.close()
                except Exception:
                    pass
            self._active_sockets.clear()
