"""Tests for VNC connection management."""

import time
import subprocess

import numpy as np
import pytest

from monitor_eye.connection import VNCConnection
from monitor_eye.mock.vnc_server import MockVNCServer


@pytest.fixture(scope="module")
def mock_server():
    srv = MockVNCServer(port=15901)
    srv.start()
    time.sleep(0.5)
    yield srv
    srv.stop()


class TestVNCConnection:
    def test_connect_and_disconnect(self, mock_server):
        conn = VNCConnection("localhost", port=15901)
        conn.connect()
        assert conn.is_connected
        conn.disconnect()

    def test_capture_returns_numpy_array(self, mock_server):
        conn = VNCConnection("localhost", port=15901)
        conn.connect()
        frame = conn.capture()
        conn.disconnect()
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (600, 800, 3)

    def test_click_does_not_raise(self, mock_server):
        conn = VNCConnection("localhost", port=15901)
        conn.connect()
        conn.click(400, 300)
        conn.disconnect()

    def test_type_text_does_not_raise(self, mock_server):
        conn = VNCConnection("localhost", port=15901)
        conn.connect()
        conn.type_text("hello")
        conn.disconnect()
