"""VNC connection management wrapping vncdotool."""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from monitor_eye.exceptions import ConnectionError


class VNCConnection:
    """Manages a VNC connection to a patient monitor (or mock server).

    Uses the vncdotool CLI via subprocess to avoid Twisted reactor
    issues that occur when using the Python API in pytest.
    """

    def __init__(self, host: str = "localhost", port: int = 5900,
                 password: Optional[str] = None):
        self.host = host
        self.port = port
        self.password = password
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        """Establish a VNC connection by verifying connectivity."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            probe_path = f.name
        try:
            self._run_vncdotool("capture", probe_path)
            self._connected = True
        except Exception as e:
            raise ConnectionError(self.host, self.port, str(e))
        finally:
            Path(probe_path).unlink(missing_ok=True)

    def disconnect(self) -> None:
        """Close the VNC connection."""
        self._connected = False

    def _run_vncdotool(self, *args: str) -> subprocess.CompletedProcess:
        """Run vncdotool CLI command."""
        cmd = ["vncdotool", "-s", f"{self.host}::{self.port}"]
        if self.password:
            cmd.extend(["--password", self.password])
        cmd.extend(args)
        return subprocess.run(cmd, capture_output=True, timeout=10, check=True)

    def capture(self) -> np.ndarray:
        """Capture current screen as BGR numpy array."""
        if not self._connected:
            raise ConnectionError(self.host, self.port, "Not connected")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            self._run_vncdotool("capture", path)
            img = cv2.imread(path)
            if img is None:
                raise ConnectionError(self.host, self.port,
                                      "Failed to capture screen")
            return img
        finally:
            Path(path).unlink(missing_ok=True)

    def click(self, x: int, y: int) -> None:
        """Send a mouse click at (x, y) coordinates."""
        if not self._connected:
            raise ConnectionError(self.host, self.port, "Not connected")
        self._run_vncdotool("move", str(x), str(y), "click", "1")

    def type_text(self, text: str) -> None:
        """Type text via VNC keyboard events."""
        if not self._connected:
            raise ConnectionError(self.host, self.port, "Not connected")
        self._run_vncdotool("type", text)
