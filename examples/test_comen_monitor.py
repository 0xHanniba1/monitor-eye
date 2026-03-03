"""Example: Testing a COMEN patient monitor with MonitorEye.

This example uses the built-in mock server. To test a real monitor,
replace MonitorScreen.from_mock() with:
    screen = MonitorScreen("192.168.1.100", port=5900, password="xxx")
"""

import pytest
from monitor_eye import MonitorScreen


@pytest.fixture
def monitor():
    screen = MonitorScreen.from_mock(port=15911)
    yield screen
    screen.disconnect()


class TestComenMonitorDisplay:
    """Verify patient monitor displays vital signs correctly."""

    def test_capture_screen(self, monitor, tmp_path):
        """TC-01: Capture monitor screen."""
        path = str(tmp_path / "monitor.png")
        frame = monitor.capture(path)
        assert frame is not None, "Failed to capture screen"

    def test_heart_rate_in_range(self, monitor):
        """TC-02: Heart rate should be in normal range."""
        hr_area = monitor.region(20, 40, 200, 80)
        hr = hr_area.read_number()
        if hr is not None:
            assert 30 < hr < 250, f"Heart rate out of range: {hr}"

    def test_alarm_silence(self, monitor):
        """TC-03: Silence button should dismiss active alarm."""
        monitor._mock_server.renderer.trigger_alarm("hr_high")
        assert monitor._mock_server.renderer.alarm_active
        monitor._conn.click(715, 570)
        assert not monitor._mock_server.renderer.alarm_active
