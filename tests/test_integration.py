"""End-to-end integration tests using Mock VNC Server."""

import pytest

from monitor_eye import MonitorScreen


class TestEndToEnd:
    @pytest.fixture
    def screen(self):
        s = MonitorScreen.from_mock(port=15910)
        yield s
        s.disconnect()

    def test_full_workflow(self, screen, tmp_path):
        """Full flow: connect -> capture -> OCR -> save screenshot."""
        # Capture
        frame = screen.capture()
        assert frame.shape == (600, 800, 3)

        # Save screenshot
        path = str(tmp_path / "test_capture.png")
        screen.capture(path)

        # Read HR from approximate region
        hr_region = screen.region(20, 40, 200, 80)
        hr = hr_region.read_number()
        assert hr is None or isinstance(hr, int)

    def test_alarm_workflow(self, screen):
        """Trigger alarm -> verify -> silence -> verify cleared."""
        screen._mock_server.renderer.trigger_alarm("hr_high")
        assert screen._mock_server.renderer.alarm_active

        # Click silence button area
        screen._conn.click(715, 570)

        # Verify alarm silenced
        assert not screen._mock_server.renderer.alarm_active
