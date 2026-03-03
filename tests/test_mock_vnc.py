"""Tests for the mock VNC server."""

import socket
import struct
import threading
import time

import numpy as np
import pytest

from monitor_eye.mock.vnc_server import MockVNCServer


class TestMockVNCServer:
    @pytest.fixture
    def server(self):
        srv = MockVNCServer(port=15900)
        srv.start()
        time.sleep(0.5)
        yield srv
        srv.stop()

    def test_server_starts_and_stops(self, server):
        assert server.is_running

    def test_server_stop(self):
        srv = MockVNCServer(port=15901)
        srv.start()
        time.sleep(0.3)
        assert srv.is_running
        srv.stop()
        assert not srv.is_running

    def test_client_can_connect(self, server):
        """Test that a raw socket client can complete the RFB handshake."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            sock.connect(("localhost", 15900))
            # Receive server version
            version = sock.recv(12)
            assert version == b"RFB 003.003\n"
            # Send client version
            sock.sendall(b"RFB 003.003\n")
            # Receive security type (U32)
            security = sock.recv(4)
            sec_type = struct.unpack("!I", security)[0]
            assert sec_type == 1  # No authentication
            # Send ClientInit (shared=1)
            sock.sendall(struct.pack("B", 1))
            # Receive ServerInit: width(2) + height(2) + pixel_format(16) + name_len(4) + name
            server_init = sock.recv(24)  # 2+2+16+4 = 24 bytes minimum
            w, h = struct.unpack("!HH", server_init[:4])
            assert w == 800
            assert h == 600
        finally:
            sock.close()

    def test_framebuffer_update(self, server):
        """Test that we can request and receive a framebuffer update."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            sock.connect(("localhost", 15900))
            # Complete handshake
            sock.recv(12)  # server version
            sock.sendall(b"RFB 003.003\n")
            sock.recv(4)   # security type
            sock.sendall(struct.pack("B", 1))  # ClientInit
            # Read ServerInit header
            header = _recv_exact(sock, 24)
            name_len = struct.unpack("!I", header[20:24])[0]
            _recv_exact(sock, name_len)  # read name

            # Send FramebufferUpdateRequest
            # type(3) + incremental(0) + x(0) + y(0) + w(800) + h(600)
            sock.sendall(struct.pack("!BBHHHH", 3, 0, 0, 0, 800, 600))

            # Receive FramebufferUpdate response
            fb_header = _recv_exact(sock, 4)  # type(1) + padding(1) + nRects(2)
            msg_type, n_rects = struct.unpack("!BxH", fb_header)
            assert msg_type == 0
            assert n_rects == 1

            # Read rectangle header
            rect_header = _recv_exact(sock, 12)  # x(2)+y(2)+w(2)+h(2)+encoding(4)
            x, y, w, h, encoding = struct.unpack("!HHHHi", rect_header)
            assert x == 0
            assert y == 0
            assert w == 800
            assert h == 600
            assert encoding == 0  # raw

            # Read pixel data (800*600*4 bytes for 32bpp)
            pixel_data = _recv_exact(sock, w * h * 4)
            assert len(pixel_data) == 800 * 600 * 4
        finally:
            sock.close()

    def test_capture_returns_valid_image(self, server):
        """Test that captured framebuffer contains valid pixel data."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            sock.connect(("localhost", 15900))
            # Handshake
            sock.recv(12)
            sock.sendall(b"RFB 003.003\n")
            sock.recv(4)
            sock.sendall(struct.pack("B", 1))
            header = _recv_exact(sock, 24)
            name_len = struct.unpack("!I", header[20:24])[0]
            _recv_exact(sock, name_len)

            # Request framebuffer
            sock.sendall(struct.pack("!BBHHHH", 3, 0, 0, 0, 800, 600))

            # Skip update header + rect header
            _recv_exact(sock, 4)
            _recv_exact(sock, 12)

            # Read pixels
            pixel_data = _recv_exact(sock, 800 * 600 * 4)
            # Reconstruct as numpy array and verify it's not all zeros
            pixels = np.frombuffer(pixel_data, dtype=np.uint8).reshape(600, 800, 4)
            # The monitor renderer draws colored text, so the image should
            # have some non-zero pixels
            assert pixels.sum() > 0
        finally:
            sock.close()

    def test_renderer_vitals_affect_output(self, server):
        server.renderer.set_vitals(hr=200)
        assert server.renderer.vitals["hr"] == 200

    def test_vncdotool_connect_and_capture(self, server):
        """Test that vncdotool can connect and capture a screenshot."""
        import subprocess
        result = subprocess.run(
            ["vncdotool", "-s", "localhost::15900", "capture", "/tmp/mock_vnc_test.png"],
            timeout=15,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"vncdotool failed: {result.stderr}"
        import cv2
        img = cv2.imread("/tmp/mock_vnc_test.png")
        assert img is not None
        assert img.shape[0] == 600
        assert img.shape[1] == 800


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    """Receive exactly n bytes from a socket."""
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError(f"Connection closed, received {len(data)}/{n} bytes")
        data += chunk
    return data
