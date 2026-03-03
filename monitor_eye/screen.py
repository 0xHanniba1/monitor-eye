"""High-level Screen and Region API for patient monitor GUI testing."""

import time
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np

from monitor_eye.connection import VNCConnection
from monitor_eye.exceptions import FindFailed
from monitor_eye.finder import ImageFinder, Match
from monitor_eye.ocr import OCREngine


class Region:
    """A rectangular area of the screen for focused operations."""

    def __init__(self, x: int, y: int, width: int, height: int,
                 screen: "MonitorScreen"):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self._screen = screen

    def _crop(self, frame: np.ndarray) -> np.ndarray:
        return frame[self.y:self.y + self.height, self.x:self.x + self.width]

    def find(self, pattern: str, timeout: float = 0) -> Match:
        return self._screen.find(pattern, timeout=timeout,
                                  region=(self.x, self.y, self.width, self.height))

    def exists(self, pattern: str, timeout: float = 0) -> Optional[Match]:
        return self._screen.exists(pattern, timeout=timeout,
                                    region=(self.x, self.y, self.width, self.height))

    def text(self) -> str:
        frame = self._screen._capture_raw()
        cropped = self._crop(frame)
        return self._screen._ocr.read_text(cropped)

    def read_number(self) -> Optional[int]:
        frame = self._screen._capture_raw()
        cropped = self._crop(frame)
        return self._screen._ocr.read_number(cropped)

    def capture(self, path: str) -> None:
        frame = self._screen._capture_raw()
        cropped = self._crop(frame)
        cv2.imwrite(path, cropped)


class MonitorScreen:
    """Main entry point for patient monitor GUI testing."""

    def __init__(self, host: str = "localhost", port: int = 5900,
                 password: Optional[str] = None):
        self._conn = VNCConnection(host, port, password)
        self._finder = ImageFinder()
        self._ocr = OCREngine()
        self._mock_server = None
        self._conn.connect()

    @classmethod
    def from_mock(cls, port: int = 15999) -> "MonitorScreen":
        """Create a MonitorScreen backed by the built-in mock VNC server."""
        from monitor_eye.mock.vnc_server import MockVNCServer
        server = MockVNCServer(port=port)
        server.start()
        time.sleep(0.5)
        instance = cls("localhost", port=port)
        instance._mock_server = server
        return instance

    def disconnect(self) -> None:
        self._conn.disconnect()
        if self._mock_server:
            self._mock_server.stop()
            self._mock_server = None

    def _capture_raw(self) -> np.ndarray:
        return self._conn.capture()

    def capture(self, path: Optional[str] = None) -> np.ndarray:
        frame = self._capture_raw()
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(path, frame)
        return frame

    def region(self, x: int, y: int, width: int, height: int) -> Region:
        return Region(x, y, width, height, self)

    def find(self, pattern: str, timeout: float = 0,
             region: Optional[tuple[int, int, int, int]] = None) -> Match:
        deadline = time.time() + timeout
        while True:
            frame = self._capture_raw()
            match = self._finder.find(frame, pattern, region=region)
            if match:
                return match
            if time.time() >= deadline:
                raise FindFailed(pattern, timeout)
            time.sleep(0.3)

    def exists(self, pattern: str, timeout: float = 0,
               region: Optional[tuple[int, int, int, int]] = None) -> Optional[Match]:
        try:
            return self.find(pattern, timeout=timeout, region=region)
        except FindFailed:
            return None

    def find_all(self, pattern: str,
                 region: Optional[tuple[int, int, int, int]] = None) -> list[Match]:
        frame = self._capture_raw()
        return self._finder.find_all(frame, pattern, region=region)

    def click(self, target: Union[str, Match], timeout: float = 3) -> None:
        if isinstance(target, str):
            match = self.find(target, timeout=timeout)
        else:
            match = target
        x, y = match.click_point
        self._conn.click(x, y)

    def type_text(self, text: str) -> None:
        self._conn.type_text(text)
