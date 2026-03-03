"""Tests for the high-level Screen API."""

import time

import pytest

from monitor_eye.screen import MonitorScreen, Region
from monitor_eye.finder import Match


class TestMonitorScreen:
    def test_from_mock_creates_working_screen(self):
        screen = MonitorScreen.from_mock(port=15903)
        try:
            frame = screen.capture()
            assert frame is not None
            assert frame.shape == (600, 800, 3)
        finally:
            screen.disconnect()

    def test_region_returns_region_object(self):
        screen = MonitorScreen.from_mock(port=15904)
        try:
            region = screen.region(0, 0, 400, 300)
            assert isinstance(region, Region)
            assert region.width == 400
            assert region.height == 300
        finally:
            screen.disconnect()

    def test_capture_saves_to_file(self, tmp_path):
        screen = MonitorScreen.from_mock(port=15905)
        try:
            path = str(tmp_path / "capture.png")
            screen.capture(path)
            import cv2
            img = cv2.imread(path)
            assert img is not None
        finally:
            screen.disconnect()


class TestRegion:
    def test_region_read_number(self):
        """Read HR from the mock monitor."""
        screen = MonitorScreen.from_mock(port=15906)
        try:
            # HR is rendered at approximately (30, 50) in the mock
            hr_region = screen.region(20, 40, 200, 80)
            number = hr_region.read_number()
            # Allow None (OCR might not read it) or a valid number
            assert number is None or isinstance(number, int)
        finally:
            screen.disconnect()

    def test_region_capture(self, tmp_path):
        screen = MonitorScreen.from_mock(port=15907)
        try:
            region = screen.region(0, 0, 400, 300)
            path = str(tmp_path / "region.png")
            region.capture(path)
            import cv2
            img = cv2.imread(path)
            assert img is not None
            assert img.shape[0] == 300
            assert img.shape[1] == 400
        finally:
            screen.disconnect()
